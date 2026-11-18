"""Windows process list and per-process IO counters via ctypes (no extra packages)."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes as wt

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.GetProcessIoCounters.argtypes = [wt.HANDLE, ctypes.POINTER(IO_COUNTERS)]
kernel32.CloseHandle.argtypes = [wt.HANDLE]


def list_processes() -> list[tuple[int, str]]:
    """(pid, exe_name) for every running process."""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wt.HANDLE(-1).value or not snap:
        return []
    out: list[tuple[int, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return []
        while True:
            out.append((int(entry.th32ProcessID), entry.szExeFile))
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return out


def find_processes(exe_names: set[str]) -> list[tuple[int, str]]:
    """(pid, name) pairs matching the given executable names."""
    names = {n.lower() for n in exe_names}
    return [(pid, name) for pid, name in list_processes() if name.lower() in names]


def find_pids(exe_names: set[str]) -> list[int]:
    return [pid for pid, _ in find_processes(exe_names)]


def io_counters(pid: int) -> tuple[int, int, int] | None:
    """(bytes read, bytes written, other bytes) for the given process."""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        counters = IO_COUNTERS()
        if not kernel32.GetProcessIoCounters(handle, ctypes.byref(counters)):
            return None
        return (
            int(counters.ReadTransferCount),
            int(counters.WriteTransferCount),
            int(counters.OtherTransferCount),
        )
    finally:
        kernel32.CloseHandle(handle)


class ProcessActivity:
    """Derives per-second IO rates from cumulative process counters.

    Used only as a *supporting* signal (display + extra evidence that data is
    still moving). The authoritative signal is Steam's own state machine.
    """

    def __init__(self) -> None:
        self._prev: dict[str, tuple[float, int, int, int]] = {}

    def sample(self, exe_names: set[str]) -> dict[str, dict]:
        now = time.time()
        result: dict[str, dict] = {}
        for pid, exe in find_processes(exe_names):
            counters = io_counters(pid)
            if not counters:
                continue
            key = exe.lower()
            prev = self._prev.get(key)
            if prev is None:
                write_bps = read_bps = 0.0
            else:
                dt = max(0.5, now - prev[0])
                write_bps = max(0, counters[1] - prev[2]) / dt
                read_bps = max(0, counters[0] - prev[1]) / dt
            self._prev[key] = (now, counters[0], counters[1], counters[2])
            result[exe] = {
                "pid": pid,
                "write_bps": write_bps,
                "read_bps": read_bps,
                "total_write": counters[1],
                "alive": True,
            }
        return result

    def forget(self, names: set[str]) -> None:
        for name in names:
            self._prev.pop(name.lower(), None)
