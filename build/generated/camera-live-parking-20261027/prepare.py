from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def runner_source():
    s=(HERE.parent/'camera-far-live-detach-20261027/run.py').read_text('utf-8-sig')
    s=s.replace('camera-far-live-detach-1','camera-live-parking-1').replace('tests/SceneCameraRasterTrial.as','tests/SceneFarParkingTrial.as')
    s=one(s,"return reference.options(name)+['--draw-control','tilecrop','--presentation-check']", "return reference.options(name)+['--draw-control','rcnative']")
    start=s.index('def summarize(raw):');end=s.index('\n\ndef main():',start)
    s=s[:start]+"summary_module=load('live_parking_summary',HERE/'summary.py')\nsummarize=summary_module.summarize\n"+s[end:]
    s=s.replace('ContinuousScene / far live root detach / 01a13816','ContinuousScene / live owned-object parking / 01a13816')
    s=s.replace('960 static/moving live-root visibility controls; diagnostic only, no deployment','1200 live native sprint/combat intervals; lifecycle parking diagnostic, no deployment')
    s=one(s,'"""Paused moving-camera backdrop/object alpha attribution; diagnostic only."""','"""Live native sprint/combat Box/Bonus parking; diagnostic only."""')
    return s
if __name__=='__main__':
    s=runner_source();ast.parse(s);out=HERE/'run.py'
    if out.exists():assert out.read_text('utf-8-sig')==s
    else:out.write_text(s,'utf-8')
    print('Prepared live parking runner; seed source remains unchanged')
