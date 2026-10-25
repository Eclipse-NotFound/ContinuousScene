"""Windows x64, new Python child only. No external PID/attach entry point.

Capture IP and <=64 KiB stack with exactly one balanced suspension. Decode
after resume with StackWalk64 custom callbacks: frozen stack and bounded
copies of loaded modules' read-only PE sections. No symbol engine or PDB.
"""
import bisect
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
U64, U32, U16, PTR = C.c_uint64, C.c_uint32, C.c_uint16, C.c_void_p
MAX_STACK = 65536
MAX_MODULE_CACHE = 128 * 1024 * 1024
INVALID = 0xffffffff
K = C.WinDLL("kernel32", use_last_error=True)


def api(name, ret, *args):
    f = getattr(K, name)
    f.restype, f.argtypes = ret, list(args)
    return f


CloseHandle = api("CloseHandle", W.BOOL, PTR)
GetProcessId = api("GetProcessId", U32, PTR)
GetThreadId = api("GetThreadId", U32, PTR)
GetProcessIdOfThread = api("GetProcessIdOfThread", U32, PTR)
GetProcessTimes = api("GetProcessTimes", W.BOOL, PTR, PTR, PTR, PTR, PTR)
GetThreadTimes = api("GetThreadTimes", W.BOOL, PTR, PTR, PTR, PTR, PTR)
OpenThread = api("OpenThread", PTR, U32, W.BOOL, U32)
SuspendThread = api("SuspendThread", U32, PTR)
ResumeThread = api("ResumeThread", U32, PTR)
GetThreadContext = api("GetThreadContext", W.BOOL, PTR, PTR)
ReadProcessMemory = api("ReadProcessMemory", W.BOOL, PTR, PTR, PTR, C.c_size_t, PTR)
VirtualQueryEx = api("VirtualQueryEx", C.c_size_t, PTR, PTR, PTR, C.c_size_t)
WaitForSingleObject = api("WaitForSingleObject", U32, PTR, U32)
IsWow64Process2 = api("IsWow64Process2", W.BOOL, PTR, PTR, PTR)
QueryFullProcessImageNameW = api("QueryFullProcessImageNameW", W.BOOL, PTR, U32, W.LPWSTR, PTR)
CreateJobObjectW = api("CreateJobObjectW", PTR, PTR, W.LPCWSTR)
SetInformationJobObject = api("SetInformationJobObject", W.BOOL, PTR, U32, PTR, U32)
AssignProcessToJobObject = api("AssignProcessToJobObject", W.BOOL, PTR, PTR)
EnumProcessModulesEx = api("K32EnumProcessModulesEx", W.BOOL, PTR, PTR, U32, PTR, U32)
GetModuleFileNameExW = api("K32GetModuleFileNameExW", U32, PTR, PTR, W.LPWSTR, U32)
GetModuleInformation = api("K32GetModuleInformation", W.BOOL, PTR, PTR, PTR, U32)


class MBI(C.Structure):
    _fields_ = [("BaseAddress", PTR), ("AllocationBase", PTR),
                ("AllocationProtect", U32), ("PartitionId", U16),
                ("RegionSize", C.c_size_t), ("State", U32),
                ("Protect", U32), ("Type", U32)]


class MODULEINFO(C.Structure):
    _fields_ = [("base", PTR), ("size", U32), ("entry", PTR)]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(C.Structure):
    _fields_ = [("PerProcessUserTimeLimit", C.c_int64), ("PerJobUserTimeLimit", C.c_int64),
                ("LimitFlags", U32), ("MinimumWorkingSetSize", C.c_size_t),
                ("MaximumWorkingSetSize", C.c_size_t), ("ActiveProcessLimit", U32),
                ("Affinity", C.c_size_t), ("PriorityClass", U32), ("SchedulingClass", U32)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(C.Structure):
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", U64 * 6), ("ProcessMemoryLimit", C.c_size_t),
                ("JobMemoryLimit", C.c_size_t), ("PeakProcessMemoryUsed", C.c_size_t),
                ("PeakJobMemoryUsed", C.c_size_t)]


class ADDRESS64(C.Structure):
    _fields_ = [("Offset", U64), ("Segment", U16), ("Mode", U32)]


class KDHELP64(C.Structure):
    _fields_ = [("Thread", U64), ("ThCallbackStack", U32), ("ThCallbackBStore", U32),
                ("NextCallback", U32), ("FramePointer", U32),
                ("KiCallUserMode", U64), ("KeUserCallbackDispatcher", U64),
                ("SystemRangeStart", U64), ("KiUserExceptionDispatcher", U64),
                ("StackBase", U64), ("StackLimit", U64), ("BuildVersion", U32),
                ("RetpolineStubFunctionTableSize", U32), ("RetpolineStubFunctionTable", U64),
                ("RetpolineStubOffset", U32), ("RetpolineStubSize", U32), ("Reserved0", U64 * 2)]


class STACKFRAME64(C.Structure):
    _fields_ = [("AddrPC", ADDRESS64), ("AddrReturn", ADDRESS64),
                ("AddrFrame", ADDRESS64), ("AddrStack", ADDRESS64), ("AddrBStore", ADDRESS64),
                ("FuncTableEntry", PTR), ("Params", U64 * 4), ("Far", W.BOOL),
                ("Virtual", W.BOOL), ("Reserved", U64 * 3), ("KdHelp", KDHELP64)]


def checked(ok, operation):
    if not ok:
        raise OSError(C.get_last_error(), operation)


def times(handle, fn):
    values = [U64() for _ in range(4)]
    checked(fn(handle, *(C.byref(v) for v in values)), fn.__name__)
    return tuple(v.value for v in values)


def memory(handle, address, size):
    if not 0 < size <= MAX_MODULE_CACHE:
        raise ValueError("bounded memory request required")
    out, count = C.create_string_buffer(size), C.c_size_t()
    checked(ReadProcessMemory(handle, address, out, size, C.byref(count)), "ReadProcessMemory")
    if count.value != size:
        raise RuntimeError("partial remote memory")
    return out.raw


def aligned_context(data=None):
    # Official AMD64 CONTEXT layout, 1232 bytes, alignment 16; CONTROL|INTEGER.
    storage = C.create_string_buffer(1232 + 15)
    address = (C.addressof(storage) + 15) & ~15
    if data is not None:
        C.memmove(address, data, 1232)
    else:
        C.c_uint32.from_address(address + 48).value = 0x100003
    return storage, address


def modules(handle):
    handles, needed = (PTR * 1024)(), U32()
    checked(EnumProcessModulesEx(handle, handles, C.sizeof(handles), C.byref(needed), 3), "modules")
    if needed.value > C.sizeof(handles):
        raise RuntimeError("module inventory exceeded fixed bound")
    result = []
    for h in handles[:needed.value // C.sizeof(PTR)]:
        info, name = MODULEINFO(), C.create_unicode_buffer(32768)
        checked(GetModuleInformation(handle, h, C.byref(info), C.sizeof(info)), "module info")
        checked(GetModuleFileNameExW(handle, h, name, len(name)), "module name")
        result.append({"base": info.base, "size": info.size, "path": name.value})
    return sorted(result, key=lambda m: m["base"])


class LocalImages:
    """Only PE metadata and nonwritable mapped image sections, never a full dump."""
    def __init__(self, owner):
        owner.verify()
        self.inventory = modules(owner.handle)
        self.regions, self.tables, self.failures = [], {}, []
        self.bytes = 0
        for m in self.inventory:
            try:
                self.load(owner.handle, m)
            except (OSError, ValueError, RuntimeError, struct.error) as error:
                self.failures.append({"module": m["path"], "error": str(error)})
        self.regions.sort(key=lambda r: r[0])

    def load(self, handle, m):
        base, size = m["base"], m["size"]
        header = memory(handle, base, min(4096, size))
        if header[:2] != b"MZ":
            raise ValueError("not PE")
        pe = struct.unpack_from("<I", header, 60)[0]
        if pe > 2048 or header[pe:pe + 4] != b"PE\0\0":
            raise ValueError("PE header out of bound")
        machine, sections = struct.unpack_from("<HH", header, pe + 4)
        optional_size = struct.unpack_from("<H", header, pe + 20)[0]
        op = pe + 24
        if machine != 0x8664 or struct.unpack_from("<H", header, op)[0] != 0x20b:
            raise ValueError("only AMD64 PE32+")
        table = op + optional_size
        if sections > 64 or table + sections * 40 > len(header):
            raise ValueError("section table out of bound")
        self.regions.append((base, header))
        self.bytes += len(header)
        for i in range(sections):
            sh = table + i * 40
            virtual_size, rva = struct.unpack_from("<II", header, sh + 8)
            flags = struct.unpack_from("<I", header, sh + 36)[0]
            # READ && !WRITE: .text/.pdata/.xdata/.rdata, not heaps or writable globals.
            if not (flags & 0x40000000) or flags & 0x80000000 or not virtual_size:
                continue
            if rva + virtual_size > size or self.bytes + virtual_size > MAX_MODULE_CACHE:
                raise ValueError("image cache bound exceeded")
            data = memory(handle, base + rva, virtual_size)
            self.regions.append((base + rva, data))
            self.bytes += len(data)
        count = struct.unpack_from("<I", header, op + 108)[0]
        if count < 4:
            return
        pdata_rva, pdata_size = struct.unpack_from("<II", header, op + 112 + 3 * 8)
        if not pdata_rva or not pdata_size:
            return
        pdata = self.read(base + pdata_rva, pdata_size)
        if pdata is None or pdata_size % 12:
            raise ValueError("runtime function table unavailable")
        entries = list(struct.iter_unpack("<III", pdata))
        if any(a >= b or b > size or u >= size for a, b, u in entries):
            raise ValueError("invalid runtime function table")
        starts = [a for a, _, _ in entries]
        if starts != sorted(starts):
            raise ValueError("unsorted runtime function table")
        self.tables[base] = (starts, entries, C.create_string_buffer(pdata))

    def read(self, address, size):
        for base, data in self.regions:
            offset = address - base
            if 0 <= offset and offset + size <= len(data):
                return data[offset:offset + size]
        return None

    def module(self, address):
        for m in self.inventory:
            if m["base"] <= address < m["base"] + m["size"]:
                return m
        return None

    def location(self, address):
        m = self.module(address)
        return {"address": hex(address), "module": m["path"] if m else None,
                "rva": hex(address - m["base"]) if m else None,
                "kind": "loaded-image" if m else "unmapped-or-dynamic-unknown"}


class OwnedFixture:
    def __init__(self):
        self.process = self.job = self.handle = None
        self.thread_handles = {}
        self.identity = None

    def start(self):
        self.job = CreateJobObjectW(None, None)
        checked(self.job, "create owned job")
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        checked(SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)), "job limits")
        env = os.environ.copy()
        for key in ("_NT_SYMBOL_PATH", "_NT_ALTERNATE_SYMBOL_PATH", "DBGHELP_LOG", "DBGHELP_DBGOUT"):
            env.pop(key, None)
        self.process = subprocess.Popen([sys.executable, "-B", "-I", str(HERE / "worker.py")],
            cwd=HERE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.handle = int(self.process._handle)  # exact handle created by this Popen; never OpenProcess
        checked(AssignProcessToJobObject(self.job, self.handle), "assign owned job")
        pm, nm = U16(), U16()
        checked(IsWow64Process2(self.handle, C.byref(pm), C.byref(nm)), "architecture")
        if pm.value or nm.value != 0x8664:
            raise RuntimeError("fixture must be native AMD64")
        name, n = C.create_unicode_buffer(32768), U32(32768)
        checked(QueryFullProcessImageNameW(self.handle, 0, name, C.byref(n)), "fixture image")
        if Path(name.value).resolve() != Path(sys.executable).resolve():
            raise RuntimeError("fixture executable mismatch")
        self.identity = {"pid": self.process.pid, "creation_filetime": times(self.handle, GetProcessTimes)[0],
                         "image": name.value, "parent_pid": os.getpid(), "native_machine": nm.value}
        ready = json.loads(self.process.stdout.readline())
        if ready["pid"] != self.process.pid:
            raise RuntimeError("child handshake PID mismatch")
        for role in ("busy", "sleep"):
            tid = ready[role + "_tid"]
            h = OpenThread(0x0002 | 0x0008 | 0x0040 | 0x00100000, False, tid)
            checked(h, "open owned fixture thread")
            self.thread_handles[role] = {"handle": h, "tid": tid,
                "creation_filetime": times(h, GetThreadTimes)[0]}
            self.verify(role)
        self.process.stdin.write("go\n")
        self.process.stdin.flush()

    def verify(self, role=None):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("owned child exited")
        if GetProcessId(self.handle) != self.identity["pid"] or times(self.handle, GetProcessTimes)[0] != self.identity["creation_filetime"]:
            raise RuntimeError("owned process identity mismatch")
        if role:
            t = self.thread_handles[role]
            if GetProcessIdOfThread(t["handle"]) != self.identity["pid"] or GetThreadId(t["handle"]) != t["tid"]:
                raise RuntimeError("owned thread PID/TID mismatch")
            if times(t["handle"], GetThreadTimes)[0] != t["creation_filetime"] or WaitForSingleObject(t["handle"], 0) != 258:
                raise RuntimeError("owned thread creation time/exit mismatch")

    def close(self):
        # Both terminate and job cleanup use retained handles of our child only.
        result = {"child_exited": self.process is None}
        errors = []
        try:
            if self.process:
                if self.process.poll() is None:
                    self.process.terminate()
                self.process.wait(timeout=3)
        except Exception as error:
            errors.append(repr(error))
        finally:
            # Never skip closing the kill-on-close job even if terminate/wait failed.
            if self.job:
                if not CloseHandle(self.job):
                    errors.append("CloseHandle(job) failed: " + str(C.get_last_error()))
                self.job = None
            if self.process:
                try:
                    self.process.wait(timeout=3)
                    result = {"child_exited": True, "exit_code": self.process.returncode}
                except Exception as error:
                    errors.append(repr(error))
                    result = {"child_exited": False}
                for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                    if stream:
                        try:
                            stream.close()
                        except Exception as error:
                            errors.append(repr(error))
            for t in self.thread_handles.values():
                CloseHandle(t["handle"])
            self.thread_handles.clear()
        if errors:
            result["errors"] = errors
        return result


def capture(owner, role, force_exception=False):
    owner.verify(role)
    t = owner.thread_handles[role]
    h = t["handle"]
    # Allocate before suspension. No file, DbgHelp, synchronization or symbol calls below.
    ctx_storage, ctx = aligned_context()
    stack = C.create_string_buffer(MAX_STACK)
    count, mbi = C.c_size_t(), MBI()
    result = {"role": role, "tid": t["tid"], "thread_creation_filetime": t["creation_filetime"],
              "cpu_before_100ns": sum(times(h, GetThreadTimes)[2:]), "max_stack_bytes": MAX_STACK,
              "forced_exception": force_exception}
    suspended = False
    prior = resumed = None
    start = time.perf_counter_ns()
    try:
        prior = SuspendThread(h)
        if prior == INVALID:
            raise OSError(C.get_last_error(), "SuspendThread failed")
        suspended = True
        if prior != 0:
            raise RuntimeError("preexisting suspension; decline capture and undo only ours")
        checked(GetThreadContext(h, ctx), "GetThreadContext")
        if force_exception:
            raise RuntimeError("intentional failure after GetThreadContext")
        rsp = U64.from_address(ctx + 152).value
        result["rip"] = U64.from_address(ctx + 248).value
        result["rsp"] = rsp
        if VirtualQueryEx(owner.handle, rsp, C.byref(mbi), C.sizeof(mbi)) != C.sizeof(mbi):
            raise RuntimeError("stack query failed")
        if mbi.State != 0x1000 or mbi.Protect & 0x101:
            raise RuntimeError("stack unavailable/guarded")
        size = min(MAX_STACK, int(mbi.BaseAddress) + mbi.RegionSize - rsp)
        if size <= 0:
            raise RuntimeError("stack span invalid")
        checked(ReadProcessMemory(owner.handle, rsp, stack, size, C.byref(count)), "stack snapshot")
        if count.value != size:
            raise RuntimeError("partial stack snapshot")
    except Exception as error:
        result["capture_error"] = str(error)
    finally:
        if suspended:
            # Exactly one ResumeThread for our one successful SuspendThread, including errors.
            resumed = ResumeThread(h)
        finish = time.perf_counter_ns()
    result.update(suspend_previous=prior, resume_previous=resumed,
                  suspension_ms=(finish - start) / 1e6, stack_bytes=count.value)
    if suspended and resumed != prior + 1:
        raise RuntimeError("resume count mismatch; abort and clean owned fixture")
    owner.verify(role)
    result["cpu_after_100ns"] = sum(times(h, GetThreadTimes)[2:])
    if "capture_error" not in result:
        result["context"] = C.string_at(ctx, 1232)
        result["stack"] = stack.raw[:count.value]
    return result


def unwind(snapshot, images):
    """No live remote reads, no Sym* API, no PDB; all callbacks use copies."""
    if "capture_error" in snapshot:
        return {"frames": [], "status": "capture-error"}
    system = C.create_unicode_buffer(32768)
    get_system = api("GetSystemDirectoryW", U32, W.LPWSTR, U32)
    checked(get_system(system, len(system)), "system directory")
    dbg_path = str(Path(system.value) / "dbghelp.dll")
    dbg = C.WinDLL(dbg_path, use_last_error=True)
    readtype = C.WINFUNCTYPE(W.BOOL, PTR, U64, PTR, U32, C.POINTER(U32))
    tabletype = C.WINFUNCTYPE(PTR, PTR, U64)
    basetype = C.WINFUNCTYPE(U64, PTR, U64)
    misses = []

    @readtype
    def read(_token, address, output, size, received):
        received[0] = 0
        if not 0 < size <= MAX_STACK:
            return False
        offset = address - snapshot["rsp"]
        if 0 <= offset and offset + size <= len(snapshot["stack"]):
            data = snapshot["stack"][offset:offset + size]
        else:
            data = images.read(address, size)
        if data is None:
            if len(misses) < 16:
                misses.append({"address": hex(address), "bytes": size})
            return False
        C.memmove(output, data, size)
        received[0] = size
        return True

    @tabletype
    def table(_token, address):
        m = images.module(address)
        if not m or m["base"] not in images.tables:
            return None
        starts, entries, buf = images.tables[m["base"]]
        rva = address - m["base"]
        i = bisect.bisect_right(starts, rva) - 1
        if i >= 0 and entries[i][0] <= rva < entries[i][1]:
            return C.addressof(buf) + i * 12
        return None

    @basetype
    def base(_token, address):
        m = images.module(address)
        return m["base"] if m else 0

    walk = dbg.StackWalk64
    walk.restype = W.BOOL
    walk.argtypes = [U32, PTR, PTR, PTR, PTR, readtype, tabletype, basetype, PTR]
    storage, context = aligned_context(snapshot["context"])
    frame = STACKFRAME64()
    for a in (frame.AddrPC, frame.AddrFrame, frame.AddrStack):
        a.Mode = 3  # AddrModeFlat
    frame.AddrPC.Offset = snapshot["rip"]
    frame.AddrStack.Offset = snapshot["rsp"]
    frame.AddrFrame.Offset = struct.unpack_from("<Q", snapshot["context"], 160)[0]
    frames, seen, status = [images.location(snapshot["rip"])], set(), "max-depth"
    for _ in range(24):
        if not images.module(frame.AddrPC.Offset):
            status = "dynamic-or-unknown-address-stop"
            break
        # Tokens deliberately are not OS handles: only our three local callbacks can serve data.
        if not walk(0x8664, 0x12345, 0x23456, C.byref(frame), context, read, table, base, None):
            status = "StackWalk64-stopped"
            break
        key = (frame.AddrPC.Offset, frame.AddrStack.Offset)
        if not key[0] or key in seen:
            status = "zero-or-repeated-frame-stop"
            break
        seen.add(key)
        if frame.AddrPC.Offset != snapshot["rip"] or len(frames) > 1:
            frames.append(images.location(frame.AddrPC.Offset))
    return {"frames": frames, "status": status, "read_misses": misses,
            "dbghelp": dbg_path, "symbol_engine_initialized": False, "live_reads_during_walk": 0}


def smoke():
    if os.name != "nt" or C.sizeof(PTR) != 8 or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("Windows AMD64 Python required")
    assert C.sizeof(MBI) == 48 and C.sizeof(ADDRESS64) == 16
    assert STACKFRAME64.KdHelp.offset == 152 and C.sizeof(STACKFRAME64) == 264
    output = HERE / ("smoke-" + uuid.uuid4().hex + ".json")
    report = {"schema": 1, "scope": "new-owned-python-fixture-only", "samples": [],
              "performance_acceptance": False, "game_tested": False, "pdb_or_symbol_service_used": False}
    owner = OwnedFixture()
    try:
        owner.start()
        report["owner"] = owner.identity
        images = LocalImages(owner)
        report["image_cache"] = {"bytes": images.bytes, "modules": images.inventory, "failures": images.failures,
                                 "runtime_tables": len(images.tables), "full_process_dump": False}
        before_time = time.perf_counter_ns()
        before = {r: sum(times(t["handle"], GetThreadTimes)[2:]) for r, t in owner.thread_handles.items()}
        time.sleep(0.25)
        for i in range(12):
            role = "busy" if i % 2 == 0 else "sleep"
            sample = capture(owner, role)
            sample["walk"] = unwind(sample, images)
            sample.pop("context", None)
            sample.pop("stack", None)  # never persist raw memory
            report["samples"].append(sample)
            time.sleep(0.035)
        report["failure_path"] = capture(owner, "busy", force_exception=True)
        time.sleep(0.1)
        after_time = time.perf_counter_ns()
        after = {r: sum(times(t["handle"], GetThreadTimes)[2:]) for r, t in owner.thread_handles.items()}
        report["thread_cpu"] = {"window_ms": (after_time - before_time) / 1e6,
            "deltas_100ns": {r: after[r] - before[r] for r in before},
            "note": "CPU deltas are independent counters; stack frequencies are wall-time snapshots, not CPU shares."}
        report["module_inventory_unchanged"] = images.inventory == modules(owner.handle)
        report["post_failure_busy_progress_100ns"] = after["busy"] - report["failure_path"]["cpu_after_100ns"]
        report["balanced_suspensions"] = all(s["suspend_previous"] == 0 and s["resume_previous"] == 1
            for s in report["samples"] + [report["failure_path"]])
        report["ip_capture_passed"] = all("capture_error" not in s and s["rip"] for s in report["samples"])
        report["multi_frame_walks"] = sum(len(s["walk"]["frames"]) > 1 for s in report["samples"])
        report["passed"] = (report["balanced_suspensions"] and report["ip_capture_passed"]
            and report["post_failure_busy_progress_100ns"] > 0 and report["module_inventory_unchanged"])
    except Exception as error:
        report["error"] = repr(error)
        report["passed"] = False
    finally:
        report["cleanup"] = owner.close()
        report["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (Path(__file__), HERE / "worker.py")}
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "passed": report.get("passed"),
                      "error": report.get("error"), "cleanup": report["cleanup"]}))
    return 0 if report.get("passed") and report["cleanup"]["child_exited"] else 1


if __name__ == "__main__":
    if sys.argv[1:] != ["--smoke-owned-child"]:
        raise SystemExit("Only --smoke-owned-child is supported; no PID/attach/launch-game interface.")
    raise SystemExit(smoke())
