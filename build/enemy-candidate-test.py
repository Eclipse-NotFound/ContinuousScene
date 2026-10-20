"""Validate the frozen sight/threat candidates against current installed mods."""
from pathlib import Path
import argparse,importlib.util,shutil
B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('enemy',B/'enemy-speed.py')
enemy=importlib.util.module_from_spec(spec);spec.loader.exec_module(enemy)
motion=enemy.motion
HOST='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
TDFC='7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5'

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);a=p.parse_args()
    with motion.Registration(owner='ContinuousScene / sight and threat regression / 01a13816-367b-7261-8e11-ca9152565dd9',purpose=a.name,run_dir=motion.RUNTIME,evidence=B.parent/'knowledge/experiments/evidence'/a.name,wait=600) as record:
        if motion.air_pids():raise RuntimeError('Other AIR present; untouched')
        assert enemy.digest(B/'generated/fog-typed/pfe.swf')==HOST
        assert enemy.digest(B/'generated/tdfc-threat/TDFCMod.swf')==TDFC
        enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',enemy.OUT/'ContinuousSceneProbe.swf')
        for suffix,flags in [('normal',['--encounter','--fixed-enemies','--benchmark','normal','--speed','24']),('scene',['--encounter','--fixed-enemies','--benchmark','scene','--speed','24']),('native',['--suite','native'])]:
            motion.prepare()
            shutil.copy2(enemy.OUT/'ContinuousSceneProbe.swf',motion.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            shutil.copy2(B/'generated/fog-typed/pfe.swf',motion.RUNTIME/'pfe.swf')
            shutil.copy2(B/'generated/tdfc-threat/TDFCMod.swf',motion.RUNTIME/'mods/TDFC/release/TDFCMod.swf')
            args=motion.parse_args(['--name',a.name+'-'+suffix,'--short','--no-lighting','--no-wall','--high-qos','--expect-no-signs','--window-width','2048','--window-height','1123']+flags)
            motion.run_owned(args,record)
if __name__=='__main__':main()
