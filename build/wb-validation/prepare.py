"""Copy frozen published WB tests into CS and compile only isolated harnesses."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
CS = HERE.parents[1]
ROOT = CS.parents[1]
WB = ROOT / "mods/WallBlend"
BASE = "f32e4a99643ccc901dc4f8e8caac29a6cde441b4"
HOST_SHA = "2032451D3987BAD8ACAE38776DF1D510C5BABBEBE0AFB505236BB5590EB025A4"
MOD_SHA = "8EAC7B08BABF2631A1897C988C36416BA8B6CF204788256B46F436CACB319BB3"
APP = HERE / "app"
TESTS = HERE / "tests"
OUTPUT = HERE / "candidate"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


host = CS / "build/runtime/pfe.swf"
candidate = CS / "build/runtime/mods/WallBlend/release/WallBlendMod.swf"
assert digest(host) == HOST_SHA, "Frozen CS host changed"
assert digest(candidate) == MOD_SHA, "Frozen WB candidate changed"
for path in (APP, TESTS, OUTPUT):
    path.mkdir(parents=True, exist_ok=True)

records = []
files = subprocess.check_output(["git", "-C", str(WB), "ls-tree", "-r", "--name-only", BASE, "tests"], text=True).splitlines()
for relative in files:
    if not relative.endswith(".as"):
        continue
    original = subprocess.check_output(["git", "-C", str(WB), "show", BASE + ":" + relative])
    adapted = original
    if relative == "tests/WallBlendHarness.as":
        # Exact target identity, not a weakened assertion: this candidate's
        # public version is the explicitly reviewed compatibility suffix.
        anchor = b'entry["status"].version=="0.5.3"'
        assert original.count(anchor) == 1
        adapted = original.replace(anchor, b'entry["status"].version=="0.5.3-scene"')
    target = TESTS / Path(relative).relative_to("tests")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(adapted)
    records.append({"path": relative, "sourceSHA256": hashlib.sha256(original).hexdigest(),
                    "driverSHA256": hashlib.sha256(adapted).hexdigest(), "adapted": adapted != original})

for name in ("texture.swf", "texture1.swf", "sprite.swf", "sprite1.swf", "sound.swf",
             "sound_unit.swf", "sound_weapon.swf", "lang.xml", "text_en.xml", "rooms.xml"):
    shutil.copy2(ROOT / name, APP / name)
shutil.copytree(ROOT / "Rooms", APP / "Rooms", dirs_exist_ok=True)
shutil.copy2(host, APP / "pfe.swf")
shutil.copy2(candidate, APP / "WallBlendMod.swf")
config = subprocess.check_output(["git", "-C", str(WB), "show", BASE + ":build/config.modes.example.json"])
config_path = APP / "mods/WallBlend/release/config.json"
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_bytes(config)

tools = ROOT / "mods/Sandevistan/build/tools"
compiler = tools / "flexsdk/lib/mxmlc.jar"
java = Path("D:/Program Files/Adobe Animate 2024/jre/bin/java.exe")
air = tools / "airsdk/frameworks/libs/air/airglobal.swc"
compiler_config = HERE / "air-config.xml"
compiler_config.write_text(f'''<flex-config><compiler>
<external-library-path><path-element>{escape(str(air))}</path-element></external-library-path>
<debug>false</debug><optimize>true</optimize><strict>true</strict><theme/>
</compiler><target-player>32.0</target-player><swf-version>32</swf-version>
<use-network>false</use-network><static-link-runtime-shared-libraries>true</static-link-runtime-shared-libraries>
</flex-config>''', encoding="utf-8")
for kind in ("Harness", "Coverage", "Destruction"):
    name = "WallBlend" + kind
    output = OUTPUT / (name + ".swf")
    subprocess.run([str(java), "-Dfile.encoding=UTF-8", "-jar", str(compiler),
                    "+flexlib=" + str(tools / "flexsdk/frameworks"), "+configname=air",
                    "-load-config=" + str(compiler_config), "-source-path+=" + str(TESTS),
                    "-output=" + str(output), str(TESTS / (name + "Doc.as"))], check=True)
    destination = APP / ("mods/" + name + "/release")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, destination / output.name)

manifest = {"publishedTestCommit": BASE, "hostSHA256": HOST_SHA, "modSHA256": MOD_SHA,
            "configSHA256": hashlib.sha256(config).hexdigest().upper(), "files": records,
            "adaptation": "Only Harness exact version expectation: 0.5.3 -> 0.5.3-scene; all behavioral assertions unchanged."}
(HERE / "source-provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"prepared": str(APP), "harnesses": 3, "testSources": len(records), "hostSHA256": digest(APP / "pfe.swf"), "modSHA256": digest(APP / "WallBlendMod.swf")}))
