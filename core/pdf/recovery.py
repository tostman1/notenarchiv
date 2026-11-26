"""Prune only owned abandoned parser files, under exclusive dead-worker ownership."""

import logging
import os
import re
import stat

from core import files

logger = logging.getLogger(__name__)
PARSER_ACTIVE_MARKER = "parser-active"


def prune_disposable(root, directory):
    """Discard parser scratch under the same lock required by prune."""
    try:
        prune(root, directory)
    except FileNotFoundError:
        pass
    except (files.FileError, OSError):
        logger.warning("Could not safely prune disposable PDF processing workspaces")


def prune(root, directory):
    """Caller must hold the worker lifetime lock; children must have stopped."""
    with root.parent(directory + "/placeholder") as (parent, _):
        with os.scandir(parent) as entries:
            names = []
            for entry in entries:
                if len(names) >= 1000 or not re.fullmatch(r"pdf-[a-zA-Z0-9_-]+", entry.name):
                    raise files.FileError("UNSAFE_STAGING")
                names.append(entry.name)
        for name in names:
            with root.parent(directory + "/" + name + "/placeholder") as (child, _):
                try:
                    os.stat(PARSER_ACTIVE_MARKER, dir_fd=child, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    continue
                with os.scandir(child) as entries:
                    children = []
                    for entry in entries:
                        info = entry.stat(follow_symlinks=False)
                        if (
                            len(children) >= 1004
                            or not re.fullmatch(r"[0-9]+\.pdf|request\.json|response\.json|output", entry.name)
                            or not stat.S_ISREG(info.st_mode)
                            or info.st_uid != os.geteuid()
                            or info.st_nlink != 1
                        ):
                            raise files.FileError("UNSAFE_STAGING")
                        children.append((entry.name, files.identity(info)))
                for filename, identity in children:
                    if files.identity(os.stat(filename, dir_fd=child, follow_symlinks=False)) != identity:
                        raise files.FileError("STAGING_CHANGED")
                    os.unlink(filename, dir_fd=child)
            os.rmdir(name, dir_fd=parent)
