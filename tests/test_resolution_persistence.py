"""Central resolver reopens actual confirmed copies and saved inputs after restart."""

import os
import subprocess
import sys


def test_resolver_independent_migration_and_reopen(tmp_path):
    env = os.environ.copy()
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "data" / "synthetic.sqlite3"),
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"], env=env, check=True, capture_output=True, timeout=30
    )
    create = """
import django,hashlib,uuid
django.setup()
from django.contrib.auth import get_user_model
from apps.archive import services as a,models as am
from apps.catalog.models import Work,Arrangement,Part,InstrumentVariant
from apps.projects import services as p,models as m,resolution_services as r
from config.env import env
from tests.pdf_fixtures import pdf
from tests.archive_fixtures import PAGE
from tests.test_archive_workflow import receipt,draft,confirm
actor=get_user_model().objects.create_user('synthetic-resolver-persist')
arr=Arrangement.objects.create(work=Work.objects.create(title='Synthetic resolver'))
part=Part.objects.create(instrument=InstrumentVariant.objects.create(name='Synthetic',clef='BASS'),code='2')
folder=am.SourceFolder.objects.create(relative_path='Synthetic')
data=pdf()
version,_=a.observe_version(folder.pk,'Synthetic/scan.pdf',sha256=hashlib.sha256(data).hexdigest(),byte_size=len(data),pdf_state='VALID',page_info=[PAGE])
file,_=receipt(a.register_base(version.pk,'_Ungeprueft/test.pdf'))
file=confirm(file,draft(file,actor,arr,[part]),actor,path='Synthetic/test.pdf')
path=env.curated_dir/file.relative_path; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
values=dict(name='Synthetic',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title='')
project=p.save_project(values,actor=actor)
person=m.ProjectParticipant.objects.create(project=project,guest_id=uuid.uuid4(),display_name='Synthetic',default_part=part)
slot=m.ProjectPosition.objects.create(project=project,order=1,arrangement=arr)
result=r.resolve_cell(project.pk,slot.pk,person.pk)
assert result.usable and result.edition_origin=='SOLE' and result.sha256==file.sha256
"""
    subprocess.run([sys.executable, "-c", create], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from apps.projects import models as m,resolution_services as r
from apps.archive.models import ArchiveFile
project=m.Project.objects.get(); slot=project.positions.get(); person=project.participants.get()
result=r.resolve_cell(project.pk,slot.pk,person.pk)
assert result.usable and result.part_origin=='SAVED_DEFAULT' and result.edition_origin=='SOLE'
assert result.sha256==ArchiveFile.objects.get().sha256 and project.revision==1
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
