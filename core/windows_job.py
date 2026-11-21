"""Owned Windows process-tree containment (nested Job Objects, Windows 8+).

Microsoft contract: https://learn.microsoft.com/windows/win32/procthread/job-objects
The launcher waits for input until assignment, closing the child-spawn race.
"""

import ctypes
import time
from ctypes import wintypes


class WindowsJob:
    def __init__(self, *, memory_bytes=None, cpu_seconds=None):
        class Basic(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_longlong),
                ("job_time", ctypes.c_longlong),
                ("flags", wintypes.DWORD),
                ("min_set", ctypes.c_size_t),
                ("max_set", ctypes.c_size_t),
                ("active_limit", wintypes.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD),
            ]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", ctypes.c_ulonglong * 6), ("memory", ctypes.c_size_t * 4)]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "QueryInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p],
                wintypes.BOOL,
            ),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("Cannot create process containment")
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway.
        if memory_bytes is not None:
            limits.basic.flags |= 0x200  # JOB_OBJECT_LIMIT_JOB_MEMORY
            limits.memory[1] = memory_bytes
        if cpu_seconds is not None:
            limits.basic.flags |= 0x4  # JOB_OBJECT_LIMIT_JOB_TIME (100 ns units)
            limits.basic.job_time = cpu_seconds * 10_000_000
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.api.CloseHandle(self.handle)
            raise OSError("Cannot configure process containment")

    def assign(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError("Cannot contain child process")

    def stop(self):
        class Accounting(ctypes.Structure):
            _fields_ = [
                ("times", ctypes.c_longlong * 4),
                ("faults", wintypes.DWORD),
                ("total", wintypes.DWORD),
                ("active", wintypes.DWORD),
                ("terminated", wintypes.DWORD),
            ]

        try:
            if not self.api.TerminateJobObject(self.handle, 1):
                raise OSError("Cannot terminate process tree")
            deadline = time.monotonic() + 5
            while True:
                info = Accounting()
                if not self.api.QueryInformationJobObject(
                    self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None
                ):
                    raise OSError("Cannot verify process termination")
                if info.active == 0:
                    return
                if time.monotonic() >= deadline:
                    raise OSError("Process tree did not stop")
                time.sleep(0.01)
        finally:
            self.api.CloseHandle(self.handle)
