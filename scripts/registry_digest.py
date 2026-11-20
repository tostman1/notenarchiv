"""Select the published repository digest without relying on list order."""

import json
import re
import sys


def registry_digest(metadata, repository):
    pattern = re.escape(repository) + r"@sha256:[0-9a-f]{64}"
    matches = {value for value in metadata.get("RepoDigests", []) if re.fullmatch(pattern, value)}
    if len(matches) != 1:
        raise ValueError("Exactly one digest for the published repository is required")
    return matches.pop()


if __name__ == "__main__":
    sys.stdout.write(registry_digest(json.load(sys.stdin)[0], sys.argv[1]) + "\n")
