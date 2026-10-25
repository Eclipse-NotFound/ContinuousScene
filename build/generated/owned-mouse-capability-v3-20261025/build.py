"""Build only this independent AIR fixture; never starts AIR or writes deployment files.

All compiler arguments are individual Python subprocess list elements. Existing
SWF/receipt and prior failed attempts are preserved, never silently replaced.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
JAVA = Path("D:/Program Files/Adobe Animate 2024/jre/bin/java.exe")
SDK = ROOT / "mods/Sandevistan/build/tools/flexsdk"
MXMLC = SDK / "lib/mxmlc.jar"
FLEXLIB = SDK / "frameworks"
AIRGLOBAL = ROOT / "mods/Sandevistan/build/tools/airsdk/frameworks/libs/air/airglobal.swc"
SOURCE = HERE / "src/OwnedMouseCapability.as"
CONFIG = HERE / "compile.xml"
OUTPUT = HERE / "build/OwnedMouseCapability.swf"
RECEIPT = HERE / "build/compile-receipt.json"
EXPECTED_SOURCE = "EA0A6B273F48603F6CB546991996A8FD7BAD6AB8014EC36D5ACD1AC24AB9EE4E"
EXPECTED_CONFIG = "B5567A9EAFEF822DDE0B98C3F1F06821F837CC0827105990D528E91AB4A46A90"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def decode(raw):
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding), encoding, False
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8", True


def main():
    if OUTPUT.exists() or RECEIPT.exists():
        raise RuntimeError("Refuse existing SWF or compile receipt; preserve earlier build")
    if sha(SOURCE) != EXPECTED_SOURCE or sha(CONFIG) != EXPECTED_CONFIG:
        raise RuntimeError("Reviewed fixture source/config fingerprint changed")
    # Only explicit local tool paths; no PATH lookup, shell, download or installation.
    for path in (JAVA, MXMLC, AIRGLOBAL, SOURCE, CONFIG):
        path.resolve(strict=True)
    FLEXLIB.resolve(strict=True)
    attempt = HERE / "build/compile-attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True, exist_ok=False)
    temporary = attempt / "java-tmp"
    temporary.mkdir()
    command = [str(JAVA), "-Xmx256m", "-Djava.io.tmpdir=" + str(temporary),
               "-jar", str(MXMLC), "+flexlib=" + str(FLEXLIB),
               "-load-config=" + str(CONFIG), "-swf-version=32",
               "-static-link-runtime-shared-libraries=true",
               "-compiler.source-path=" + str(SOURCE.parent),
               "-output=" + str(OUTPUT), str(SOURCE)]
    # Hash the bounded compiler lib directory because mxmlc's manifest loads
    # sibling jars. This is provenance, not a claim every jar was executed.
    compiler_inputs = [JAVA, AIRGLOBAL, *sorted((SDK / "lib").glob("*.jar"))]
    compiler_inputs = list(dict.fromkeys(compiler_inputs))
    frozen = {str(path): sha(path) for path in compiler_inputs}
    source_sha, config_sha = sha(SOURCE), sha(CONFIG)
    record = {"version": "owned-mouse-capability-build-3", "attempt": str(attempt),
              "startedEpochMs": time.time_ns() / 1_000_000,
              "cwd": str(HERE), "command": command, "compilerInputs": frozen,
              "sourceSHA256": source_sha, "configSHA256": config_sha,
              "exitCode": None, "compiled": False, "airStarted": False}
    save(attempt / "build-result.json", record)
    raw = b""
    try:
        completed = subprocess.run(command, cwd=str(HERE), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   shell=False, check=False, timeout=120,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        raw = completed.stdout
        record["exitCode"] = completed.returncode
    except subprocess.TimeoutExpired as error:
        raw = error.stdout or b""
        record["error"] = "Compiler timed out; subprocess.run killed and waited for its owned Java child"
        record["traceback"] = traceback.format_exc()
    except BaseException as error:
        record["error"] = repr(error)
        record["traceback"] = traceback.format_exc()
    finally:
        (attempt / "compile.raw.bin").write_bytes(raw)
        decoded, encoding, replaced = decode(raw)
        (attempt / "compile.txt").write_text(decoded, encoding="utf-8")
        record["rawSHA256"] = hashlib.sha256(raw).hexdigest().upper()
        record["decodedEncoding"] = encoding
        record["decodeHadReplacement"] = replaced
        record["outputExists"] = OUTPUT.is_file()
        if OUTPUT.is_file():
            record["outputBytes"] = OUTPUT.stat().st_size
            record["swfSHA256"] = sha(OUTPUT)
        try:
            record["compilerInputChanges"] = [path for path, digest in frozen.items() if sha(Path(path)) != digest]
            record["sourceUnchanged"] = sha(SOURCE) == source_sha
            record["configUnchanged"] = sha(CONFIG) == config_sha
        except BaseException as error:
            record["verificationError"] = repr(error)
        record["endedEpochMs"] = time.time_ns() / 1_000_000
        record["compiled"] = bool(record["exitCode"] == 0 and record.get("outputBytes", 0) > 0
            and not record.get("error") and not record.get("verificationError")
            and record.get("compilerInputChanges") == [] and record.get("sourceUnchanged")
            and record.get("configUnchanged"))
        save(attempt / "build-result.json", record)
        if record["compiled"]:
            # Exclusive creation prevents an unrelated build receipt being overwritten.
            with RECEIPT.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"compiled": record["compiled"], "evidence": str(attempt / "build-result.json"),
                      "exitCode": record["exitCode"]}, ensure_ascii=False))
    return 0 if record["compiled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
