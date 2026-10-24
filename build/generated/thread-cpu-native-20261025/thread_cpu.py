"""Read CPU counters only for an explicitly owned Windows process.

Call sample(process.pid, process._desktop_handle) while the caller still owns
the live HiddenProcess and its desktop. The borrowed HDESK is never closed or
switched. This module starts no process/thread, writes no file, changes no
privilege, and retains no handles between calls. A PID alone is not ownership
proof: the caller must retain and check its original HiddenProcess handle.

Snapshots are sequential, not atomic. Match process identity and thread identity
before computing deltas. Missing/exited threads make coverage incomplete; do not
replace their counters by zero. CPU times are cumulative 100-ns durations, not
wall time. Cycles must not be converted to milliseconds. A window-owning thread
is not automatically the AIR/game/main thread. Top-level windows only are mapped.

Microsoft API contracts:
https://learn.microsoft.com/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes
https://learn.microsoft.com/windows/win32/api/realtimeapiset/nf-realtimeapiset-querythreadcycletime
https://learn.microsoft.com/windows/win32/api/tlhelp32/nf-tlhelp32-thread32first
https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-enumdesktopwindows
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import os
import time

VERSION = "owned-thread-cpu-1"
THREAD_QUERY_LIMITED_INFORMATION = 0x0800
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPTHREAD = 0x00000004
ERROR_NO_MORE_FILES = 18


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD),
                ("th32ThreadID", w.DWORD), ("th32OwnerProcessID", w.DWORD),
                ("tpBasePri", w.LONG), ("tpDeltaPri", w.LONG),
                ("dwFlags", w.DWORD)]


def _begin():
    return {"epochBeforeMs": time.time_ns() / 1_000_000,
            "monotonicBefore": time.monotonic(), "perfCounterBefore": time.perf_counter()}


def _end(record):
    record["perfCounterAfter"] = time.perf_counter()
    record["monotonicAfter"] = time.monotonic()
    record["epochAfterMs"] = time.time_ns() / 1_000_000
    # Some shipped Python versions use coarse GetTickCount64 for monotonic().
    record["elapsedMs"] = (record["perfCounterAfter"] - record["perfCounterBefore"]) * 1000


def _filetime(value):
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _api():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    u = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM, use_last_error=True)
    declarations = [
        (k.CloseHandle, [w.HANDLE], w.BOOL),
        (k.OpenProcess, [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        (k.GetProcessTimes, [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4, w.BOOL),
        (k.GetExitCodeProcess, [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        (k.CreateToolhelp32Snapshot, [w.DWORD, w.DWORD], w.HANDLE),
        (k.Thread32First, [w.HANDLE, ctypes.POINTER(THREADENTRY32)], w.BOOL),
        (k.Thread32Next, [w.HANDLE, ctypes.POINTER(THREADENTRY32)], w.BOOL),
        (k.OpenThread, [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        (k.GetProcessIdOfThread, [w.HANDLE], w.DWORD),
        (k.GetThreadTimes, [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4, w.BOOL),
        (k.QueryThreadCycleTime, [w.HANDLE, ctypes.POINTER(ctypes.c_uint64)], w.BOOL),
        (u.GetWindowThreadProcessId, [w.HWND, ctypes.POINTER(w.DWORD)], w.DWORD),
        (u.EnumDesktopWindows, [w.HANDLE, callback_type, w.LPARAM], w.BOOL),
    ]
    for function, args, result in declarations:
        function.argtypes, function.restype = args, result
    return k, u, callback_type


def sample(pid, desktop_handle):
    """Return a JSON-compatible dict; Win32 failures remain explicit in errors.

    Exact large counters/identities are decimal strings, suitable for JSON/JS.
    valid/complete require all queried counters, enumeration and cleanup to
    succeed. Individual successful rows are retained when a concurrent thread
    exit or API failure makes the whole observation incomplete.
    """
    out = _begin()
    out.update(version=VERSION, pid=pid if isinstance(pid, int) else None,
               valid=False, complete=False, process=None, threads=[], windows=[],
               errors=[], threadEnumeration={}, windowEnumeration={},
               cleanup={"handlesOpened": 0, "handlesClosed": 0, "closeErrors": []})
    k = None
    process_handle = snapshot_handle = None

    def error(stage, *, row=None, code=None, message=None, **extra):
        if code is None and message is None:
            code = ctypes.get_last_error()
        item = {"stage": stage, "winerror": code,
                "message": message if message is not None else ctypes.FormatError(code).strip(), **extra}
        out["errors"].append(item)
        if row is not None:
            row["errors"].append(item)
        return item

    def close(handle, kind):
        if handle:
            ctypes.set_last_error(0)
            if k.CloseHandle(handle):
                out["cleanup"]["handlesClosed"] += 1
            else:
                item = error("CloseHandle", kind=kind)
                out["cleanup"]["closeErrors"].append(item)

    def process_live(stage):
        code = w.DWORD()
        ctypes.set_last_error(0)
        if not k.GetExitCodeProcess(process_handle, ctypes.byref(code)):
            error(stage)
            return False
        if code.value != 259:  # STILL_ACTIVE; no wait/suspend/control access.
            error(stage, message="Owned process exited during sample", exitCode=code.value)
            return False
        return True

    try:
        if os.name != "nt":
            error("platform", message="Windows is required; no fallback enumeration")
            return out
        if isinstance(pid, bool) or not isinstance(pid, int) or not 0 < pid <= 0xFFFFFFFF:
            error("arguments", message="pid must be an explicit positive DWORD")
            return out
        desktop = getattr(desktop_handle, "value", desktop_handle)
        pointer_max = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
        if isinstance(desktop, bool) or not isinstance(desktop, int) or not 0 < desktop < pointer_max:
            error("arguments", message="A non-null borrowed owned desktop handle is required")
            return out
        out["desktopHandle"] = hex(desktop)
        k, u, callback_type = _api()
        ctypes.set_last_error(0)
        process_handle = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process_handle:
            error("OpenProcess")
            return out
        out["cleanup"]["handlesOpened"] += 1
        proc = _begin()
        creation, unused_exit, unused_kernel, unused_user = (w.FILETIME() for _ in range(4))
        ctypes.set_last_error(0)
        if not k.GetProcessTimes(process_handle, ctypes.byref(creation), ctypes.byref(unused_exit),
                                 ctypes.byref(unused_kernel), ctypes.byref(unused_user)):
            error("GetProcessTimes")
            return out
        proc.update(creationTime100ns=str(_filetime(creation)), identity=f"{pid}:{_filetime(creation)}")
        _end(proc)
        out["process"] = proc
        if not process_live("GetExitCodeProcess.before"):
            return out

        enumeration = out["threadEnumeration"] = _begin()
        enumeration.update(complete=False, matchedTids=[])
        ctypes.set_last_error(0)
        snapshot_handle = k.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if snapshot_handle == ctypes.c_void_p(-1).value or not snapshot_handle:
            snapshot_handle = None
            error("CreateToolhelp32Snapshot")
            return out
        out["cleanup"]["handlesOpened"] += 1
        try:
            entry = THREADENTRY32()
            entry.dwSize = ctypes.sizeof(entry)
            ctypes.set_last_error(0)
            found = k.Thread32First(snapshot_handle, ctypes.byref(entry))
            while found:
                required = THREADENTRY32.th32OwnerProcessID.offset + ctypes.sizeof(w.DWORD)
                if entry.dwSize < required:
                    error("THREADENTRY32", message="Truncated record lacks owner PID", size=entry.dwSize)
                    break
                if entry.th32OwnerProcessID == pid:
                    enumeration["matchedTids"].append(int(entry.th32ThreadID))
                entry.dwSize = ctypes.sizeof(entry)
                ctypes.set_last_error(0)
                found = k.Thread32Next(snapshot_handle, ctypes.byref(entry))
            else:
                last_error = ctypes.get_last_error()
                if last_error == ERROR_NO_MORE_FILES:
                    enumeration["complete"] = True
                else:
                    error("Thread32First/Next", code=last_error)
        finally:
            close(snapshot_handle, "snapshot")
            snapshot_handle = None
            _end(enumeration)

        window_enum = out["windowEnumeration"] = _begin()
        window_enum.update(complete=False)

        @callback_type
        def visit(hwnd, _):
            try:
                owner = w.DWORD()
                ctypes.set_last_error(0)
                tid = u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
                if not tid:
                    error("GetWindowThreadProcessId.enumerate", hwnd=hex(hwnd))
                elif owner.value == pid:
                    out["windows"].append({"hwnd": hex(hwnd), "tid": int(tid), "pid": pid,
                                           "threadIdentity": None, "ownerRevalidated": False})
                return True
            except Exception as exc:
                error("EnumDesktopWindows.callback", message=repr(exc))
                ctypes.set_last_error(995)  # ERROR_OPERATION_ABORTED
                return False

        ctypes.set_last_error(0)
        if u.EnumDesktopWindows(desktop, visit, 0):
            window_enum["complete"] = True
        else:
            code = ctypes.get_last_error()
            error("EnumDesktopWindows", code=code,
                  message="EnumDesktopWindows returned FALSE with no error code" if code == 0 else None)
        _end(window_enum)

        for tid in enumeration["matchedTids"]:
            row = _begin()
            row.update(tid=tid, pid=pid, identity=None, creationTime100ns=None,
                       kernel100ns=None, user100ns=None, kernelMs=None, userMs=None,
                       cycles=None, windowHandles=[], errors=[])
            out["threads"].append(row)
            thread_handle = None
            try:
                ctypes.set_last_error(0)
                thread_handle = k.OpenThread(THREAD_QUERY_LIMITED_INFORMATION, False, tid)
                if not thread_handle:
                    error("OpenThread", row=row, tid=tid)
                    continue
                out["cleanup"]["handlesOpened"] += 1
                ctypes.set_last_error(0)
                actual_pid = k.GetProcessIdOfThread(thread_handle)
                if not actual_pid:
                    error("GetProcessIdOfThread", row=row, tid=tid)
                    continue
                if actual_pid != pid:
                    error("thread-owner", row=row, tid=tid, message="TID reused by another process; counters not read")
                    continue
                created, ignored_exit, kernel, user = (w.FILETIME() for _ in range(4))
                ctypes.set_last_error(0)
                if k.GetThreadTimes(thread_handle, ctypes.byref(created), ctypes.byref(ignored_exit),
                                    ctypes.byref(kernel), ctypes.byref(user)):
                    # exitTime is undefined for a live thread and is deliberately not interpreted.
                    row.update(creationTime100ns=str(_filetime(created)),
                               identity=f"{pid}:{tid}:{_filetime(created)}",
                               kernel100ns=str(_filetime(kernel)), user100ns=str(_filetime(user)),
                               kernelMs=_filetime(kernel) / 10000, userMs=_filetime(user) / 10000)
                else:
                    error("GetThreadTimes", row=row, tid=tid)
                cycles = ctypes.c_uint64()
                ctypes.set_last_error(0)
                if k.QueryThreadCycleTime(thread_handle, ctypes.byref(cycles)):
                    row["cycles"] = str(cycles.value)
                else:
                    error("QueryThreadCycleTime", row=row, tid=tid)
                for window in out["windows"]:
                    if window["tid"] != tid:
                        continue
                    owner = w.DWORD()
                    ctypes.set_last_error(0)
                    actual_tid = u.GetWindowThreadProcessId(int(window["hwnd"], 16), ctypes.byref(owner))
                    if actual_tid == tid and owner.value == pid:
                        window["ownerRevalidated"] = True
                        window["threadIdentity"] = row["identity"]
                        row["windowHandles"].append(window["hwnd"])
                    else:
                        error("window-owner-recheck", row=row, tid=tid,
                              message="Window disappeared or changed owner during sample", hwnd=window["hwnd"])
            finally:
                close(thread_handle, "thread")
                _end(row)
        if not enumeration["matchedTids"]:
            error("thread-coverage", message="No owned threads in snapshot; not a zero-CPU sample")
        for window in out["windows"]:
            if not window["threadIdentity"]:
                error("window-thread-coverage", message="Window owner has no sampled thread identity",
                      hwnd=window["hwnd"], tid=window["tid"])
        process_live("GetExitCodeProcess.after")
    except Exception as exc:
        error("sample.exception", message=repr(exc))
    finally:
        if k is not None:
            close(snapshot_handle, "snapshot")
            close(process_handle, "process")
        out["complete"] = bool(not out["errors"] and out["threads"]
                               and out["threadEnumeration"].get("complete")
                               and out["windowEnumeration"].get("complete")
                               and out["cleanup"]["handlesOpened"] == out["cleanup"]["handlesClosed"])
        out["valid"] = out["complete"]
        _end(out)
    return out
