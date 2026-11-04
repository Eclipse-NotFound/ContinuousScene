"""Isolated live smoke for CS 0.9.9 aim-look (edge latch + viewport re-ensure).

Copies the game into a private tree (formal assets + the current formal mod
stack, but with the 0.9.9 candidate CS SWF, the sceneCU-free host candidate and
one extra test-only probe mod), launches it on a private Windows desktop through
the ModLoader test infrastructure, and asserts the probe's JSON verdict. The
formal install, player saves and running game are untouched: the copy has its own
AIR id and its own APPDATA storage.

Usage: python run_live_099.py [--rebuild]
"""
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
aimv2 = HERE.parent / "aimv2-20261104"
MOD = HERE.parents[2]                      # mods/ContinuousScene
GAME = MOD.parents[1]                      # game root
TOOLS = GAME / "mods/ModLoader/tools"
sys.path.insert(0, str(TOOLS))
from test_registry import Registration      # noqa: E402
from air_test_process import HiddenProcess  # noqa: E402

LIVE = HERE / "live"
ROOTDIR = LIVE / "root"
LAUNCH_LOG = LIVE / "launch.out"
RESULT_COPY = LIVE / "probe-storage"

CANDIDATE_CS = aimv2 / "product/ContinuousSceneMod.swf"
CANDIDATE_HOST = HERE / "host/candidate.swf"
DRIVER_SWF = aimv2 / "driver/release/ContinuousSceneAimProbeMod.swf"
EXPECT_CS_SHA = "D04CD26AA674238BBB2F43A2CA49C57811301E9B9B614352A099F8190D9E0193"
EXPECT_HOST_SHA = "91F8E10DFB36A2024EAB140FC4BD67719330BF67310BA5CAB5CDAE8DEDF3CB45"

ROOT_FILES = [
    "pfe.swf", "adl64.exe", "steam_appid.txt", "pfe60.cfg", "lang.xml", "rooms.xml",
    "texture.swf", "texture1.swf", "sprite.swf", "sprite1.swf",
    "sound.swf", "sound_unit.swf", "sound_weapon.swf",
    "text_zh.xml", "text_en.xml", "text_ru.xml", "text_tw.xml", "text_jp.xml",
    "text_de.xml", "text_es.xml", "text_pl.xml", "text_ua.xml",
]
ROOT_DIRS = ["runtimes/air/win64", "Music", "Rooms"]
APP_ID = "pfe-cs-aimgrid-" + uuid.uuid4().hex[:10] + "-host"


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def build_tree():
    if ROOTDIR.exists():
        shutil.rmtree(ROOTDIR, ignore_errors=True)
    ROOTDIR.mkdir(parents=True)
    for name in ROOT_FILES:
        src = GAME / name
        if not src.exists():
            print("WARN missing root file " + name)
            continue
        shutil.copy2(src, ROOTDIR / name)
    for name in ROOT_DIRS:
        src, dst = GAME / name, ROOTDIR / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["robocopy", str(src), str(dst), "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
                       check=False, capture_output=True)
    # The candidate host replaces the formal pfe.swf in this private tree only.
    shutil.copy2(CANDIDATE_HOST, ROOTDIR / "pfe.swf")
    (ROOTDIR / "mods").mkdir(parents=True, exist_ok=True)
    manifest = GAME / "mods/loader-manifest.txt"
    lines = [l for l in manifest.read_text(encoding="utf-8-sig").splitlines()
             if l.strip() and not l.strip().startswith("#")]
    for line in lines:
        folder = line.split("|")[0]
        src = GAME / "mods" / folder / "release"
        if not src.is_dir():
            print("WARN missing mod release " + folder)
            continue
        dst = ROOTDIR / "mods" / folder / "release"
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["robocopy", str(src), str(dst), "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
                       check=False, capture_output=True)
    cs_rel = ROOTDIR / "mods/ContinuousScene/release"
    cs_rel.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CANDIDATE_CS, cs_rel / "ContinuousSceneMod.swf")
    maps = MOD / "maps"
    if maps.is_dir():
        subprocess.run(["robocopy", str(maps), str(ROOTDIR / "mods/ContinuousScene/maps"), "/E",
                        "/NFL", "/NDL", "/NJH", "/NJS", "/NP"], check=False, capture_output=True)
    probe_rel = ROOTDIR / "mods/ContinuousSceneAimProbe/release"
    probe_rel.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DRIVER_SWF, probe_rel / "ContinuousSceneAimProbeMod.swf")
    (ROOTDIR / "mods/loader-manifest.txt").write_text(
        "\n".join(lines + ["ContinuousSceneAimProbe|ContinuousSceneAimProbeMod|1|0|0"]) + "\n",
        encoding="utf-8")
    app = (GAME / "application.xml").read_text(encoding="utf-8-sig")
    app = app.replace("<id>pfe</id>", "<id>" + APP_ID + "</id>")
    (ROOTDIR / "application-live.xml").write_text(app, encoding="utf-8")
    cs_hash = sha(cs_rel / "ContinuousSceneMod.swf")
    host_hash = sha(ROOTDIR / "pfe.swf")
    if cs_hash != EXPECT_CS_SHA:
        raise SystemExit("candidate CS SWF mismatch: " + cs_hash)
    if host_hash != EXPECT_HOST_SHA:
        raise SystemExit("candidate host mismatch: " + host_hash)
    print("tree ready: " + str(ROOTDIR) + " app=" + APP_ID + " cs=" + cs_hash + " host=" + host_hash)


def storage_dir():
    return Path(os.environ.get("APPDATA", "")) / APP_ID / "Local Store"


def collect_evidence():
    store = storage_dir()
    RESULT_COPY.mkdir(parents=True, exist_ok=True)
    for name in ("ContinuousSceneAimProbe.json", "ContinuousSceneAimProbe.log",
                 "ContinuousScene.log", "ContinuousSceneMod.log"):
        src = store / name
        if src.exists():
            shutil.copy2(src, RESULT_COPY / name)
    return RESULT_COPY / "ContinuousSceneAimProbe.json"


def main():
    global APP_ID
    rebuild = "--rebuild" in sys.argv
    LIVE.mkdir(parents=True, exist_ok=True)
    descriptor = ROOTDIR / "application-live.xml"
    if rebuild or not descriptor.exists():
        build_tree()
    else:
        for line in descriptor.read_text(encoding="utf-8").splitlines():
            if "<id>" in line:
                APP_ID = line.split("<id>")[1].split("</id>")[0].strip()
        print("reusing tree id " + APP_ID)
        shutil.copy2(DRIVER_SWF, ROOTDIR / "mods/ContinuousSceneAimProbe/release/ContinuousSceneAimProbeMod.swf")
        shutil.copy2(CANDIDATE_HOST, ROOTDIR / "pfe.swf")
        shutil.copy2(CANDIDATE_CS, ROOTDIR / "mods/ContinuousScene/release/ContinuousSceneMod.swf")
        print("driver sha", sha(ROOTDIR / "mods/ContinuousSceneAimProbe/release/ContinuousSceneAimProbeMod.swf")[:16],
              "cs sha", sha(ROOTDIR / "mods/ContinuousScene/release/ContinuousSceneMod.swf")[:16],
              "host sha", sha(ROOTDIR / "pfe.swf")[:16])
    cmd = [str(ROOTDIR / "adl64.exe"), "-runtime", str(ROOTDIR / "runtimes/air/win64"),
           str(ROOTDIR / "application-live.xml")]
    with open(LAUNCH_LOG, "wb") as out, open(LIVE / "launch.err", "wb") as err:
        with Registration(owner="ContinuousScene / aim v2 live",
                          purpose="CS 0.9.9 isolated run: edge latch, viewport re-ensure, release; no-sceneCU host",
                          resource="game-coexist", run_dir=str(ROOTDIR),
                          evidence=str(RESULT_COPY), wait=900) as record:
            record.before_launch("host(no-sceneCU) / " + APP_ID + " / formal stack + probe")
            try:
                proc = HiddenProcess(cmd, cwd=str(ROOTDIR), stdout=out, stderr=err)
            except BaseException as launch_error:
                record.launching = False
                record.note = "launch failed: " + str(launch_error)
                print("LAUNCH FAILED:", launch_error, flush=True)
                return 1
            record.child(proc.pid)
            try:
                code = proc.wait(420)
                print("exit code", code)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = 124
                print("TIMEOUT: stopped owned process")
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(30)
                record.child_stopped()
            result_path = collect_evidence()
            verdict = {"ok": False, "reason": "no result json"}
            if result_path.exists():
                verdict = json.loads(result_path.read_text(encoding="utf-8"))
            print(json.dumps(verdict, ensure_ascii=False, indent=2))
            log_path = RESULT_COPY / "ContinuousSceneAimProbe.log"
            if log_path.exists():
                print("--- probe log ---")
                print(log_path.read_text(encoding="utf-8", errors="replace")[-5000:])
            passed = bool(verdict.get("ok")) and code == 0
            record.outcome = "passed" if passed else "failed"
            record.note = "exit=" + str(code) + " ok=" + str(verdict.get("ok")) + " reason=" \
                          + str(verdict.get("reason")) + " checks=" + str(len(verdict.get("rows") or []))
            return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
