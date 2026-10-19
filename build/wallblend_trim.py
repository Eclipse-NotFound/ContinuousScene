"""Isolated experiment: omit overlay pixels hidden by each native chunk crop.

Starts from the exact 0.5.6 scene source recipe, not WallBlend's unpublished HEAD.
All geometry and native sampling buffers retain their original padding.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import wallblend_compat as base
import wallblend_perf

STAGE = base.MOD / 'build/generated/wb-trim-source'

def once(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new, 1)

def apply(relative, s):
    if relative == 'src/wallblend/SceneBlendCache.as':
        s = once(s, '        private var entries:Dictionary',
                 '        public static var trimPadding:Boolean=true;\n        private var entries:Dictionary')
        s = once(s, '            loc.homeStable=region?',
                 '            if(trimPadding) loc.paintOutputClip=new Rectangle(s.gutter,s.gutter,s.side,s.side);\n'
                 '            else delete loc.paintOutputClip;\n            loc.homeStable=region?')
    if relative == 'src/wallblend/BlendLayer.as':
        s = once(s, '            if (rect.isEmpty()) return;',
                 '            if (rect.isEmpty() || ("paintOutputClip" in location && !rect.intersects(location.paintOutputClip))) return;')
    if relative == 'src/wallblend/BackgroundBlendLayer.as':
        s = once(s, '            if(rect.isEmpty()) return;',
                 '            if(rect.isEmpty() || ("paintOutputClip" in location && !rect.intersects(location.paintOutputClip))) return;')
    if relative == 'src/WallBlendMod.as':
        s = once(s, '    import flash.display.DisplayObject;',
                 '    import flash.desktop.NativeApplication;\n    import flash.events.DataEvent;\n    import flash.display.DisplayObject;')
        s = once(s, '"0.5.6-scene"', '"0.5.8-scene"')
        s = once(s, '                worldClass = getDefinitionByName("fe.World") as Class;',
                 '                if(NativeApplication.nativeApplication.applicationID!="pfe")\n'
                 '                    host.addEventListener("continuousSceneTrimPadding",function(e:DataEvent):void {\n'
                 '                        setScenePaddingTrim(e.data=="1");e.data="done";\n'
                 '                    });\n                worldClass = getDefinitionByName("fe.World") as Class;')
        s = once(s, '        public static function refreshNow():void {',
                 '        public static function setScenePaddingTrim(value:Boolean):void {\n'
                 '            SceneBlendCache.trimPadding=value;sceneCache.clear();onFrame(null);\n'
                 '        }\n\n        public static function refreshNow():void {')
    return s

def prepare():
    records=[]
    files=subprocess.check_output(['git','-C',str(base.WB),'ls-tree','-r','--name-only',base.BASE,'src'],text=True).splitlines()
    assert len(files)==13
    for relative in files:
        original=subprocess.check_output(['git','-C',str(base.WB),'show',base.BASE+':'+relative])
        published=wallblend_perf.apply(relative,base.candidate_source(relative,original).decode('utf-8-sig'))
        candidate=apply(relative,published)
        target=STAGE/Path(relative).relative_to('src');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(candidate,encoding='utf-8')
        records.append({'path':relative,'changed':published!=candidate,
                        'baseline':hashlib.sha256(published.encode()).hexdigest(),
                        'candidate':hashlib.sha256(candidate.encode()).hexdigest()})
    (STAGE/'air-config.xml').write_bytes((base.STAGE/'air-config.xml').read_bytes())
    (STAGE/'source-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps({'stage':str(STAGE),'files':len(records),'modified':[r['path'] for r in records if r['changed']]}))

if __name__=='__main__':prepare()
