"""Uninstrumented camera intervals plus setup-only native environment checks."""
from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;VERSION='camera-environment-quiet-1'
BASE=HERE.parent/'camera-visible-room-fog-history-20261027'
POLICY=HERE.parent/'camera-visible-room-sampling-policy-20261027'
CHECKS=HERE/'environment-checks.as.inc'
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('environment_quiet_base',BASE/'prepare.py');policy=load('environment_quiet_policy',POLICY/'prepare.py');one=base.one
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'                selectReferenceSite();makeRoute();','                selectReferenceSite();\n                report.environmentChecks=environmentCheck();\n                makeRoute();')
    s=one(s,'        public function clear(w:*):Object {',CHECKS.read_text('utf-8-sig')+'\n        public function clear(w:*):Object {')
    return s
def runner_source():
    s=policy.runner_source().replace(policy.VERSION,VERSION).replace('== 87','== 86')
    s=one(s,"    assert r.sha(frozen/'tests/SceneCameraSampler.as') == r.sha(patch.SAMPLER)\n",'')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared native environment component checks and sampler-free camera intervals')
