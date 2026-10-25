"""Owned, private-desktop WM_MOUSEMOVE capability only. No arbitrary PID attach.

Source preparation does not authorize executing this runner. After review/build,
it launches one independent fixture and posts at most three native messages.
"""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
TOOLS = ROOT / "mods/ModLoader/tools"
EXPECTED_TOOLS = {
    "air_test_process.py": "628FFED886DB293ABE0177FD42C61AC09482E04AEE6AAE358CF2E3D6DEB0D1F9",
    "test_registry.py": "8B35A6D6CA1DD94CFD5CBA9A42979EBD14D9AE65497688FA859D084425922049",
}
SOURCE = HERE / "src/OwnedMouseCapability.as"
SWF = HERE / "build/OwnedMouseCapability.swf"
RECEIPT = HERE / "build/compile-receipt.json"
EXE = ROOT / "adl64.exe"
RUNTIME = ROOT / "runtimes/air/win64"
WM_MOUSEMOVE = 0x0200


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def save(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def read(path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def stamp():
    return {"epochMs": time.time_ns() / 1_000_000, "perfNs": time.perf_counter_ns()}


class MEMORYSTATUSEX(C.Structure):
    _fields_ = [("dwLength", W.DWORD), ("dwMemoryLoad", W.DWORD)] + [
        (name, C.c_ulonglong) for name in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile",
        "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]


class OwnedWindow:
    """The caller creates the process immediately before binding this object."""
    def __init__(self, process, descriptor, descriptor_sha, hidden_class):
        if type(process) is not hidden_class:
            raise RuntimeError("Exact freshly created HiddenProcess required")
        self.process, self.handle, self.desktop = process, process._process, process._desktop_handle
        if not self.handle or not self.desktop or process.poll() is not None:
            raise RuntimeError("Original live process and private desktop handles required")
        self.k = C.WinDLL("kernel32", use_last_error=True)
        self.u = C.WinDLL("user32", use_last_error=True)
        self.callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        for fn, args, result in [
            (self.k.GetProcessId, [W.HANDLE], W.DWORD),
            (self.k.GetProcessTimes, [W.HANDLE] + [C.POINTER(W.FILETIME)] * 4, W.BOOL),
            (self.k.QueryFullProcessImageNameW, [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL),
            (self.k.GlobalMemoryStatusEx, [C.POINTER(MEMORYSTATUSEX)], W.BOOL),
            (self.u.GetUserObjectInformationW, [W.HANDLE, C.c_int, W.LPVOID, W.DWORD, C.POINTER(W.DWORD)], W.BOOL),
            (self.u.EnumDesktopWindows, [W.HANDLE, self.callback, W.LPARAM], W.BOOL),
            (self.u.GetWindowThreadProcessId, [W.HWND, C.POINTER(W.DWORD)], W.DWORD),
            (self.u.GetClientRect, [W.HWND, C.POINTER(W.RECT)], W.BOOL),
            (self.u.GetClassNameW, [W.HWND, W.LPWSTR, C.c_int], C.c_int),
            (self.u.GetWindowTextW, [W.HWND, W.LPWSTR, C.c_int], C.c_int),
            (self.u.IsWindow, [W.HWND], W.BOOL),
            (self.u.PostMessageW, [W.HWND, W.UINT, W.WPARAM, W.LPARAM], W.BOOL),
        ]:
            fn.argtypes, fn.restype = args, result
        self.descriptor, self.descriptor_sha = descriptor, descriptor_sha
        self.command = [str(EXE), "-runtime", str(RUNTIME), str(descriptor)]
        if process.command != self.command:
            raise RuntimeError("Owned descriptor command differs from the newly created fixture")
        self.identity = self.identity_now()
        self.hwnd_row = None

    @staticmethod
    def checked(ok, operation):
        if not ok:
            raise OSError(C.get_last_error(), operation)

    def identity_now(self):
        if self.process._process != self.handle or self.process._desktop_handle != self.desktop:
            raise RuntimeError("Original owned handles changed")
        if self.process.poll() is not None:
            raise RuntimeError("Owned fixture exited")
        if self.process.command != self.command or sha(self.descriptor) != self.descriptor_sha:
            raise RuntimeError("Owned launch descriptor changed")
        pid = self.k.GetProcessId(self.handle)
        if pid != self.process.pid:
            raise RuntimeError("Original process handle PID mismatch")
        times = [W.FILETIME() for _ in range(4)]
        self.checked(self.k.GetProcessTimes(self.handle, *[C.byref(t) for t in times]), "GetProcessTimes")
        creation = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        image, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        self.checked(self.k.QueryFullProcessImageNameW(self.handle, 0, image, C.byref(size)), "Owned image")
        if Path(image.value).resolve(strict=True) != EXE.resolve(strict=True):
            raise RuntimeError("Owned image is not expected adl64.exe")
        desktop, needed = C.create_unicode_buffer(512), W.DWORD()
        self.checked(self.u.GetUserObjectInformationW(self.desktop, 2, desktop, C.sizeof(desktop), C.byref(needed)),
                     "Private desktop name")
        if desktop.value != self.process.desktop or not desktop.value.startswith("RemainsTest-"):
            raise RuntimeError("Private desktop handle/name mismatch")
        return {"pid": pid, "creationFiletime100ns": str(creation), "image": image.value,
                "desktop": desktop.value, "processHandle": str(self.handle),
                "desktopHandle": str(self.desktop), "descriptor": str(self.descriptor),
                "descriptorSHA256": self.descriptor_sha, "command": self.command}

    def verify(self):
        if self.identity_now() != self.identity:
            raise RuntimeError("Owned fixture identity changed")

    def windows(self):
        self.verify()
        rows, errors = [], []

        @self.callback
        def collect(hwnd, unused):
            try:
                pid = W.DWORD()
                tid = self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
                if pid.value != self.process.pid:
                    return True  # No class/title or input to other PIDs.
                if not tid or len(rows) >= 32:
                    raise RuntimeError("Invalid or excessive owned window inventory")
                rect = W.RECT()
                self.checked(self.u.GetClientRect(hwnd, C.byref(rect)), "Owned GetClientRect")
                name, title = C.create_unicode_buffer(256), C.create_unicode_buffer(1024)
                self.checked(self.u.GetClassNameW(hwnd, name, len(name)), "Owned GetClassNameW")
                self.u.GetWindowTextW(hwnd, title, len(title))
                rows.append({"hwnd": int(hwnd), "pid": pid.value, "tid": tid,
                             "className": name.value, "title": title.value,
                             "client": [rect.left, rect.top, rect.right, rect.bottom]})
                return True
            except Exception as error:
                errors.append(repr(error))
                C.set_last_error(1)
                return False

        C.set_last_error(0)
        ok = self.u.EnumDesktopWindows(self.desktop, collect, 0)
        if errors:
            raise RuntimeError("Owned window enumeration: " + "; ".join(errors))
        self.checked(ok, "EnumDesktopWindows(private owned desktop)")
        self.verify()
        return rows

    def select(self, app_id):
        rows = self.windows()
        candidates = [row for row in rows if row["client"] == [0, 0, 640, 480]]
        if len(candidates) != 1 or candidates[0]["title"] != app_id:
            raise RuntimeError("Unique ready 640x480 owned top-level content window missing: " + json.dumps(rows))
        self.hwnd_row = candidates[0]
        return rows

    def post_once(self, x, y):
        rows = self.windows()
        candidates = [row for row in rows if row["client"] == [0, 0, 640, 480]]
        if candidates != [self.hwnd_row] or not self.u.IsWindow(self.hwnd_row["hwnd"]):
            raise RuntimeError("Owned content window identity changed")
        self.verify()
        C.set_last_error(0)
        before = stamp()
        ok = self.u.PostMessageW(self.hwnd_row["hwnd"], WM_MOUSEMOVE, 0, (y << 16) | x)
        after = stamp()
        # Success proves queue acceptance only. The AIR observations decide capability.
        return {"before": before, "after": after, "accepted": bool(ok),
                "winerror": 0 if ok else C.get_last_error(), "hwnd": self.hwnd_row["hwnd"],
                "message": WM_MOUSEMOVE, "wParam": 0, "lParam": (y << 16) | x,
                "clientX": x, "clientY": y, "ownership": self.identity}


def memory(minimum):
    k = C.WinDLL("kernel32", use_last_error=True)
    k.GlobalMemoryStatusEx.argtypes = [C.POINTER(MEMORYSTATUSEX)]
    k.GlobalMemoryStatusEx.restype = W.BOOL
    state = MEMORYSTATUSEX()
    state.dwLength = C.sizeof(state)
    OwnedWindow.checked(k.GlobalMemoryStatusEx(C.byref(state)), "GlobalMemoryStatusEx")
    if state.ullAvailPageFile < minimum:
        raise RuntimeError("Insufficient available commit: " + str(state.ullAvailPageFile))
    return {"availableCommitBytes": state.ullAvailPageFile, "minimumBytes": minimum, **stamp()}


def check_snapshot(value, app_id, nonce):
    if not isinstance(value, dict) or value.get("appId") != app_id or value.get("nonce") != nonce:
        raise RuntimeError("Fixture JSON identity mismatch")
    if value.get("stageWidth") != 640 or value.get("stageHeight") != 480:
        raise RuntimeError("Stage dimensions changed")
    if value.get("scaleMode") != "noScale" or value.get("align") != "TL" or value.get("errors"):
        raise RuntimeError("Unexpected AIR stage/error state")


def near(value, expected):
    return type(value) in (int, float) and abs(value - expected) <= 1.0


def confirmed(snapshot, baseline, target, x, y):
    for event in snapshot.get("events", []):
        if event.get("seq", 0) <= baseline["eventSeq"]:
            continue
        path = event.get("path", [])
        if not (event.get("type") == "mouseMove" and event.get("targetName") == target
                and event.get("buttonDown") is False
                and event.get("targetClass") == "flash.display::Sprite"
                and len(path) == 3 and path[0].get("name") == target
                and path[1].get("name") == "probeRoot" and path[2].get("isStage") is True
                and event.get("pathReachedStage") is True
                and all(near(event.get(key), expected) for key, expected in (
                    ("eventStageX", x), ("eventStageY", y), ("stageMouseX", x), ("stageMouseY", y)))):
            continue
        for timer in snapshot.get("timers", []):
            if (timer.get("seq", 0) > baseline["timerSeq"] and timer.get("eventSeq", 0) >= event["seq"]
                    and timer.get("appMs", -1) >= event["appMs"]
                    and near(timer.get("stageMouseX"), x) and near(timer.get("stageMouseY"), y)):
                return {"event": event, "laterTimer": timer}
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait", type=float, default=300, help="Shared test registry wait seconds")
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("Windows private desktop required")
    if HERE.is_symlink():
        raise RuntimeError("Fixture root may not be a symlink")
    for name, expected in EXPECTED_TOOLS.items():
        if sha(TOOLS / name) != expected:
            raise RuntimeError("Reviewed shared tool changed: " + name)
    receipt = read(RECEIPT)
    expected_build = {"sourceSHA256": sha(SOURCE), "configSHA256": sha(HERE / "compile.xml"), "swfSHA256": sha(SWF)}
    if not receipt or any(receipt.get(key, "").upper() != value for key, value in expected_build.items()):
        raise RuntimeError("Reviewed fixture build receipt missing or mismatched")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(TOOLS))
    from air_test_process import HiddenProcess
    from test_registry import Registration
    nonce = uuid.uuid4().hex
    app_id = "com.remains.ownedmouse." + nonce
    run_dir = HERE / "runs" / nonce
    run_dir.mkdir(parents=True, exist_ok=False)
    storage = Path(os.environ["APPDATA"]) / app_id / "Local Store"
    if storage.exists():
        raise RuntimeError("New unique AIR storage already exists")
    descriptor = run_dir / ("app-owned-mouse-test-" + nonce + ".xml")
    descriptor.write_text('''<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
  <id>''' + app_id + '''</id><versionNumber>1.0.0</versionNumber>
  <filename>OwnedMouseCapability</filename><name>OwnedMouseCapability</name>
  <initialWindow><content>OwnedMouseCapability.swf</content><title>''' + app_id + '''</title>
    <width>640</width><height>480</height><visible>true</visible>
    <systemChrome>standard</systemChrome><transparent>false</transparent>
    <renderMode>direct</renderMode><resizable>false</resizable><maximizable>false</maximizable>
  </initialWindow><supportedProfiles>extendedDesktop</supportedProfiles>
</application>''', encoding="utf-8")
    save(run_dir / "fixture.json", {"appId": app_id, "nonce": nonce})
    shutil.copyfile(SWF, run_dir / "OwnedMouseCapability.swf")
    report_path = run_dir / "runner-result.json"
    if sha(run_dir / "OwnedMouseCapability.swf") != expected_build["swfSHA256"]:
        raise RuntimeError("Fixture copy fingerprint mismatch")
    inputs = [Path(__file__), SOURCE, HERE / "compile.xml", RECEIPT, SWF, EXE,
              run_dir / "OwnedMouseCapability.swf", run_dir / "fixture.json", *[TOOLS / n for n in EXPECTED_TOOLS]]
    inputs += sorted(p for p in RUNTIME.rglob("*") if p.is_file())
    frozen = {str(path): sha(path) for path in inputs}
    out = {"version": "owned-mouse-capability-runner-1", "appId": app_id, "nonce": nonce,
           "runDir": str(run_dir), "storage": str(storage), "inputs": frozen,
           "descriptor": descriptor.read_text(encoding="utf-8"), "descriptorSHA256": sha(descriptor),
           "steps": [], "capabilityPassed": False, "diagnosticOnly": True,
           "performanceEligible": False, "cleanup": {}, "began": stamp()}
    process = None
    record = None
    def persist():
        save(report_path, out)
    try:
        with Registration(owner="ContinuousScene / owned mouse capability", resource="game", wait=args.wait,
                          purpose="Independent three-target private desktop WM_MOUSEMOVE capability only",
                          run_dir=run_dir, evidence=report_path) as record:
            out["registrationId"] = record.id
            try:
                out["startupMemory"] = memory(4 * 1024**3)
                persist()
                record.before_launch(app_id + " / standalone fixture / private desktop")
                with (run_dir / "stdout.log").open("wb") as stdout, (run_dir / "stderr.log").open("wb") as stderr:
                    process = HiddenProcess([str(EXE), "-runtime", str(RUNTIME), str(descriptor)],
                                            cwd=run_dir, stdout=stdout, stderr=stderr)
                    record.child(process.pid)
                    window = OwnedWindow(process, descriptor, out["descriptorSHA256"], HiddenProcess)
                    out["ownership"] = window.identity
                    persist()
                    deadline = time.perf_counter() + 20
                    ready = None
                    while time.perf_counter() < deadline:
                        window.verify()
                        memory(512 * 1024**2)
                        ready = read(storage / "ready.json")
                        if ready:
                            break
                        time.sleep(0.1)
                    if not ready:
                        raise RuntimeError("AIR ready timeout; no input posted")
                    check_snapshot(ready, app_id, nonce)
                    if Path(ready["storageNativePath"]).resolve() != storage.resolve():
                        raise RuntimeError("AIR storage location mismatch")
                    out["ready"] = ready
                    out["ownedWindows"] = window.select(app_id)
                    persist()
                    for i, x in enumerate((90, 290, 490)):
                        baseline = read(storage / "events.json")
                        check_snapshot(baseline, app_id, nonce)
                        step = {"target": "target" + str(i), "baseline": baseline,
                                "memory": memory(512 * 1024**2), "attemptCount": 0}
                        out["steps"].append(step)
                        persist()
                        step["attemptCount"] = 1
                        persist()  # Preserve intended single attempt even if a later API call raises.
                        step["post"] = window.post_once(x, 230)
                        persist()
                        if not step["post"]["accepted"]:
                            raise RuntimeError("WM_MOUSEMOVE queue rejected; no retry or next target")
                        deadline = time.perf_counter() + 3
                        while time.perf_counter() < deadline:
                            window.verify()
                            memory(512 * 1024**2)
                            observed = read(storage / "events.json")
                            check_snapshot(observed, app_id, nonce)
                            step["lastObservation"] = observed
                            proof = confirmed(observed, baseline, step["target"], x, 230)
                            if proof:
                                step["confirmation"] = proof
                                step["confirmedAt"] = stamp()
                                break
                            time.sleep(0.1)
                        persist()
                        if "confirmation" not in step:
                            raise RuntimeError("Native event/target and later actual Stage coordinates unconfirmed; stop")
                    out["threeTargetsConfirmed"] = True
            except BaseException as error:
                out["executionError"] = repr(error)
                out["executionTraceback"] = traceback.format_exc()
                persist()
            finally:
                # Only the exact process created above is ever stopped. A failed
                # ownership check does not authorize looking up/killing another PID.
                if process is not None:
                    try:
                        try:
                            if process.poll() is None and storage.is_dir():
                                save(storage / "command.json", {"appId": app_id, "nonce": nonce,
                                    "action": "finish", "reason": "runner-complete" if out.get("threeTargetsConfirmed") else "runner-stop"})
                                deadline = time.perf_counter() + 2
                                while process.poll() is None and time.perf_counter() < deadline:
                                    time.sleep(0.05)
                        except BaseException as error:
                            out["cleanup"]["gracefulError"] = repr(error)
                        finally:
                            if process.poll() is None:
                                out["cleanup"]["forcedOwnedStop"] = True
                                process.kill()
                            out["cleanup"]["exitCode"] = process.wait(10)
                            try:
                                record.child_stopped()
                            finally:
                                process.close()
                                out["cleanup"]["ownedHandlesClosed"] = True
                    except BaseException as error:
                        out["cleanup"]["error"] = repr(error)
                else:
                    out["cleanup"]["noProcessReturned"] = True
                    # before_launch may be uncertain: do not clear the registry flag.
                for name in ("ready.json", "events.json", "result.json"):
                    try:
                        value = read(storage / name)
                        if value is not None:
                            save(run_dir / ("air-" + name), value)
                            if name == "result.json":
                                out["airResult"] = value
                    except BaseException as error:
                        out.setdefault("artifactErrors", []).append(name + ": " + repr(error))
                try:
                    after = {path: sha(path) for path in frozen}
                    out["inputChanges"] = [path for path in frozen if after[path] != frozen[path]]
                except BaseException as error:
                    out["inputVerificationError"] = repr(error)
                final = out.get("airResult") or {}
                out["capabilityPassed"] = bool(out.get("threeTargetsConfirmed") and not out.get("executionError")
                    and out["cleanup"].get("ownedHandlesClosed") and out["cleanup"].get("exitCode") == 0
                    and not out["cleanup"].get("forcedOwnedStop") and not out.get("artifactErrors")
                    and not out["cleanup"].get("error") and not out["cleanup"].get("gracefulError")
                    and not out.get("inputVerificationError") and out.get("inputChanges") == []
                    and final.get("appId") == app_id and final.get("nonce") == nonce
                    and final.get("reason") == "runner-finish:runner-complete" and final.get("errors") == [])
                record.outcome = "passed" if out["capabilityPassed"] else "failed"
                record.note = "Only native message target/Stage readback capability; no physical cursor or performance claim"
                if process is not None and out["cleanup"].get("ownedHandlesClosed"):
                    try:
                        descriptor.unlink()  # Its exact bytes remain in runner-result.json.
                        out["cleanup"]["descriptorRemoved"] = True
                    except BaseException as error:
                        out["cleanup"]["descriptorRemovalError"] = repr(error)
                        out["capabilityPassed"] = False
                        record.outcome = "failed"
                out["ended"] = stamp()
                persist()
    except BaseException as error:
        out["outerError"] = repr(error)
        out["outerTraceback"] = traceback.format_exc()
        out["capabilityPassed"] = False
        persist()
    print(json.dumps({"report": str(report_path), "capabilityPassed": out["capabilityPassed"]}, ensure_ascii=False))
    return 0 if out["capabilityPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
