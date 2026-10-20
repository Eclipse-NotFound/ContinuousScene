"""One registered build + sight equivalence + ABBA group; isolated files only."""
from pathlib import Path
import argparse, importlib.util, shutil
B=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
enemy=load('enemy',B/'enemy-speed.py');motion=enemy.motion
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--reuse',action='store_true');a=p.parse_args()
    with motion.Registration(owner='ContinuousScene / sight loop / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=a.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/a.name,wait=300) as record:
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        if not a.reuse:
            enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',enemy.OUT/'ContinuousSceneProbe.swf')
            load('typed',B/'fog-typed.py').build()
        for suffix,options in [('mane-pixels',['--fog-check']),('plant-pixels',['--fog-check','--land','random_plant']),('abba',['--fog-typed-abba','--benchmark','scene'])]:
            motion.prepare()
            shutil.copy2(B/'generated/fog-typed/pfe.swf',motion.RUNTIME/'pfe.swf')
            shutil.copy2(enemy.OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            args=motion.parse_args(['--name',a.name+'-'+suffix,'--short','--no-lighting','--no-wall','--high-qos','--expect-no-signs']+options)
            motion.run_owned(args,record)
if __name__=='__main__':main()
