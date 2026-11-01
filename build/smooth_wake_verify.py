"""Registered functional verification for the smooth-wake 0.9.4 build.

Wraps build/test.ps1 -Issues -DiagnosticsOnly in the shared test registry
(game-coexist) and registers the isolated ADL child PID it launches.
"""
import re
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
ROOT = BUILD.parents[2]
sys.path.insert(0, str(ROOT / "mods" / "ModLoader" / "tools"))
from test_registry import Registration  # noqa: E402

EVIDENCE_NAME = "smooth-wake-v094-mechanics-r1"
EVIDENCE = ROOT / "mods" / "ContinuousScene" / "knowledge" / "experiments" / "evidence" / EVIDENCE_NAME

cmd = [
    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", str(BUILD / "test.ps1"),
    "-Issues", "-DiagnosticsOnly", "-TimeoutSeconds", "300",
    "-EvidenceName", EVIDENCE_NAME,
]

with Registration(
    owner="ContinuousScene / smooth wake 0.9.4",
    purpose="v0.9.4 wake-budget mechanics+activity functional checks",
    resource="game-coexist",
    run_dir=str(BUILD / "runtime"),
    evidence=str(EVIDENCE),
    wait=900,
) as record:
    record.before_launch("issues-mechanics / pfe-modsettings-continuous-scene / 14 mods + probe")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", cwd=str(BUILD))
    child_pid = None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        m = re.search(r"Isolated AIR PID (\d+)", line)
        if m and child_pid is None:
            child_pid = int(m.group(1))
            record.child(child_pid)
    code = proc.wait()
    if child_pid is not None:
        record.child_stopped()
    if code == 0:
        record.outcome = "passed"
        record.note = "smooth-wake v0.9.4 mechanics+activity assertions passed; no timing claims"
    else:
        record.outcome = "failed"
        record.note = f"driver exit {code}; inspect evidence at {EVIDENCE}"
    sys.exit(code)
