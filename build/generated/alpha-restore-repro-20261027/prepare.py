from pathlib import Path
import ast
import hashlib
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'stage3d-capability-20261027'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def write(path,text):
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')
write(HERE/'compile.xml',(BASE/'compile.xml').read_text('utf-8-sig'))
build=(BASE/'build.py').read_text('utf-8-sig').replace('Stage3DCapability','AlphaRestoreRepro').replace('stage3d-capability-build-1','alpha-restore-build-1')
build=build.replace('9569E532F790DF0872667793537786126083C39F1B07DF7A49D2A8C4461A07E0',sha(HERE/'src/AlphaRestoreRepro.as'))
ast.parse(build);write(HERE/'build.py',build)
runner=(BASE/'run.py').read_text('utf-8-sig').replace('Stage3DCapability','AlphaRestoreRepro')
runner=runner.replace('stage3dcapability','alpharestorerepro').replace('app-stage3d-','app-alpha-restore-')
runner=runner.replace('stage3d-capability-runner-1','alpha-restore-runner-1').replace('capabilityPassed','diagnosticCompleted')
runner=runner.replace('<width>256</width><height>256</height>','<width>512</width><height>512</height>')
runner=runner.replace('Stage3D capability / 01a13816','Alpha restore reproduction / 01a13816')
runner=runner.replace('256px standalone context clear/readback; no game or timing claim','512px synthetic alpha restoration; no game or timing claim')
runner=runner.replace("and result.get('errors')==[] and result.get('contextDisposed')\n                        and result.get('allocations')==result.get('disposals')==1\n                        and result.get('readback',{}).get('pixels')==65536\n                        and result['readback']['maxRGB']<=1 and result['readback']['maxAlpha']==0)",
                      "and result.get('errors')==[] and result.get('completed')\n                        and result.get('allocations')==result.get('disposals')\n                        and len(result.get('cases',[]))==16\n                        and all(row['nativeRepeat']['equal'] for row in result['cases']))")
runner=runner.replace('Standalone capability only; no game performance or mixed-render acceptance','Synthetic alpha restoration diagnosis only; not game acceptance')
runner=runner.replace("driverInfo=out.get('airResult',{}).get('driverInfo')","restorationFailures=[row['name'] for row in out.get('airResult',{}).get('cases',[]) if not row['restored']['equal']]")
assert 'get(\'contextDisposed\')' not in runner and 'len(result.get(\'cases\',[]))==16' in runner
ast.parse(runner);write(HERE/'run.py',runner)
write(HERE/'README.md','''# 最小透明度恢复复现

16个合成显示树案例：矢量、缓存、模糊/发光、不同像素对齐位图、文字、嵌套变换与小颗粒。
每例等待实际呈现4帧，比较未改动的连续截图，再切换父层alpha并恢复、重复读回。
只记录绘制状态恢复现象；不加载游戏、不评价性能、不放宽游戏像素门槛。
沿已验证独立驱动：共享game登记、唯一ID/存储、私有桌面、输入指纹与内存预检，清理自有进程。
''')
print('Prepared standalone alpha restoration diagnostic; direct render mode matches game descriptor')
