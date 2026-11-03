"""Exact method-only host candidates, preserving original class layout/loaders."""
from pathlib import Path
import importlib.util,json,re,subprocess,sys
import stutter_opt as opt

sys.path.insert(0,str(opt.MOD/'build'))
from pcode_plan import abc_methods

def method(text,name):
    start=re.search(r'^      (?:public|private|internal|protected) function '+name+r'\(',text,re.M).start()
    following=re.search(r'^      (?:public|private|internal|protected) (?:override )?function ',text[start+7:],re.M)
    end=start+7+following.start() if following else text.rfind('   }')
    return text[start:end]

def once(text,old,new):
    assert text.count(old)==1,(old[:75],text.count(old))
    return text.replace(old,new)

def diagnostic(text):
    changes={}
    name='sceneCancelWarm';old=method(text,name)
    changes[name]=once(old,'         this.sceneWarmJob = null;',
        '''         var diag:* = World.w.visual.root["sceneDiagStats"];
         if(diag) {
            ++diag.cancelCount;diag.cancelWork += job.work;
            if(diag.events.length < 3000)diag.events.push({kind:"cancel",at:getTimer(),cx:job.cx,cy:job.cy,work:job.work,step:job.at,reason:diag.dirtyKind});
         }
         this.sceneWarmJob = null;''')
    name='sceneApply';old=method(text,name)
    new=once(old,'         this.sceneCancelWarm(affected);',
        '''         var diag:* = World.w.visual.root["sceneDiagStats"];
         if(diag){diag.dirtyKind=kind;++diag.applyCalls;}
         this.sceneCancelWarm(affected);''')
    changes[name]=once(new,'            for each(entry in this.sceneChunks)\n            {',
        '            for each(entry in this.sceneChunks)\n            {\n               if(diag)++diag.applyScanned;')
    name='sceneRestoreMarks';old=method(text,name)
    new=once(old,'         try\n         {','         var diag:* = World.w.visual.root["sceneDiagStats"];\n         try\n         {')
    changes[name]=once(new,'            for each(item in this.sceneMarks)\n            {',
        '            for each(item in this.sceneMarks)\n            {\n               if(diag)++diag.markScanned;')
    name='sceneAdvanceWarm';old=method(text,name)
    new=once(old,'         start = int(getTimer());',
        '         var diag:* = World.w.visual.root["sceneDiagStats"];\n         start = int(getTimer());')
    new=once(new,'                  if(job.steps[job.at].call(null) !== false)',
        '                  var stepAt:int=getTimer();\n                  var stepIndex:int=job.at;\n                  if(job.steps[job.at].call(null) !== false)')
    new=once(new,'                     ++job.at;\n                  }',
        '''                     ++job.at;
                  }
                  if(diag) {
                     var stepMs:int=getTimer()-stepAt;
                     ++diag.stepCount;diag.stepMs+=stepMs;diag.maxStepMs=Math.max(diag.maxStepMs,stepMs);
                     if(stepMs>=8 && diag.events.length<3000)diag.events.push({kind:"step",at:getTimer(),ms:stepMs,step:stepIndex,cx:job.cx,cy:job.cy,force:force});
                  }''')
    changes[name]=once(new,'         job.work += elapsed;',
        '         job.work += elapsed;\n         if(diag){diag.warmMs+=elapsed;if(force)diag.forcedMs+=elapsed;}')
    name='sceneRender';old=method(text,name)
    new=once(old,'         this.sceneX = cx * this.sceneSide - this.sceneGutter;',
        '         var diag:* = World.w.visual.root["sceneDiagStats"];\n         var renderAt:int=getTimer();\n         this.sceneX = cx * this.sceneSide - this.sceneGutter;')
    changes[name]=once(new,'         ++this.sceneResident;',
        '''         ++this.sceneResident;
         if(diag){++diag.syncCount;diag.syncMs+=getTimer()-renderAt;
            if(diag.events.length<3000)diag.events.push({kind:"sync",at:getTimer(),ms:getTimer()-renderAt,cx:cx,cy:cy});}''')
    for name,new in changes.items():
        new=new.replace('var diag:* = World.w.visual.root["sceneDiagStats"];',
            'var diagCarrier:* = World.w.visual.root.getChildByName("ContinuousSceneCarrier");\n         var diag:* = diagCarrier ? diagCarrier["nativeAPI"]["chunkDiagnostics"] : null;')
        text=text.replace(method(text,name),new)
    return text,list(changes)

def build(tag,kind,base_tag=None):
    out=opt.WORK/tag;out.mkdir(exist_ok=False)
    baseline=opt.read(opt.WORK/'baseline.json')
    formal=opt.ROOT/'pfe.swf';assert opt.sha(formal)==baseline['formal'][str(formal)]
    host=opt.WORK/base_tag/'candidate.swf' if base_tag else formal
    predecessor=opt.read(opt.WORK/base_tag/'build.json') if base_tag else None
    if predecessor:assert predecessor['compiled'] and opt.sha(host)==predecessor['output']
    if kind=='diagnostic':
        cls='fe.graph.Grafon';source=opt.MOD/'build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as'
        content,names=diagnostic(source.read_text(encoding='utf-8-sig'))
    elif kind=='collision':
        cls='fe.weapon.Bullet';source=opt.MOD/'build/generated/camera-spatial-20261101/bullet-src/fe/weapon/Bullet.as'
        content=source.read_text(encoding='utf-8-sig');start=content.index('         var _collisionUnits:Array = loc.units;')
        end=content.index('         for each(_loc2_ in _collisionUnits)',start)+len('         for each(_loc2_ in _collisionUnits)')
        content=content[:start]+'         for each(_loc2_ in loc.units)'+content[end:];names=['run']
    elif kind=='dead-list':
        cls='fe.graph.Grafon';source=opt.MOD/'build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as'
        content=source.read_text(encoding='utf-8-sig');old=method(content,'sceneTick')
        new='''      public function sceneTick() : void
      {
         if(!this.sceneLarge || this.loc == null)return;
         var camera:* = World.w.cam;
         var scale:Number = Number(camera.scaleV > 0 ? camera.scaleV : 1);
         this.sceneEnsure((-camera.vx-camera.quakeX)/scale,(-camera.vy-camera.quakeY)/scale,camera.screenX/scale,camera.screenY/scale);
         this.sceneCullSurfaces();
      }

'''
        content=content.replace(old,new);names=['sceneTick']
    else:raise ValueError(kind)
    target=out/'source'/Path(*cls.split('.')).with_suffix('.as');target.parent.mkdir(parents=True);target.write_text(content,encoding='utf-8')
    receipt={'kind':kind,'host':opt.sha(formal),'inputHost':opt.sha(host),'baseTag':base_tag,
        'source':opt.sha(target),'methods':names,'compiled':False,'deployed':False}
    from test_registry import Registration
    with Registration(owner='ContinuousScene / stutter host candidate',purpose=tag,resource='offline',run_dir=out,evidence=out,wait=60) as lease:
        def ff(*args):
            command=[str(opt.JAVA),'-Xmx1400m','-jar',str(opt.SDK/'ffdec/ffdec-cli.jar'),*map(str,args)]
            proc=None
            try:
                lease.before_launch('Owned FFDec method patch compiler, 1400 MiB heap')
                with (out/'ffdec.log').open('ab') as log:
                    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    lease.child(proc.pid);proc.wait(420)
                if proc.returncode:raise RuntimeError('FFDec failed; retained ffdec.log')
            finally:
                if proc:
                    if proc.poll() is None:proc.kill();proc.wait(15)
                    lease.child_stopped()
        try:
            ff('-swf2xml',host,out/'base.xml')
            ff('-importScript',host,out/'donor.swf',out/'source')
            for label,swf in [('original',host),('donor',out/'donor.swf')]:
                ff('-format','script:pcode','-selectclass',cls,'-export','script',out/(label+'-pcode'),swf)
            relative=Path(*cls.split('.')).with_suffix('.pcode')
            original=(out/'original-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
            donor=(out/'donor-pcode/scripts'/relative).read_text(encoding='utf-8-sig')
            if kind=='collision':
                archived=(opt.MOD/'build/generated/camera-spatial-20261101/donor-bullet-pcode/scripts/fe/weapon/Bullet.pcode').read_text(encoding='utf-8-sig')
                def run_body(value):
                    start=value.index('function run(')
                    return value[start:value.index('end ; method',start)]
                assert run_body(original)==run_body(archived),'Bullet source provenance changed'
            methods=abc_methods(out/'base.xml');specs=[];keys=[]
            for name in names:
                start=re.search(r'\bfunction '+name+r'\(',donor).end()
                first=re.search(r'\bmethod\s*\n',donor[start:]).start()+start
                last=donor.index('end ; method',first)+len('end ; method');code=donor[first:last]
                old_start=re.search(r'\bfunction '+name+r'\(',original).end();old_end=original.index('end ; method',old_start)
                old_ns=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',original[old_start:old_end])))
                new_ns=list(dict.fromkeys(re.findall(r'PrivateNamespace\([^)]*\)',code)))
                if new_ns:
                    assert len(old_ns)==len(new_ns),(name,old_ns,new_ns)
                    for a,b in zip(new_ns,old_ns):code=code.replace(a,b)
                prior=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',original))
                used=set(re.findall(r'QName\(PrivateNamespace\([^)]*\),"([^"]+)"\)',code));assert used<=prior,(name,used-prior)
                key=next(n for n in methods if n.endswith(':'+name) and cls+'::' in n)
                path=out/(name+'.pcode');path.write_text(code+'\n',encoding='utf-8');keys.append(key)
                specs.extend([cls,str(path),str(methods[key][0])])
            (out/'replace.txt').write_text('\n'.join(specs)+'\n',encoding='utf-8')
            ff('-replace',host,out/'candidate.swf',out/'replace.txt')
            ff('-swf2xml',out/'candidate.swf',out/'candidate.xml')
            audit=opt.load('stutter_audit',opt.MOD/'build/renderer-audit.py')
            assert audit.classes(out/'base.xml')==audit.classes(out/'candidate.xml'),'Class layout changed'
            after=abc_methods(out/'candidate.xml')
            changed=[n for n,pair in methods.items() if (None if pair is None else pair[1].attrib['codeBytes'])!=(None if after[n] is None else after[n][1].attrib['codeBytes'])]
            assert set(changed)==set(keys),(changed,keys)
            baseline_xml=Path(predecessor['baselineXml']) if predecessor else out/'base.xml'
            original_methods=abc_methods(baseline_xml)
            combined=[n for n,pair in original_methods.items() if (None if pair is None else pair[1].attrib['codeBytes'])!=(None if after[n] is None else after[n][1].attrib['codeBytes'])]
            expected=set(keys)|set(predecessor.get('combinedChanges',[]) if predecessor else [])
            assert set(combined)==expected,(combined,expected)
            assert opt.sha(formal)==receipt['host'],'Formal host changed during build'
            receipt.update(compiled=True,output=opt.sha(out/'candidate.swf'),changedMethods=changed,
                combinedChanges=combined,baselineXml=str(baseline_xml),classesUnchanged=True)
            lease.outcome='passed';lease.note='Method-only candidate built, runtime evidence pending'
        finally:(out/'build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))

if __name__=='__main__':build(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
