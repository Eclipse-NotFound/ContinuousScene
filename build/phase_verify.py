"""Registered functional verification driver for CS mod builds.

Usage: python phase_verify.py <evidence-name> [mechanics]
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

EVIDENCE_NAME = sys.argv[1] if len(sys.argv) > 1 else "phase-verify-r1"
MECHANICS = len(sys.argv) > 2 and sys.argv[2] == "mechanics"
EVIDENCE = ROOT / "mods" / "ContinuousScene" / "knowledge" / "experiments" / "evidence" / EVIDENCE_NAME
MECHANICS_FLAG = BUILD / "runtime" / "mechanics-controls.flag"

cmd = [
    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", str(BUILD / "test.ps1"),
    "-Issues", "-DiagnosticsOnly", "-TimeoutSeconds", "300",
    "-EvidenceName", EVIDENCE_NAME,
]

if MECHANICS:
    MECHANICS_FLAG.write_text("phase-verify-mechanics", encoding="utf-8")
else:
    MECHANICS_FLAG.unlink(missing_ok=True)

with Registration(
    owner="ContinuousScene / phase verify",
    purpose=f"functional checks ({'mechanics+activity' if MECHANICS else 'issues doors/borders/fixed-visuals'})",
    resource="game-coexist",
    run_dir=str(BUILD / "runtime"),
    evidence=str(EVIDENCE),
    wait=900,
) as record:
    record.before_launch("issues probe / pfe-modsettings-continuous-scene / 14 mods + probe")
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
        record.note = "assertions passed; no timing claims"
    else:
        record.outcome = "failed"
        record.note = f"driver exit {code}; inspect evidence at {EVIDENCE}"
    MECHANICS_FLAG.unlink(missing_ok=True)
    sys.exit(code)
