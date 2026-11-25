# Shared runtime and Windows distribution

## Local initialization guard increment

The local synthetic profile validates archive-root nesting and database/secret/
log separation before creating its secret or directories. It rejects configured
parent traversal, existing symlink/reparse components and non-regular or hardlinked
runtime files. Fifty-three targeted Windows configuration checks passed, including
real synthetic hardlinks and a linked-root test with no initialization writes.
Windows reserved names, alternate-stream syntax and trailing-dot/space aliases
are rejected before lookup/creation. Metadata errors use fixed messages.
Sandbox-denied hardlink setup was rerun with approved native access.

These are configuration-time guards. Native handle-relative access, independent
RAW write denial, publication/recovery and packaged runtime acceptance still need
their own WP-06p verification. A local read-only directory-handle probe confirmed
stable inode identity while exposing different timestamp precision between
descriptor and path metadata. The Windows backend must use consistent high-
precision handle metadata and validate mutation/race behavior.

## Verified checkpoint and remaining foundation gates

The shared-runtime proof in `scripts/portable_runtime_smoke.py` now exercises
fresh actual migrations, an exclusively owned application lock, loopback WSGI
requests with normal authentication/CSRF, one worker's lease/release, bounded
shutdown and an isolated SQLite backup/restore. Its subprocess regression uses
a foreign working directory and conflicting inherited installation settings;
the protected synthetic sentinel is unchanged. Targeted Windows execution
passed with twelve startup/worker/runtime tests. Exact Linux/Windows integration
CI is pending. The WSGI reference server is test-only. This is evidence for the
shared lifecycle building blocks, not a shipped launcher or desktop edition.
Native archive safety, managed production serving, full installation restore,
packaging and physical acceptance retain their separate contracts.

PR #56/57 are integrated at main
`ca8647cfb04d26e3d61048e22e8885e6b5c460bb`; exact Main CI 45640472935 passed
Foundation, Container, Windows shared runtime and changes. This verifies shared
processing and the implemented boundaries. It does not prove native Windows
archive publication, packaged desktop installation or physical NAS behavior.

WP-06p tracks the remaining high-priority foundation work. Validate the native
storage boundary without relaxing reparse/identity/no-clobber/RAW contracts and
exercise configured roots, initialization/locking, owned loopback lifecycle,
graceful shutdown and restore on synthetic Windows/Linux inputs. Complete these
foundation gates before major expanded product work. The final installer remains
separate distribution acceptance. Region/content architecture and future OCR
dependencies must preserve these boundaries.

## Runtime recommendation

Package an application directory with a private Python interpreter, pinned
packages, collected static files, migrations, PDFium, fonts and OCR binaries
and trained data. A native launcher should start the same WSGI application and
one worker, expose the UI in a managed WebView and bind exclusively to loopback.
This preserves template rendering, authentication, CSRF and the existing service
APIs. A user-installed Python would conflict with the distribution requirement.
A single-file self-extracting executable adds extraction cost and complicates
native library discovery and child interpreter invocation. Validate the directory
bundle first. An installer and WebView/runtime redistribution rights, offline
installation and update/rollback tests are later desktop deliverables.

PyInstaller is a packaging alternative that needs a dedicated child-process
dispatcher because its frozen executable is a bootloader. The current PDF and
resource-limit children expect a Python interpreter. A private interpreter
directory avoids that specific change and preserves module subprocesses.
This recommendation follows the documented runtime semantics and still needs
an installed-runtime prototype. See [PyInstaller runtime information](https://pyinstaller.org/en/stable/runtime-information.html)
and [bundle modes](https://pyinstaller.org/en/stable/operating-mode.html).

## Existing boundaries and work before desktop delivery

* Services and ORM models already implement catalog, resolution, snapshots and
  job ownership. Reuse them through the existing UI. Keep Gunicorn, Compose,
  mount validation and private TLS at the server entry point.
* A desktop shortcut can start in an arbitrary directory. Database readiness
  now invokes the installed management script. PDF subprocesses start in the
  installed code tree and continue to stage data only in their private scratch
  directory. Keep installed code read-only.
* The local profile creates synthetic roots and supports development login.
  Implement desktop settings separately from that profile. Validate configured
  roots for identity, nesting, permissions and reparse points before any writes.
  Keep database, logs, secret, settings and scratch in private writable storage.
  Store only validated selections and change them while the worker is quiescent.
* SQLite migrations and short transactions are shared. Require local database
  storage, exclusive maintenance and isolated recovery. The launcher must hold
  the application lifecycle lock, migrate before serving and supervise shutdown.
  Verify crash recovery, single-instance startup and database backup/restore on
  NTFS with synthetic data before enabling desktop use.
* `core.files.Root` depends on descriptor-relative POSIX operations.
  Publication/recovery, export cleanup and backup writes still use directory
  descriptors directly. Windows archive access
  requires handle-relative traversal, reparse rejection, independent RAW write
  denial, file identity checks, no-clobber publication and tested crash durability.
  Keep operations unavailable until the backend and its consumers pass equivalent
  race, collision, withdrawal and recovery tests. Ordinary path normalization
  alone cannot meet this contract.
  Inventory traversal now consumes the root's directory metadata interface.
  The backend owns no-follow enumeration and directory mutation detection.
  Cycle detection, relative references and entry budgets stay in inventory
  policy and can be tested independently on both platforms.
  Archive copies and generated PDF staging share the backend's bounded
  exclusive writer. Their independent byte/hash verification and PDF inspection
  remain in the processing layer.
  STATUS services now use backend-owned metadata, bounded staging and marker
  replacement; private download-directory creation also belongs to the backend.
  A conflict proven before publication is distinct from uncertain replacement
  or flush failures, which retain operation-recovery semantics. Backup traversal
  consumes the same no-follow metadata boundary, checks reopened directory
  identities and rejects concurrent directory mutation. Backup writes remain
  POSIX-specific. Local-profile relative roots/runtime paths are pinned to the
  startup directory before initialization, so later working-directory changes
  cannot redirect them. These boundaries do not enable native Windows writes.
* core/processes.py already binds descendants to a Windows Job or Linux process
  group. Preserve bounded CPU, memory, time, input and output for PDF and OCR.
  Windows output writers must enforce byte bounds explicitly. WP-24 should use
  an explicit trusted Tesseract installation and bundled language data, with
  matching evidence and error behavior on each platform.
* Printing is currently unavailable. Future adapters must expose platform
  capabilities and retain uncertain-submission semantics. Spooler and physical
  acceptance remain separate.

## Verification boundary

The foreign-working-directory PDF regression exercises inspection, extraction
and native rendering with synthetic inputs. The migration regression checks the
selected script path. Neither exercises an installed desktop launcher. Desktop
release requires offline clean-machine installation, per-user data ACLs, shared
business workflow tests, managed shutdown and uninstall with user data preserved.
The server retains full Foundation and Container checks and separate NAS acceptance.

The Windows CI job runs configuration, native PDF, process-tree/resource-limit
and startup tests with pinned Python and locked dependencies. Foundation repeats
these contracts on Linux. Windows archive publication and installed desktop
lifecycle remain explicit future acceptance gates.
