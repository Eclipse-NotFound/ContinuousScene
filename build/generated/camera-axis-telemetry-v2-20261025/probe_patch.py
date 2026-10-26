"""Only add native telemetry anchors to the already-validated axis fixture."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-axis-motion-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-axis-motion-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(PATCH_SOURCE)=='D06BCF4622ED8C4F25CF67390555458EA0152F06F1BFF9D1877903CC4E597383'
assert sha(ORIGINAL)=='5A89E4EFA30792002E8A96C5D29EE56C749D8096A7D94EFF327FD1FE6F5195D4'
spec=importlib.util.spec_from_file_location('native_axis_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

def helper_source():
    original=ORIGINAL.read_text('utf-8-sig');assert original==base.helper_source()
    edits=[('    import flash.system.System;','    import flash.system.System;\n    import flash.profiler.Telemetry;'),
        ('version:"camera-axis-motion-1"','version:"camera-axis-telemetry-1"'),
        ('                require(w!=null && p!=null,"Missing world/presenter");',
         '                require(Telemetry.connected,"Native telemetry not connected");\n                require(w!=null && p!=null,"Missing world/presenter");'),
        ('                            report.complete=true;report.passed=true;clear(w);',
         '                            Telemetry.sendMetric("remains.camera.end",{frame:960,timer:getTimer(),appId:NativeApplication.nativeApplication.applicationID});\n                            report.complete=true;report.passed=true;clear(w);'),
        ('            var at:int=getTimer();\n            var target:Object=row.moving?route[age]:views[0];',
         '            require(Telemetry.connected,"Native telemetry disconnected during measurement");\n            Telemetry.sendMetric("remains.camera.frame",{frame:segment*120+age,segment:segment,condition:row.condition,timer:getTimer(),appId:NativeApplication.nativeApplication.applicationID});\n            var at:int=getTimer();\n            var target:Object=row.moving?route[age]:views[0];')]
    out=original
    for a,b in edits:assert out.count(a)==1,a;out=out.replace(a,b,1)
    reverse=out
    for a,b in reversed(edits):assert reverse.count(b)==1;reverse=reverse.replace(b,a,1)
    assert reverse==original
    return out

def transform(source):return base.transform(source)
def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

if __name__=='__main__':
    assert not HELPER.exists();HELPER.parent.mkdir(parents=True,exist_ok=True);HELPER.write_text(helper_source(),'utf-8')
