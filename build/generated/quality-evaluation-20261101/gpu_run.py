"""Reuse the frozen v23 probe; only this private descriptor requests GPU mode.
This is an experimental rendering/quality diagnostic, not a deployment gate.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
BASE=HERE.parent/'camera-native-quality-v23-20261101'
spec=importlib.util.spec_from_file_location('v23_gpu_runner',BASE/'work.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
original_load=runner.load
def load(name,path):
    module=original_load(name,path)
    if name=='motion_review':
        original_prepare=module.prepare
        def prepare():
            original_prepare()
            p=module.RUNTIME/'application.xml';before=p.read_text('utf-8-sig')
            assert before.count('<renderMode>direct</renderMode>')==1
            after=before.replace('<renderMode>direct</renderMode>','<renderMode>gpu</renderMode>')
            after=after.replace('<depthAndStencil>true</depthAndStencil>','<depthAndStencil>false</depthAndStencil>')
            p.write_text(after,'utf-8')
            runner.write(module.RUNTIME/'gpu-diagnostic.json',{
                'experimentalOnly':True,'requestedRenderMode':'gpu','probeCombatQualification':False,
                'originalDescriptorSHA256':hashlib.sha256(before.encode()).hexdigest(),
                'wrapperSHA256':runner.sha(Path(__file__)),'probeReceiptSHA256':runner.sha(BASE/'build.json')})
        module.prepare=prepare
    return module
runner.load=load
parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--small',action='store_true');args=parser.parse_args()
runner.run(SimpleNamespace(name=args.name,small=args.small,dense=True,layers=False,legacy_menu=False,native_presentation=False,host='current'))
