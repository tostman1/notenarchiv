"""A stable OS lock inode prevents duplicate local publisher processes."""

import os
import stat
import threading


class ProcessLock:
    def __init__(self, path):
        self.path = path
        self.stream = None
        self.owner = None

    def __enter__(self):
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(self.path, flags, 0o600)
        self.stream = os.fdopen(fd, "a+b")
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("Process lock must be a regular file")
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.stream.close()
            raise
        self.owner = (os.getpid(), threading.get_ident())
        return self

    def assert_owned(self):
        if self.owner != (os.getpid(), threading.get_ident()) or self.stream is None or self.stream.closed:
            raise RuntimeError("Publisher process ownership is required")

    def __exit__(self, *exception):
        self.owner = None
        self.stream.close()
