"""Validate original tag-build evidence before resuming an approved publication."""

import json
import os
import re
import subprocess
import urllib.request

from scripts.check_release import validate_tag


def verify_candidate(run, jobs, artifacts, tag, source):
    if (
        run["head_sha"] != source
        or run["head_branch"] != tag
        or run["event"] != "push"
        or run["path"] != ".github/workflows/release.yml"
        or run["status"] != "completed"
    ):
        raise ValueError("Candidate must come from the original completed release tag workflow")
    passed = {job["name"] for job in jobs if job["conclusion"] == "success"}
    required = {
        "validate",
        "checks / Foundation (ruff + pytest)",
        "checks / Container (amd64 + security + synthetic smoke)",
    }
    if not required.issubset(passed):
        raise ValueError("All original release checks must have succeeded")
    candidates = [artifact for artifact in artifacts if artifact["name"] == "verified-container"]
    if len(candidates) != 1 or candidates[0]["expired"]:
        raise ValueError("Exactly one unexpired verified candidate is required")
    artifact = candidates[0]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["digest"]):
        raise ValueError("Candidate artifact must have a SHA-256 digest")
    return artifact


def main():
    tag = os.environ["RELEASE_TAG"]
    validate_tag(tag)
    source = subprocess.check_output(["git", "rev-parse", f"{tag}^{{commit}}"], text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", source, "origin/main"], check=True)
    run_id = os.environ["CANDIDATE_RUN_ID"]
    if not run_id.isdigit():
        raise ValueError("Candidate run ID must be numeric")
    outputs = {"tag": tag, "source": source, "run_id": run_id}
    if os.environ["GITHUB_EVENT_NAME"] == "workflow_dispatch":
        repository = os.environ["GITHUB_REPOSITORY"]

        def request(endpoint):
            request = urllib.request.Request(
                f"https://api.github.com/repos/{repository}/{endpoint}",
                headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)

        run = request(f"actions/runs/{run_id}")
        jobs = request(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]
        artifacts = request(f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
        artifact = verify_candidate(run, jobs, artifacts, tag, source)
        outputs.update(artifact_id=str(artifact["id"]), artifact_digest=artifact["digest"])
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        stream.writelines(f"{key}={value}\n" for key, value in outputs.items())


if __name__ == "__main__":
    main()
