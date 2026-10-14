"""Optional timing in isolated generated source only; never edits RV production source."""
from pathlib import Path
p=Path(__file__).resolve().parent/'generated/rv-production/RealisticVisionMod.as'
s=p.read_text(encoding='utf-8')
assert 'sceneTimings' not in s
s=s.replace('      private var lastFrameMs:int = 0;', '      private var sceneTimings:Object = {};\n      private var lastFrameMs:int = 0;')
names=['prepareOcclusion','computeFov','refreshWallField','fillFogCache','applyVision','hideEnemies']
for name in names:
    start=s.index('function '+name+'(')
    a=s.index('{',start)
    depth=1; b=a+1
    while depth:
        if s[b]=='{': depth+=1
        elif s[b]=='}': depth-=1
        b+=1
    body=s[a+1:b-1]
    tail='\n return false;\n' if name in ('prepareOcclusion','refreshWallField') else '\n'
    s=s[:a+1]+'\n var sceneT0:int=getTimer(); try {\n'+body+'\n } finally { this.sceneTimings["'+name+'"] = Number(this.sceneTimings["'+name+'"] || 0) + getTimer()-sceneT0; }'+tail+s[b-1:]
a=s.index('{',s.index('function autoStats('))+1
s=s[:a]+'\n this.fileLog("scene profile "+JSON.stringify(this.sceneTimings)); this.sceneTimings={};\n'+s[a:]
p.write_text(s,encoding='utf-8')
