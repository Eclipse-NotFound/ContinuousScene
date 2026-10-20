"""Registered render batching / threat-equivalence component investigation."""
from pathlib import Path
import argparse,importlib.util,shutil
B=Path(__file__).resolve().parent
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
enemy=load('enemy',B/'enemy-speed.py');motion=enemy.motion
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--only-threat',action='store_true');a=p.parse_args()
    with motion.Registration(owner='ContinuousScene / enemy and render fixes / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=a.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/a.name,wait=600) as record:
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',enemy.OUT/'ContinuousSceneProbe.swf')
        load('threat',B/'tdfc-threat.py').build()
        for suffix,extra in [('raster',['--render-perf']),('threat',['--threat-check'])]:
            if a.only_threat and suffix!='threat':continue
            motion.prepare()
            shutil.copy2(enemy.OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            if suffix=='threat':shutil.copy2(B/'generated/tdfc-threat/TDFCMod.swf',motion.RUNTIME/'mods/TDFC/release/TDFCMod.swf')
            args=motion.parse_args(['--name',a.name+'-'+suffix,'--no-lighting','--no-wall','--high-qos','--expect-no-signs','--window-width','2048','--window-height','1123']+extra)
            motion.run_owned(args,record)
if __name__=='__main__':main()
