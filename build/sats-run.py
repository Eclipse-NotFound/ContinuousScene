"""Registered, isolated SATS pixel/UI checks and existing gameplay regression."""
from pathlib import Path
import argparse, importlib.util, shutil
B=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
enemy=load('sats_enemy',B/'enemy-speed.py');motion=enemy.motion
OUT=B/'generated/sats-tests-20261021'
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True)
    p.add_argument('--mode',choices=['pixels','native','motion','normal'],default='pixels')
    p.add_argument('--effects',choices=['off','full'],default='off')
    p.add_argument('--land',choices=['random_mane','random_plant'],default='random_mane')
    p.add_argument('--host',type=Path,default=B/'generated/sats-viewport-20261021-combined/pfe.swf')
    p.add_argument('--reuse-build',action='store_true');p.add_argument('--wait',type=int,default=300)
    a=p.parse_args();OUT.mkdir(exist_ok=True)
    with motion.Registration(owner='ContinuousScene / SATS regression / 01a13816',purpose=a.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/a.name,wait=a.wait) as record:
        if motion.air_pids():raise RuntimeError('Other AIR is running; untouched')
        if not a.reuse_build:enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        motion.prepare()
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        shutil.copy2(a.host,motion.RUNTIME/'pfe.swf')
        options=['--name',a.name,'--high-qos','--land',a.land,'--window-width','2048','--window-height','1123']
        if a.mode=='native':options+=['--suite','native']
        elif a.mode=='pixels':options+=['--sats-check','--expect-no-signs']
        else:options+=['--encounter','--fixed-enemies','--benchmark','normal' if a.mode=='normal' else 'scene','--speed','24','--short','--expect-no-signs']
        if a.effects=='off':options+=['--no-lighting','--no-wall']
        else:options+=['--vision']
        motion.run_owned(motion.parse_args(options),record)
if __name__=='__main__':main()
