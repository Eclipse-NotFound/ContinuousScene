"""Source-only owned AIR IP observer. No launch, attach, stack copy or unwind.

Reuses the hash-pinned v2 identity/lifecycle/handle-cleanup implementation.
Overrides preparation, selection, capture and report. No game was run here.
"""
from __future__ import annotations

import ctypes as C
import hashlib
from pathlib import Path
import time
import types

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "air-owned-v2/adapter.py"
BASE_SHA256 = "50211888bd0573646bb7be8a125c58a70600ecf6569f18489f41b89b18de01a6"
base_bytes = BASE_PATH.read_bytes()
if hashlib.sha256(base_bytes).hexdigest() != BASE_SHA256:
    raise RuntimeError("Frozen v2 ownership/lifecycle source changed")
V = types.ModuleType("owned_air_v2_frozen_base")
V.__file__ = str(BASE_PATH)
exec(compile(base_bytes, str(BASE_PATH), "exec"), V.__dict__)
N = V.N
stamp = V.stamp
SamplerFatalError = V.SamplerFatalError
_OwnedProcessExited = V._OwnedProcessExited


class OwnedAirSampler(V.OwnedAirSampler):
    def __init__(self, process, expected_exe, expected_descriptor):
        super().__init__(process, expected_exe, expected_descriptor)
        self.initial_modules = []
        self.cpu_batches = []
        self.ip_count = 0
        self.activity_cursor = 0
        self.last_inventory_ip_count = 0
        self.last_inventory_sample_index = 0

    def prepare(self):
        if self.prepared:
            raise RuntimeError("prepare may run only once")
        event = {"started": stamp(), "ip_only": True, "module_bytes_read": 0,
                 "stack_bytes_read": 0, "unwind_calls": 0}
        snapshot = None
        try:
            self.verify()
            snapshot = V.CreateToolhelp32Snapshot(4, 0)
            if snapshot == C.c_void_p(-1).value:
                snapshot = None
                raise OSError(C.get_last_error(), "thread snapshot")
            entry = V.THREADENTRY32()
            entry.dwSize = C.sizeof(entry)
            ok = V.Thread32First(snapshot, C.byref(entry))
            while ok:
                if entry.th32OwnerProcessID == self.identity["pid"]:
                    h = N.OpenThread(0x0002 | 0x0008 | 0x0040 | 0x00100000, False, entry.th32ThreadID)
                    N.checked(h, "OpenThread for owned PID")
                    t = {"handle": h, "tid": int(entry.th32ThreadID), "retired": False,
                         "previous_cpu": None, "previous_delta_100ns": None}
                    self.threads.append(t)
                    t["creation_filetime"] = N.times(h, N.GetThreadTimes)[0]
                    self.verify(t)
                ok = V.Thread32Next(snapshot, C.byref(entry))
            if C.get_last_error() != 18:
                raise OSError(C.get_last_error(), "thread snapshot stopped unexpectedly")
            if not self.threads:
                raise RuntimeError("owned process had no prepared threads")
            self.threads.sort(key=lambda t: t["tid"])
            self.initial_modules = N.modules(self.handle)  # metadata only, no module memory.
            event.update(thread_count=len(self.threads), module_count=len(self.initial_modules),
                         thread_enumerations=1, new_thread_discovery=False)
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
            self.close()
            self._raise("prepare", error, event)
        finally:
            if snapshot:
                N.CloseHandle(snapshot)
            event["ended"] = stamp()
            event["wall_ms"] = (event["ended"]["perf_ns"] - event["started"]["perf_ns"]) / 1e6
            self.prepare_record = event

    def _inventory_check(self, reason):
        event = {"reason": reason, "started": stamp(), "after_samples": len(self.samples),
                 "after_ip_samples": self.ip_count}
        self.verify()
        current = N.modules(self.handle)
        event["same_as_initial"] = current == self.initial_modules
        event["ended"] = stamp()
        event["wall_ms"] = (event["ended"]["perf_ns"] - event["started"]["perf_ns"]) / 1e6
        self.inventory_checks.append(event)
        if not event["same_as_initial"]:
            event["actual_inventory"] = current
            event["invalidated_indices"] = list(range(self.last_inventory_sample_index, len(self.samples)))
            for s in self.samples[self.last_inventory_sample_index:]:
                s["module_mapping_qualified"] = False
                s["mapping_reason"] = "module inventory changed after previous check"
            self._raise("module-inventory-change", RuntimeError("initial module mapping stale"), event)
        self.last_inventory_ip_count = self.ip_count
        self.last_inventory_sample_index = len(self.samples)

    def _cpu_scan(self):
        batch = {"index": len(self.cpu_batches), "started": stamp(), "threads": [],
                 "scope": "initial-persistent-handles-only", "new_threads_observed": False}
        self.cpu_batches.append(batch)  # retain partial evidence on any error.
        try:
            self.verify()
            p = N.times(self.handle, N.GetProcessTimes)
            batch["process_cpu_before"] = {"at": stamp(), "kernel_100ns": p[2], "user_100ns": p[3]}
            for t in self.threads:
                row = {"tid": t["tid"], "creation_filetime": t["creation_filetime"],
                       "read_started": stamp(), "selected": False}
                batch["threads"].append(row)
                if t["retired"]:
                    row.update(status="retired-no-reread", retirement=t.get("retirement"),
                               read_ended=stamp(), delta_100ns=None)
                    continue
                h = t["handle"]
                try:
                    if N.GetProcessIdOfThread(h) != self.identity["pid"] or N.GetThreadId(h) != t["tid"]:
                        raise RuntimeError("CPU scan persistent thread owner/TID mismatch")
                    status = N.WaitForSingleObject(h, 0)
                    if status not in (0, 258):
                        raise OSError(C.get_last_error(), "CPU thread exit-state query")
                    raw = N.times(h, N.GetThreadTimes)
                    if raw[0] != t["creation_filetime"]:
                        raise RuntimeError("CPU scan thread creation FILETIME mismatch")
                    row.update(read_ended=stamp(), kernel_100ns=raw[2], user_100ns=raw[3],
                               previous_delta_100ns=t["previous_delta_100ns"])
                    prev = t["previous_cpu"]
                    if prev is None:
                        row.update(status="baseline-pending", delta_100ns=None)
                    else:
                        dk, du = raw[2] - prev["kernel_100ns"], raw[3] - prev["user_100ns"]
                        if dk < 0 or du < 0:
                            raise RuntimeError("CPU counters went backwards")
                        row.update(status="delta-ready", delta_100ns=dk + du,
                                   delta_kernel_100ns=dk, delta_user_100ns=du,
                                   interval_from=prev["at"], interval_to=row["read_ended"])
                    t["previous_cpu"] = {"at": row["read_ended"], "kernel_100ns": raw[2], "user_100ns": raw[3]}
                    t["previous_delta_100ns"] = row["delta_100ns"]
                    if status == 0:
                        t["retired"] = True
                        row.update(status="exited-final-counters", exit_filetime=raw[1], eligible=False)
                        t["retirement"] = {"at": row["read_ended"], "reason": "original thread exited",
                            "exit_filetime": raw[1], "final_kernel_100ns": raw[2], "final_user_100ns": raw[3],
                            "unobserved_interval_before_first_counter": prev is None}
                    else:
                        row["eligible"] = row["delta_100ns"] is not None
                except Exception as error:
                    row.update(error=repr(error), read_ended=stamp(), status="counter-read-error", eligible=False)
                    raise
            self.verify()
            p = N.times(self.handle, N.GetProcessTimes)
            batch["process_cpu_after"] = {"at": stamp(), "kernel_100ns": p[2], "user_100ns": p[3]}
            batch["delta_ready_count"] = sum(row.get("eligible", False) for row in batch["threads"])
            batch["live_counter_sum_100ns"] = sum(row["delta_100ns"] for row in batch["threads"]
                                                     if row.get("eligible", False))
            batch["counter_sum_is_complete_process_cpu"] = False
            return batch
        finally:
            batch["ended"] = stamp()
            batch["wall_ms"] = (batch["ended"]["perf_ns"] - batch["started"]["perf_ns"]) / 1e6

    def _select(self, cpu, maximum):
        ready = [row for row in cpu["threads"] if row.get("eligible")]
        positive = [row for row in ready if row["delta_100ns"] > 0]
        ranked = sorted(ready, key=lambda row: (-row["delta_100ns"], row["tid"]))
        cpu["ranking"] = [{"tid": row["tid"], "delta_100ns": row["delta_100ns"]} for row in ranked]
        selected = []
        if positive:
            top = min(positive, key=lambda row: (-row["delta_100ns"], row["tid"]))
            selected.append((top, "highest-current-window-cpu; ties use lowest TID"))
        recent = {row["tid"]: row for row in ready
                  if row["delta_100ns"] > 0 or (row.get("previous_delta_100ns") or 0) > 0}
        for row, _ in selected:
            recent.pop(row["tid"], None)
        cpu["recent_two_window_pool_tids"] = sorted(recent)
        if len(selected) < maximum and recent:
            # A stable TID-sorted circular order, independent of fluctuating CPU ranking.
            for offset in range(len(self.threads)):
                index = (self.activity_cursor + offset) % len(self.threads)
                tid = self.threads[index]["tid"]
                if tid in recent:
                    selected.append((recent[tid], "fair-round-robin-other-positive-in-current-or-previous-window"))
                    self.activity_cursor = (index + 1) % len(self.threads)
                    break
        cpu["selected"] = [{"tid": row["tid"], "reason": reason} for row, reason in selected]
        for row, reason in selected:
            row.update(selected=True, selection_reason=reason)
        if not selected:
            cpu["selection_status"] = "pending-no-comparable-delta" if not ready else "no-cpu-active-thread-in-two-windows"
        else:
            cpu["selection_status"] = "selected"
        return selected

    def _location(self, rip):
        found = [m for m in self.initial_modules if m["base"] <= rip < m["base"] + m["size"]]
        if len(found) != 1:
            return {"address": hex(rip), "module": None, "rva": None, "kind": "unknown-dynamic-or-unmapped"}
        m = found[0]
        return {"address": hex(rip), "module": m["path"], "rva": hex(rip - m["base"]), "kind": "initial-loaded-image"}

    def _capture(self, t, row, selection_reason, cpu_batch_index):
        self.verify(t)
        storage, context = N.aligned_context()
        N.U32.from_address(context + 48).value = 0x100001  # AMD64 CONTEXT_CONTROL only.
        s = {"index": len(self.samples), "tid": t["tid"], "thread_creation_filetime": t["creation_filetime"],
             "started": stamp(), "ip_only": True, "stack_bytes": 0, "unwind_calls": 0,
             "suspend_calls": 0, "resume_calls": 0, "ip_obtained": False,
             "cpu_batch_index": cpu_batch_index, "selection_reason": selection_reason,
             "selection_delta_100ns": row["delta_100ns"],
             "selection_previous_delta_100ns": row.get("previous_delta_100ns"),
             "cpu_before": {"kernel_100ns": row["kernel_100ns"], "user_100ns": row["user_100ns"]},
             "cpu_before_at": row["read_ended"], "module_mapping_qualified": None,
             "mapping_reason": "initial list matched at last check, not verified at every IP sample"}
        self.samples.append(s)
        prior = resumed = None
        suspended = False
        capture_error = None
        rip = None
        start = time.perf_counter_ns()
        try:
            s["suspend_calls"] += 1
            prior = N.SuspendThread(t["handle"])
            if prior == N.INVALID:
                raise OSError(C.get_last_error(), "SuspendThread failed")
            suspended = True
            if prior != 0:
                raise RuntimeError("thread already suspended; undo only our increment")
            N.checked(N.GetThreadContext(t["handle"], context), "GetThreadContext")
            rip = N.U64.from_address(context + 248).value
        except BaseException as error:
            capture_error = error
        finally:
            if suspended:
                s["resume_calls"] += 1
                resumed = N.ResumeThread(t["handle"])
                if resumed == N.INVALID:
                    s["resume_winerror"] = C.get_last_error()
            end = time.perf_counter_ns()
            s.update(suspend_previous=prior, resume_previous=resumed, suspension_ms=(end - start) / 1e6)
        if rip is not None:
            s.update(rip=hex(rip), ip_obtained=True, module_location=self._location(rip))
            self.ip_count += 1
        if suspended and resumed != prior + 1:
            if self._exit_code() is not None:
                s["resume_balance_unverifiable_target_exited"] = True
                raise _OwnedProcessExited("process exited before balanced resume could be confirmed")
            self._raise("resume", RuntimeError("unbalanced or unconfirmed resume"), s)
        if capture_error is not None:
            s["capture_error"] = repr(capture_error)
            if self._exit_code() is not None:
                raise _OwnedProcessExited("owned process exited during IP capture")
            self._raise("capture", capture_error, s)
        self.verify(t)
        raw = N.times(t["handle"], N.GetThreadTimes)
        s["cpu_after"] = {"kernel_100ns": raw[2], "user_100ns": raw[3]}
        s["cpu_after_at"] = stamp()
        s["ended"] = stamp()
        s["wall_ms"] = (s["ended"]["perf_ns"] - s["started"]["perf_ns"]) / 1e6
        return s

    def sample(self, max_threads=2):
        if max_threads not in (1, 2):
            raise ValueError("max_threads must be 1 or 2")
        batch = {"started": stamp(), "samples": [], "skipped": [], "ip_only": True}
        try:
            if self.stopped:
                batch.update(stop_sampling=True, process_exited=True)
                return batch
            if not self.prepared:
                raise RuntimeError("prepare must run before sampling")
            self.verify()
            if self.ip_count >= self.sample_limit:
                batch["limit_reached"] = True
                return batch
            if self.ip_count - self.last_inventory_ip_count >= 16:
                self._inventory_check("bounded-16-IP-recheck")
            cpu = self._cpu_scan()
            batch["cpu"] = cpu
            selected = self._select(cpu, min(max_threads, self.sample_limit - self.ip_count))
            lookup = {t["tid"]: t for t in self.threads}
            for row, reason in selected:
                t = lookup[row["tid"]]
                if N.WaitForSingleObject(t["handle"], 0) == 0:
                    # Next full scan records final CPU counters; do not attach to another TID.
                    batch["skipped"].append({"tid": t["tid"], "reason": "exited-after-CPU-read-before-capture", "at": stamp()})
                    continue
                batch["samples"].append(self._capture(t, row, reason, cpu["index"]))
            batch["selection_status"] = cpu["selection_status"]
            return batch
        except _OwnedProcessExited as error:
            batch["lifecycle_event"] = self._record_exit("sample", repr(error))
            batch.update(stop_sampling=True, process_exited=True)
            return batch
        except SamplerFatalError:
            raise
        except Exception as error:
            if self._exit_code() is not None:
                batch["lifecycle_event"] = self._record_exit("sample-race", repr(error))
                batch.update(stop_sampling=True, process_exited=True)
                return batch
            self._raise("sample", error, batch)
        finally:
            batch["ended"] = stamp()
            batch["wall_ms"] = (batch["ended"]["perf_ns"] - batch["started"]["perf_ns"]) / 1e6

    def summary(self):
        return {"version": "owned-air-ip-only-v1", "identity": self.identity, "prepare": self.prepare_record,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "ownership_base_sha256": BASE_SHA256, "native_core_sha256": V.CORE_SHA256,
            "initial_modules": self.initial_modules, "inventory_checks": self.inventory_checks,
            "last_successful_inventory_check": next((e for e in reversed(self.inventory_checks) if e.get("same_as_initial")), None),
            "thread_identities": [{k: v for k, v in t.items() if k not in ("handle", "previous_cpu", "previous_delta_100ns")} for t in self.threads],
            "cpu_batches": self.cpu_batches, "samples": self.samples, "ip_sample_count": self.ip_count,
            "errors": self.errors, "fatal": self.fatal, "closed": self.closed,
            "stopped": self.stopped, "lifecycle_events": self.lifecycle_events, "sample_limit": self.sample_limit,
            "performance_acceptance": False, "symbols_used": False, "ip_only": True,
            "module_memory_bytes_read": 0, "stack_bytes_read": 0, "unwind_calls": 0,
            "new_threads_after_prepare_observed": False, "thread_current_desktop_queried": False,
            "thread_current_desktop_verified": False, "private_desktop_launch_verified": True,
            "limits": ["Selection is intentionally biased toward recent CPU activity; IP frequency is not a CPU percentage or wait duration.",
                "Every callback records all initially held thread identities, including unselected counters and retired/missing intervals; new threads are not discovered.",
                "Thread counters have per-read timestamps; their staggered intervals do not form an exact whole-process CPU total.",
                "A thread may wait by the time its IP is captured despite high CPU in the preceding interval.",
                "Only RIP is captured. No stack or function role is inferred; unknown/JIT remains unknown.",
                "Module inventory checked after prepare and every 16 IP samples; final unchecked tail and between-check mappings remain unknown."]}


if __name__ == "__main__":
    raise SystemExit("Source-only observer; no PID/attach/launch CLI. Caller supplies its new HiddenProcess.")
