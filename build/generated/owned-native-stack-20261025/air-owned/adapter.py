"""SOURCE-ONLY preparation. No launch, no CLI, no PID attach, no process cleanup.

Bind the caller's freshly created air_test_process.HiddenProcess. Retain only
owned thread handles; the existing runner owns process/desktop termination.
"""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import hashlib
import inspect
import os
from pathlib import Path
import struct
import sys
import time
import types

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parent / "owned_native_stack.py"
CORE_SHA256 = "91694dd28f399bc198051c50438897bc3165783d658ca8c896124b76ae4515e7"
core_source = CORE_PATH.read_bytes()
if hashlib.sha256(core_source).hexdigest() != CORE_SHA256:
    raise RuntimeError("Reviewed native sampler core changed")
N = types.ModuleType("owned_native_stack_source_only")
N.__file__ = str(CORE_PATH)
exec(compile(core_source, str(CORE_PATH), "exec"), N.__dict__)

ROOT = HERE.parents[5]
HIDDEN_PROCESS_SOURCE = ROOT / "mods/ModLoader/tools/air_test_process.py"
U32, U64, PTR = N.U32, N.U64, N.PTR
GetSystemTimePreciseAsFileTime = N.api("GetSystemTimePreciseAsFileTime", None, PTR)
CreateToolhelp32Snapshot = N.api("CreateToolhelp32Snapshot", PTR, U32, U32)
Thread32First = N.api("Thread32First", W.BOOL, PTR, PTR)
Thread32Next = N.api("Thread32Next", W.BOOL, PTR, PTR)
Process32FirstW = N.api("Process32FirstW", W.BOOL, PTR, PTR)
Process32NextW = N.api("Process32NextW", W.BOOL, PTR, PTR)
USER = C.WinDLL("user32", use_last_error=True)
USER.GetThreadDesktop.argtypes, USER.GetThreadDesktop.restype = [U32], PTR
USER.GetUserObjectInformationW.argtypes = [PTR, C.c_int, PTR, U32, PTR]
USER.GetUserObjectInformationW.restype = W.BOOL


class THREADENTRY32(C.Structure):
    _fields_ = [("dwSize", U32), ("cntUsage", U32), ("th32ThreadID", U32),
                ("th32OwnerProcessID", U32), ("tpBasePri", C.c_long),
                ("tpDeltaPri", C.c_long), ("dwFlags", U32)]


class PROCESSENTRY32W(C.Structure):
    _fields_ = [("dwSize", U32), ("cntUsage", U32), ("th32ProcessID", U32),
                ("th32DefaultHeapID", C.c_size_t), ("th32ModuleID", U32),
                ("cntThreads", U32), ("th32ParentProcessID", U32),
                ("pcPriClassBase", C.c_long), ("dwFlags", U32), ("szExeFile", W.WCHAR * 260)]


class SamplerFatalError(RuntimeError):
    """Must escape motion-test's OSError-only CPU catch into owned-process finally."""
    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence = evidence


class _OwnedProcessExited(RuntimeError):
    """Expected lifecycle race, not an ownership mismatch."""


def stamp():
    ft = U64()
    GetSystemTimePreciseAsFileTime(C.byref(ft))
    return {"epoch_filetime_100ns": ft.value, "perf_ns": time.perf_counter_ns()}


def desktop_name(handle):
    name, needed = C.create_unicode_buffer(512), U32()
    N.checked(USER.GetUserObjectInformationW(handle, 2, name, C.sizeof(name), C.byref(needed)),
              "GetUserObjectInformationW(UOI_NAME)")
    return name.value


def parent_pid(pid):
    # Only snapshot metadata; never opens another process.
    h = CreateToolhelp32Snapshot(2, 0)
    if h == C.c_void_p(-1).value:
        raise OSError(C.get_last_error(), "process metadata snapshot")
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = C.sizeof(entry)
        ok = Process32FirstW(h, C.byref(entry))
        while ok:
            if entry.th32ProcessID == pid:
                return int(entry.th32ParentProcessID)
            ok = Process32NextW(h, C.byref(entry))
        raise RuntimeError("owned process missing from metadata snapshot")
    finally:
        N.CloseHandle(h)


class OwnedAirSampler:
    def __init__(self, process, expected_exe, expected_descriptor):
        self.process = process
        self.handle = None
        self.identity = None
        self.threads = []
        self.images = None
        self.closed = False
        self.fatal = False
        self.prepared = False
        self.stopped = False
        self.lifecycle_events = []
        self.cursor = 0
        self.sample_limit = 160
        self.samples = []
        self.errors = []
        self.inventory_checks = []
        self.prepare_record = None
        self.binding_started = stamp()
        self.last_inventory_sample_count = 0
        try:
            mod = sys.modules.get("air_test_process")
            if mod is None or type(process) is not getattr(mod, "HiddenProcess", None):
                raise RuntimeError("must pass exact caller-created HiddenProcess object")
            source = Path(inspect.getsourcefile(type(process))).resolve(strict=True)
            if source != HIDDEN_PROCESS_SOURCE.resolve(strict=True):
                raise RuntimeError("HiddenProcess implementation source mismatch")
            self.handle = int(process._process)
            if not self.handle or not process._desktop_handle or process.poll() is not None:
                raise RuntimeError("fresh owned handles required")
            expected_exe = Path(expected_exe).resolve(strict=True)
            expected_descriptor = Path(expected_descriptor).resolve(strict=True)
            if expected_exe.name.lower() != "adl64.exe" or expected_descriptor.suffix.lower() != ".xml":
                raise RuntimeError("explicit adl64 and XML descriptor required")
            command = list(process.command)
            if not command or Path(command[0]).resolve(strict=True) != expected_exe:
                raise RuntimeError("owned launch command executable mismatch")
            if Path(command[-1]).resolve(strict=True) != expected_descriptor:
                raise RuntimeError("owned launch descriptor mismatch")
            pid = N.GetProcessId(self.handle)
            creation = N.times(self.handle, N.GetProcessTimes)[0]
            now = stamp()
            if pid != process.pid or not 0 <= now["epoch_filetime_100ns"] - creation <= 150_000_000:
                raise RuntimeError("bind within 15 seconds of this child's creation")
            if parent_pid(pid) != os.getpid():
                raise RuntimeError("target was not created by this runner process")
            image, length = C.create_unicode_buffer(32768), U32(32768)
            N.checked(N.QueryFullProcessImageNameW(self.handle, 0, image, C.byref(length)), "owned image")
            if Path(image.value).resolve(strict=True) != expected_exe:
                raise RuntimeError("OS executable path differs from expected adl64")
            process_machine, native_machine = N.U16(), N.U16()
            N.checked(N.IsWow64Process2(self.handle, C.byref(process_machine), C.byref(native_machine)), "AMD64")
            if process_machine.value or native_machine.value != 0x8664:
                raise RuntimeError("only native AMD64 target supported")
            actual_desktop = desktop_name(process._desktop_handle)
            if not process.desktop.startswith("RemainsTest-") or actual_desktop != process.desktop:
                raise RuntimeError("private owned desktop name mismatch")
            self.identity = {"pid": pid, "creation_filetime": creation, "image": image.value,
                "descriptor": str(expected_descriptor), "command": command, "parent_pid": os.getpid(),
                "desktop": actual_desktop, "original_process_handle": self.handle,
                "original_desktop_handle": int(process._desktop_handle), "bound_at": now,
                "hidden_process_source": str(source),
                "hidden_process_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "native_core_sha256": CORE_SHA256}
            self.verify()
        except Exception as error:
            self._raise("bind", error)

    def _raise(self, phase, error, evidence=None):
        event = {"phase": phase, "at": stamp(), "error": repr(error), "evidence": evidence}
        self.errors.append(event)
        self.fatal = True
        raise SamplerFatalError("Owned native sampler failed at " + phase, event) from error

    def verify(self, thread=None):
        if self.closed or self.fatal:
            raise RuntimeError("sampler closed or in fatal state")
        if not self.identity or int(self.process._process or 0) != self.handle:
            raise RuntimeError("original owned process handle changed")
        if self.process.poll() is not None:
            raise _OwnedProcessExited("owned process exited during observer callback")
        if N.GetProcessId(self.handle) != self.identity["pid"]:
            raise RuntimeError("owned process PID mismatch")
        if N.times(self.handle, N.GetProcessTimes)[0] != self.identity["creation_filetime"]:
            raise RuntimeError("process creation FILETIME mismatch")
        if int(self.process._desktop_handle or 0) != self.identity["original_desktop_handle"] or self.process.desktop != self.identity["desktop"]:
            raise RuntimeError("original owned desktop changed")
        if thread:
            h = thread["handle"]
            if N.GetProcessIdOfThread(h) != self.identity["pid"] or N.GetThreadId(h) != thread["tid"]:
                raise RuntimeError("thread owner/TID mismatch")
            if N.times(h, N.GetThreadTimes)[0] != thread["creation_filetime"]:
                raise RuntimeError("thread creation FILETIME mismatch")
            if N.WaitForSingleObject(h, 0) != 258:
                raise RuntimeError("selected thread no longer running")
            if "desktop" in thread:
                desktop = USER.GetThreadDesktop(thread["tid"])
                N.checked(desktop, "recheck owned thread desktop")
                if desktop_name(desktop) != self.identity["desktop"]:
                    raise RuntimeError("selected owned thread changed desktop")

    def _exit_code(self):
        # Exit is classified only while retained handle/PID/FILETIME still identify our child.
        if int(self.process._process or 0) != self.handle:
            return None
        if N.GetProcessId(self.handle) != self.identity["pid"]:
            return None
        if N.times(self.handle, N.GetProcessTimes)[0] != self.identity["creation_filetime"]:
            return None
        return self.process.poll()

    def _record_exit(self, phase, detail=None):
        self.stopped = True
        event = {"phase": phase, "at": stamp(), "reason": "owned-process-exited",
                 "exit_code": self._exit_code(), "detail": detail}
        self.lifecycle_events.append(event)
        return event

    def prepare(self):
        if self.prepared:
            raise RuntimeError("prepare may run only once")
        event = {"started": stamp()}
        snapshot = None
        try:
            self.verify()
            snapshot = CreateToolhelp32Snapshot(4, 0)
            if snapshot == C.c_void_p(-1).value:
                snapshot = None
                raise OSError(C.get_last_error(), "thread snapshot")
            entry = THREADENTRY32()
            entry.dwSize = C.sizeof(entry)
            ok = Thread32First(snapshot, C.byref(entry))
            while ok:
                if entry.th32OwnerProcessID == self.identity["pid"]:
                    tid = int(entry.th32ThreadID)
                    h = N.OpenThread(0x0002 | 0x0008 | 0x0040 | 0x00100000, False, tid)
                    N.checked(h, "OpenThread for owned PID")
                    t = {"handle": h, "tid": tid, "retired": False, "previous_cpu": None}
                    self.threads.append(t)  # close() owns h even if subsequent checks fail.
                    t["creation_filetime"] = N.times(h, N.GetThreadTimes)[0]
                    self.verify(t)
                    desktop = USER.GetThreadDesktop(tid)
                    N.checked(desktop, "GetThreadDesktop for owned thread")
                    t["desktop"] = desktop_name(desktop)
                    if t["desktop"] != self.identity["desktop"]:
                        raise RuntimeError("owned thread not on launch private desktop")
                ok = Thread32Next(snapshot, C.byref(entry))
            if C.get_last_error() != 18:
                raise OSError(C.get_last_error(), "Thread32Next stopped unexpectedly")
            if not self.threads:
                raise RuntimeError("owned process had no eligible threads")
            self.threads.sort(key=lambda t: t["tid"])
            self.images = N.LocalImages(self)
            event.update(thread_count=len(self.threads), module_count=len(self.images.inventory),
                image_cache_bytes=self.images.bytes, image_cache_limit=N.MAX_MODULE_CACHE,
                image_cache_limit_is_process_memory_cap=False,
                runtime_function_tables=len(self.images.tables), image_cache_errors=self.images.failures)
            self.prepared = True
            self._inventory_check("after-prepare")
            return event
        except _OwnedProcessExited as error:
            event["process_exited"] = self._record_exit("prepare", repr(error))
            self.close()
            return event
        except Exception as error:
            if self._exit_code() is not None:
                event["process_exited"] = self._record_exit("prepare-race", repr(error))
                self.close()
                return event
            self.close()  # release partial OpenThread ownership even before caller's finally.
            self._raise("prepare", error, event)
        finally:
            if snapshot:
                N.CloseHandle(snapshot)
            event["ended"] = stamp()
            event["wall_ms"] = (event["ended"]["perf_ns"] - event["started"]["perf_ns"]) / 1e6
            self.prepare_record = event

    def _inventory_check(self, reason):
        event = {"reason": reason, "started": stamp(), "after_samples": len(self.samples)}
        self.verify()
        current = N.modules(self.handle)
        event["same_as_cache"] = current == self.images.inventory
        event["ended"] = stamp()
        event["wall_ms"] = (event["ended"]["perf_ns"] - event["started"]["perf_ns"]) / 1e6
        self.inventory_checks.append(event)
        if not event["same_as_cache"]:
            event["actual_inventory"] = current
            event["invalidated_indices"] = list(range(self.last_inventory_sample_count, len(self.samples)))
            for s in self.samples[self.last_inventory_sample_count:]:
                s["module_mapping_qualified"] = False
                s["mapping_reason"] = "module list changed after previous successful check"
            self._raise("module-inventory-change", RuntimeError("cached module mapping is stale"), event)
        self.last_inventory_sample_count = len(self.samples)

    def _capture(self, t):
        self.verify(t)
        h = t["handle"]
        storage, context = N.aligned_context()
        stack, count, mbi = C.create_string_buffer(N.MAX_STACK), C.c_size_t(), N.MBI()
        s = {"index": len(self.samples), "tid": t["tid"], "thread_creation_filetime": t["creation_filetime"],
             "started": stamp(), "max_stack_bytes": N.MAX_STACK, "suspend_calls": 0, "resume_calls": 0,
             "module_mapping_qualified": None,
             "mapping_reason": "cache stable at last recorded check; not a per-sample mapping guarantee"}
        self.samples.append(s)  # partial evidence survives any fatal error.
        s["cpu_before_at"] = stamp()
        before = N.times(h, N.GetThreadTimes)
        s["cpu_before"] = {"kernel_100ns": before[2], "user_100ns": before[3]}
        if t["previous_cpu"]:
            p = t["previous_cpu"]
            s["cpu_since_previous"] = {"from": p["at"], "to": s["cpu_before_at"],
                "kernel_100ns": before[2] - p["kernel"], "user_100ns": before[3] - p["user"]}
        prior = resumed = None
        suspended = False
        capture_error = None
        suspend_started = time.perf_counter_ns()
        try:
            s["suspend_calls"] += 1
            prior = N.SuspendThread(h)
            if prior == N.INVALID:
                raise OSError(C.get_last_error(), "SuspendThread failed")
            suspended = True
            if prior != 0:
                raise RuntimeError("preexisting suspension; only undo our increment and abort")
            N.checked(N.GetThreadContext(h, context), "GetThreadContext")
            rsp = U64.from_address(context + 152).value
            rip = U64.from_address(context + 248).value
            if N.VirtualQueryEx(self.handle, rsp, C.byref(mbi), C.sizeof(mbi)) != C.sizeof(mbi):
                raise OSError(C.get_last_error(), "stack VirtualQueryEx")
            if mbi.State != 0x1000 or mbi.Protect & 0x101:
                raise RuntimeError("stack region unavailable/guarded")
            size = min(N.MAX_STACK, int(mbi.BaseAddress) + mbi.RegionSize - rsp)
            if size <= 0:
                raise RuntimeError("invalid stack region bounds")
            N.checked(N.ReadProcessMemory(self.handle, rsp, stack, size, C.byref(count)), "stack read")
            if count.value != size:
                raise RuntimeError("partial stack read")
        except BaseException as error:
            capture_error = error
        finally:
            if suspended:
                s["resume_calls"] += 1
                resumed = N.ResumeThread(h)  # one and only one, never a resume-to-zero loop.
                if resumed == N.INVALID:
                    s["resume_winerror"] = C.get_last_error()
            ended = time.perf_counter_ns()
            s.update(suspend_previous=prior, resume_previous=resumed,
                     suspension_ms=(ended - suspend_started) / 1e6, stack_bytes=count.value)
        if suspended and resumed != prior + 1:
            if self._exit_code() is not None:
                s["resume_balance_unverifiable_target_exited"] = True
                s["capture_error"] = repr(capture_error) if capture_error else None
                raise _OwnedProcessExited("target exited before resume could be confirmed; partial counts preserved")
            self._raise("resume", RuntimeError("could not prove balanced suspension"), s)
        if capture_error is not None:
            s["capture_error"] = repr(capture_error)
            if self._exit_code() is not None:
                raise _OwnedProcessExited("owned process exited during capture; partial evidence preserved")
            self._raise("capture", capture_error, s)
        self.verify(t)
        after = N.times(h, N.GetThreadTimes)
        s["cpu_after_at"] = stamp()
        s["cpu_after"] = {"kernel_100ns": after[2], "user_100ns": after[3]}
        t["previous_cpu"] = {"at": s["cpu_after_at"], "kernel": after[2], "user": after[3]}
        temporary = {"rip": rip, "rsp": rsp, "context": C.string_at(context, 1232),
                     "stack": stack.raw[:count.value]}
        s["rip"], s["rsp"] = hex(rip), hex(rsp)
        s["walk_started"] = stamp()
        try:
            s["walk"] = N.unwind(temporary, self.images)
        except Exception as error:
            s["walk"] = {"frames": [self.images.location(rip)], "status": "IP-only-walk-error", "error": repr(error)}
            self.errors.append({"phase": "offline-unwind", "at": stamp(), "error": repr(error), "sample_index": s["index"]})
        s["ended"] = stamp()
        s["wall_ms"] = (s["ended"]["perf_ns"] - s["started"]["perf_ns"]) / 1e6
        s["walk_wall_ms"] = (s["ended"]["perf_ns"] - s["walk_started"]["perf_ns"]) / 1e6
        return s

    def sample(self, max_threads=2):
        if max_threads not in (1, 2):
            raise ValueError("sample max_threads must be 1 or 2")
        batch = {"started": stamp(), "samples": [], "skipped": []}
        try:
            if self.stopped:
                batch["stop_sampling"] = True
                batch["process_exited"] = True
                return batch
            if not self.prepared:
                raise RuntimeError("prepare must precede sample")
            self.verify()
            if len(self.samples) >= self.sample_limit:
                batch["limit_reached"] = True
                return batch
            if len(self.samples) - self.last_inventory_sample_count >= 16:
                self._inventory_check("bounded-16-sample-recheck")
            scanned = 0
            while len(batch["samples"]) < max_threads and scanned < len(self.threads) and len(self.samples) < self.sample_limit:
                t = self.threads[self.cursor % len(self.threads)]
                self.cursor += 1
                scanned += 1
                if t["retired"]:
                    continue
                status = N.WaitForSingleObject(t["handle"], 0)
                if status == 0:
                    t["retired"] = True
                    event = {"tid": t["tid"], "at": stamp(), "reason": "owned thread exited; persistent handle retired"}
                    t["retirement"] = event
                    batch["skipped"].append(event)
                    continue
                if status != 258:
                    raise OSError(C.get_last_error(), "thread exit-state query failed")
                batch["samples"].append(self._capture(t))
            if not batch["samples"]:
                batch["no_live_prepared_threads"] = True
            return batch
        except _OwnedProcessExited as error:
            batch["lifecycle_event"] = self._record_exit("sample", repr(error))
            batch["process_exited"] = True
            batch["stop_sampling"] = True
            return batch
        except SamplerFatalError:
            raise
        except Exception as error:
            if self._exit_code() is not None:
                batch["lifecycle_event"] = self._record_exit("sample-race", repr(error))
                batch["process_exited"] = True
                batch["stop_sampling"] = True
                return batch
            self._raise("sample", error, batch)
        finally:
            batch["ended"] = stamp()
            batch["wall_ms"] = (batch["ended"]["perf_ns"] - batch["started"]["perf_ns"]) / 1e6

    def summary(self):
        # Pure local snapshot: safe after the runner has stopped/closed its process.
        return {"identity": self.identity, "prepare": self.prepare_record,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "initial_modules": self.images.inventory if self.images else [],
            "inventory_checks": self.inventory_checks,
            "last_successful_inventory_check": next((e for e in reversed(self.inventory_checks) if e.get("same_as_cache")), None),
            "thread_identities": [{k: v for k, v in t.items() if k not in ("handle", "previous_cpu")} for t in self.threads],
            "samples": self.samples, "errors": self.errors, "fatal": self.fatal, "closed": self.closed,
            "stopped": self.stopped, "lifecycle_events": self.lifecycle_events,
            "sample_limit": self.sample_limit, "performance_acceptance": False,
            "new_threads_after_prepare_observed": False, "symbols_used": False,
            "limitations": ["Wall-clock snapshots are not CPU shares or GPU evidence.",
                "Image mapping checked after prepare and at most every 16 samples; no claim that it was unchanged between checks or until process exit.",
                "No new-thread discovery after prepare; exited handles retire without reattachment.",
                "Unknown/JIT addresses stop unwind; function roles and names are not inferred.",
                "Module read-only images are a bounded cache, not an atomic process snapshot."]}

    def close(self):
        # No process calls, no desktop calls, no Resume calls: capture balanced its own suspension.
        for t in self.threads:
            if t.get("handle"):
                if not N.CloseHandle(t["handle"]):
                    self.errors.append({"phase": "thread-handle-close", "tid": t["tid"],
                                        "at": stamp(), "winerror": C.get_last_error()})
                t["handle"] = None
        self.closed = True


if __name__ == "__main__":
    raise SystemExit("Source-only adapter. Caller must supply its newly created HiddenProcess; no CLI is supported.")
