"""Compile only the deployed TDFC source lineage plus the narrow scene bridge.

The current TDFC checkout also contains unpublished networking work. Do not ship it.
"""
from pathlib import Path
import subprocess,hashlib,json
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]/'TDFC'
OUT=ROOT/'generated/tdfc-scene-compat'
BASE='fb73655'
assert hashlib.sha256((REPO/'release/TDFCMod.swf').read_bytes()).hexdigest().upper()=='99BFBAA68229635FBAA496EF9287A94BB9EA7C65D71339CEF3FDE65F47E30275'
files=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',BASE,'src'],text=True).splitlines()
for name in files:
    dest=OUT/Path(name).relative_to('src');dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(subprocess.check_output(['git','-C',str(REPO),'show',BASE+':'+name]))
head=(REPO/'src/TdfcRuntime.as').read_text(encoding='utf-8-sig')
start=head.index('     var sceneGrafon:')
end=head.index('      if(u===gg)',start)
insert=head[start:end]
source=(OUT/'TdfcRuntime.as').read_text(encoding='utf-8-sig')
mark=next(line for line in head.splitlines() if 'TdfcLog.line("scene-compat"' in line)
anchor='   overlay=new DebugOverlay(host,saveReport);'
assert source.count(anchor)==1
source=source.replace(anchor,mark+'\n'+anchor)
old='     for each(var u:* in units) {\n'
assert source.count(old)==1
(OUT/'TdfcRuntime.as').write_text(source.replace(old,insert),encoding='utf-8')
(OUT/'source-origin.json').write_text(json.dumps({'baseCommit':BASE,'installedSHA256':'99BFBAA68229635FBAA496EF9287A94BB9EA7C65D71339CEF3FDE65F47E30275','onlyChangedSource':'TdfcRuntime.as','bridgeSHA256':hashlib.sha256(insert.encode()).hexdigest()},indent=2))
print('Prepared deployed TDFC lineage + scene scheduling bridge')
