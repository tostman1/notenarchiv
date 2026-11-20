"""Regression and trust-boundary tests for promotion of the original checked image."""

import pytest

from scripts.registry_digest import registry_digest
from scripts.verify_release_source import verify_candidate

REPOSITORY = "ghcr.io/tostman1/notenarchiv"
DIGEST = "sha256:" + "a" * 64


def test_published_digest_ignores_the_loaded_candidate_repository():
    metadata = {"RepoDigests": ["notenarchiv-ci@" + DIGEST, REPOSITORY + "@" + DIGEST]}
    assert registry_digest(metadata, REPOSITORY) == REPOSITORY + "@" + DIGEST


@pytest.mark.parametrize(
    "digests",
    [
        [],
        ["notenarchiv-ci@" + DIGEST],
        [REPOSITORY + "@invalid"],
        [REPOSITORY + "@" + DIGEST, REPOSITORY + "@sha256:" + "b" * 64],
    ],
)
def test_missing_invalid_or_ambiguous_registry_digest_fails(digests):
    with pytest.raises(ValueError):
        registry_digest({"RepoDigests": digests}, REPOSITORY)


@pytest.fixture
def proof():
    return (
        {
            "head_sha": "original",
            "head_branch": "v0.1.0-preview.1",
            "event": "push",
            "path": ".github/workflows/release.yml",
            "status": "completed",
        },
        [
            {"name": name, "conclusion": "success"}
            for name in (
                "validate",
                "checks / Foundation (ruff + pytest)",
                "checks / Container (amd64 + security + synthetic smoke)",
            )
        ],
        [{"id": 1, "name": "verified-container", "expired": False, "digest": DIGEST}],
    )


def test_completed_checks_allow_reusing_the_original_artifact(proof):
    assert verify_candidate(*proof, "v0.1.0-preview.1", "original")["id"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("head_sha", "different"),
        ("head_branch", "main"),
        ("event", "pull_request"),
        ("path", ".github/workflows/ci.yml"),
        ("status", "in_progress"),
    ],
)
def test_recovery_rejects_another_source_or_workflow(proof, field, value):
    proof[0][field] = value
    with pytest.raises(ValueError):
        verify_candidate(*proof, "v0.1.0-preview.1", "original")


@pytest.mark.parametrize("index", [0, 1, 2])
def test_recovery_cannot_skip_original_checks(proof, index):
    proof[1][index]["conclusion"] = "skipped"
    with pytest.raises(ValueError):
        verify_candidate(*proof, "v0.1.0-preview.1", "original")


@pytest.mark.parametrize("problem", ["expired", "missing", "duplicate", "digest"])
def test_recovery_requires_one_intact_retained_artifact(proof, problem):
    artifact = proof[2][0]
    if problem == "expired":
        artifact["expired"] = True
    elif problem == "missing":
        proof[2].clear()
    elif problem == "duplicate":
        proof[2].append(artifact.copy())
    else:
        artifact["digest"] = "invalid"
    with pytest.raises(ValueError):
        verify_candidate(*proof, "v0.1.0-preview.1", "original")
