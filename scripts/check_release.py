"""Only prereleases are publishable until full acceptance is approved (WP-53)."""

import re
import sys


def validate_tag(tag):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+-(preview|rc)\.[1-9][0-9]*", tag):
        raise ValueError("Only versioned preview/rc tags are permitted before full acceptance")
    return tag[1:]


if __name__ == "__main__":
    validate_tag(sys.argv[1])
