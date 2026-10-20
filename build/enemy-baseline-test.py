"""Same fixed six raiders / viewport / local route in native and large scenes."""
from pathlib import Path
import argparse,importlib.util,shutil
B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('enemy',B/'enemy-speed.py');enemy=importlib.util.module_from_spec(spec);spec.loader.exec_module(enemy)
motion=enemy.motion
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--local-enemies',action='store_true');a=p.parse_args()
    with motion.Registration(owner='ContinuousScene / fixed combat baseline / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=a.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/a.name,wait=600) as record:
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',enemy.OUT/'ContinuousSceneProbe.swf')
        for mode in ['normal','scene']:
            motion.prepare()
            shutil.copy2(enemy.OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            args=motion.parse_args(['--name',a.name+'-'+mode,'--no-lighting','--no-wall','--high-qos','--expect-no-signs','--window-width','2048','--window-height','1123','--benchmark',mode,'--encounter','--fixed-enemies','--speed','24']+(['--local-enemies'] if a.local_enemies else []))
            motion.run_owned(args,record)
if __name__=='__main__':main()
