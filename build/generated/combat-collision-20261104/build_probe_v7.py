"""probe-v7 = probe-v6 + live introspection of the bullet spatial grid.

Adds, per sample row:
  row.grid = {active, stamp, gx, gy, units, bucket, dense, max, error}

`active` proves the host candidate built `World.w.visual["csBulletGrid"]` (that
property lives on a plain `Sprite`, so unlike MainFE it must not throw), `units`
is the full `loc.units` scan size the old loop paid per bullet, `bucket` is how
many units a bullet at the viewport origin would actually scan, and `dense`/`max`
are the whole-table totals sampled every 15 frames.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = MOD.parents[1]
SDK = ROOT / 'mods/Sandevistan/build/tools'
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
SOURCE = MOD / 'build/generated/phase-20261104/probe-v5/probe-src'
sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
from test_registry import Registration

ROW_OLD = '                ready:g.sceneViewReady(),playerShot:playerShot,enemyShots:enemyShots,enemyTargets:enemyTargets};\n'
ROW_NEW = ROW_OLD + '''            try
            {
                var gridWorld:Class=flash.utils.getDefinitionByName("fe.World") as Class;
                var gridInfo:*=gridWorld["w"].vgui["__csBulletGridV1"];
                row.grid={active:gridInfo!=null,stamp:gridInfo?gridInfo.stamp:0,gx:gridInfo?gridInfo.gx:0,skip:gridInfo?gridInfo.skip:0,builds:gridInfo?gridInfo.build:0,
                    gy:gridInfo?gridInfo.gy:0,units:loc.units?loc.units.length:0,bucket:0,dense:0,max:0,error:null};
                if(gridInfo && gridInfo.buckets)
                {
                    var gridCell:Number=gridInfo.cell;
                    var gridScale:Number=cam.scaleV>0?cam.scaleV:1;
                    var gridX:int=int((-cam.vx-cam.quakeX)/gridScale/gridCell);
                    var gridY:int=int((-cam.vy-cam.quakeY)/gridScale/gridCell);
                    var viewBucket:Array=gridInfo.buckets[gridY*gridInfo.gx+gridX];
                    row.grid.bucket=viewBucket?viewBucket.length:0;
                    if(age%15==0)
                    {
                        var denseTotal:int=0;
                        var denseMax:int=0;
                        for each(var bucketArr:Array in gridInfo.buckets)
                        {
                            if(bucketArr)
                            {
                                denseTotal+=bucketArr.length;
                                if(bucketArr.length>denseMax)
                                {
                                    denseMax=bucketArr.length;
                                }
                            }
                        }
                        row.grid.dense=denseTotal;
                        row.grid.max=denseMax;
                    }
                }
            }
            catch(gridError:Error)
            {
                row.grid={active:false,error:gridError.message};
            }
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()


def build(tag):
    out = HERE / tag
    out.mkdir(exist_ok=False)
    src = out / 'probe-src'
    shutil.copytree(SOURCE, src)
    main = src / 'ContinuousSceneMotionMod.as'
    text = main.read_text(encoding='utf-8-sig')
    assert text.count(ROW_OLD) == 1, text.count(ROW_OLD)
    text = text.replace(ROW_OLD, ROW_NEW)
    # A production (diagnostic-free) host exposes no chunkDiagnostics; keep the
    # probe usable against both arms instead of failing every frame.
    CHUNK_OLD = '''            var ds:*=api.chunkDiagnostics;
            row.chunk={cancelCount:ds.cancelCount,cancelWork:ds.cancelWork,warmMs:ds.warmMs,forcedMs:ds.forcedMs,
                syncCount:ds.syncCount,syncMs:ds.syncMs,applyScanned:ds.applyScanned,markScanned:ds.markScanned,
                tickMs:ds.tickMs,ensureMs:ds.ensureMs,cullMs:ds.cullMs,tickCount:ds.tickCount,
                markMs:ds.markMs,markReplayed:ds.markReplayed,
                firstWindowMs:ds.firstWindowMs,missLoopMs:ds.missLoopMs,beginWarmMs:ds.beginWarmMs};'''
    CHUNK_NEW = '''            var ds:*=api.chunkDiagnostics;
            if(ds)
            {
                row.chunk={cancelCount:ds.cancelCount,cancelWork:ds.cancelWork,warmMs:ds.warmMs,forcedMs:ds.forcedMs,
                    syncCount:ds.syncCount,syncMs:ds.syncMs,applyScanned:ds.applyScanned,markScanned:ds.markScanned,
                    tickMs:ds.tickMs,ensureMs:ds.ensureMs,cullMs:ds.cullMs,tickCount:ds.tickCount,
                    markMs:ds.markMs,markReplayed:ds.markReplayed,
                    firstWindowMs:ds.firstWindowMs,missLoopMs:ds.missLoopMs,beginWarmMs:ds.beginWarmMs};
            }
            else
            {
                row.chunk=null;
            }'''
    assert text.count(CHUNK_OLD) == 1, text.count(CHUNK_OLD)
    text = text.replace(CHUNK_OLD, CHUNK_NEW)
    main.write_text(text, encoding='utf-8')
    config = out / 'compiler.xml'
    config.write_text(
        '<flex-config><target-player>32.0</target-player><compiler>'
        '<external-library-path><path-element>' + str(SDK / 'airsdk/frameworks/libs/air/airglobal.swc').replace('\\', '/') +
        '</path-element></external-library-path><source-path><path-element>' + src.as_posix() +
        '</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>',
        encoding='utf-8')
    output = out / 'ContinuousSceneMotionMod.swf'
    command = [str(JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar', str(SDK / 'flexsdk/lib/mxmlc.jar'),
               '+flexlib=' + str(SDK / 'flexsdk/frameworks'), '-load-config=' + str(config),
               '-swf-version=32', '-use-network=false', '-static-link-runtime-shared-libraries=true',
               '-link-report=' + str(out / 'link.xml'),
               '-output=' + str(output), str(src / 'ProbeDoc.as')]
    receipt = {'kind': 'probe-v7', 'source': sha(main), 'parent': sha(SOURCE / 'ContinuousSceneMotionMod.as'),
               'command': command, 'compiled': False, 'deployed': False}
    with Registration(owner='ContinuousScene / bullet grid probe', purpose=tag, resource='offline',
                      run_dir=out, evidence=out, wait=120) as lease:
        proc = None
        try:
            with (out / 'compiler.log').open('wb') as log:
                lease.before_launch('Bounded Java compiler, 512 MiB')
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(proc.pid)
                proc.wait(300)
            if proc.returncode:
                raise RuntimeError((out / 'compiler.log').read_text(encoding='utf-8', errors='replace'))
            receipt.update(compiled=True, output=sha(output))
            lease.outcome = 'passed'
            lease.note = 'probe compiled; runtime evidence separate'
        finally:
            if proc:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(15)
                lease.child_stopped()
            (out / 'build.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'tag': tag, 'output': receipt.get('output')}))


if __name__ == '__main__':
    build(sys.argv[1])

