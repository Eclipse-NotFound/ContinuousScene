"""Exact-module candidate: stopped projectiles no longer project stale velocity."""
from pathlib import Path
import argparse, importlib.util, json, shutil, subprocess, sys, statistics
B=Path(__file__).resolve().parent;MOD=B.parent;ROOT=MOD.parent.parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('stationary_release_helpers',B/'enemy-release.py');e=r.enemy;m=r.motion
OUT=B/'generated/stationary-threat-20261021'
BASE=B/'large-map/ContinuousSceneMod.swf'
BASE_SHA='7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST_SHA='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
SOURCE_SHA='01182FACDFB7AFBA7A03CCFF1C3C28E14219E8FE654118149C50FCF7261AC0F7'
def prepare():
    assert r.sha(BASE)==r.sha(MOD/'release/ContinuousSceneMod.swf')==BASE_SHA
    assert r.sha(ROOT/'pfe.swf')==HOST_SHA
    source=MOD/'src/NativeSceneActivity.as';assert r.sha(source)==SOURCE_SHA
    s=source.read_text('utf-8-sig')
    s=e.once(s,'            var threats:Array=[];', '''            var carrier:*=w.main.getChildByName("ContinuousSceneCarrier");
            var stationary:Boolean=carrier["nativeAPI"]["stationaryThreatsEnabled"]!==false;
            s.stationary=stationary;s.stopped=0;s.projected=0;
            var threats:Array=[];''')
    s=e.once(s,'''                threats.push({l:Math.min(p.X,p.X+p.dx*4)-radius,r:Math.max(p.X,p.X+p.dx*4)+radius,
                    t:Math.min(p.Y,p.Y+p.dy*4)-radius,b:Math.max(p.Y,p.Y+p.dy*4)+radius});''', '''                // Impacted bullets retain velocity while their hit/explosion finishes.
                // Keep the local damage radius; only live movement predicts ahead.
                var stopped:Boolean=stationary && p.babah;
                var aheadX:Number=stopped?p.X:p.X+p.dx*4;
                var aheadY:Number=stopped?p.Y:p.Y+p.dy*4;
                if(p.babah)++s.stopped;else ++s.projected;
                threats.push({l:Math.min(p.X,aheadX)-radius,r:Math.max(p.X,aheadX)+radius,
                    t:Math.min(p.Y,aheadY)-radius,b:Math.max(p.Y,aheadY)+radius});''')
    s=e.once(s,'{awake:current.awake,asleep:current.asleep}', '{awake:current.awake,asleep:current.asleep,version:"stationary-threats-1",stationaryThreats:current.stationary,stopped:current.stopped,projected:current.projected}')
    s=s.replace(':*=',':* = ') # FFDec otherwise tokenizes this as *=.
    s=e.once(s,'var c:* = w.cam,scale:Number=c.scaleV;','var c:* = w.cam; var scale:Number=c.scaleV;')
    s=e.once(s,'var left:Number=-c.vx/scale-600,top:Number=-c.vy/scale-600;','var left:Number=-c.vx/scale-600; var top:Number=-c.vy/scale-600;')
    s=e.once(s,'var right:Number=left+c.screenX/scale+1200,bottom:Number=top+c.screenY/scale+1200;','var right:Number=left+c.screenX/scale+1200; var bottom:Number=top+c.screenY/scale+1200;')
    s=e.once(s,'var s:Object=rooms[u.loc],r:Object=s.records[u];','var s:Object=rooms[u.loc]; var r:Object=s.records[u];')
    out=OUT/'source/NativeSceneActivity.as';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s,'utf-8')
    return dict(base=BASE_SHA,host=HOST_SHA,originalSource=SOURCE_SHA,source=r.sha(out),deployed=False)
def build():
    with m.Registration(owner='ContinuousScene / stationary threat build / 01a13816',purpose='Only NativeSceneActivity import and semantic audit',run_dir=OUT,evidence=OUT/'build.json',wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        meta=prepare()
        def ff(*args):subprocess.run([str(e.JAVA),'-Xmx1200m','-jar',str(e.TOOLS/'ffdec/ffdec-cli.jar'),*map(str,args)],check=True)
        ff('-swf2xml',BASE,OUT/'baseline.xml')
        ff('-importScript',BASE,OUT/'compiled.swf',OUT/'source')
        ff('-swf2xml',OUT/'compiled.swf',OUT/'compiled.xml')
        # FFDec recompiles private namespaces. Keep the original ABC skeleton
        # and import only the two intended bodies with private references mapped.
        subprocess.run([sys.executable,str(B/'stationary-threat-audit.py'),'--base',str(OUT/'baseline.xml'),'--candidate',str(OUT/'compiled.xml'),'--retain-unchanged-bodies','--out',str(OUT/'retained.xml')],check=True)
        ff('-xml2swf',OUT/'retained.xml',OUT/'ContinuousSceneMod.swf')
        ff('-swf2xml',OUT/'ContinuousSceneMod.swf',OUT/'candidate.xml')
        subprocess.run([sys.executable,str(B/'stationary-threat-audit.py'),'--base',str(OUT/'baseline.xml'),'--candidate',str(OUT/'candidate.xml'),'--out',str(OUT/'audit.json')],check=True)
        e.compile_as(MOD/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        meta.update(candidate=r.sha(OUT/'ContinuousSceneMod.swf'),probe=r.sha(OUT/'ContinuousSceneProbe.swf'))
        r.save(OUT/'build.json',meta);lease.outcome='passed';lease.note='Only candidate build; no deployment'
        print(json.dumps(meta),flush=True)
def run(a):
    with m.Registration(owner='ContinuousScene / stationary threat test / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();assert baseline['pfe.swf']==HOST_SHA
        meta=r.read(OUT/'build.json');assert r.sha(OUT/'ContinuousSceneMod.swf')==meta['candidate']
        m.prepare()
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        shutil.copy2(OUT/'ContinuousSceneMod.swf',m.RUNTIME/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
        options=['--name',a.name,'--high-qos','--land',a.land,'--window-width','2048','--window-height','1123']
        if a.mode=='checks':options+=['--presentation-check','--draw-control','stationary','--expect-no-signs']
        elif a.mode=='native':options+=['--suite','native']
        else:options+=['--encounter','--fixed-enemies','--benchmark','scene','--speed','24','--short','--expect-no-signs','--draw-control','stationary']
        options+=['--vision'] if a.full else ['--no-lighting','--no-wall']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production dependency drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(meta['candidate'] if path=='mods/ContinuousScene/release/ContinuousSceneMod.swf' else digest),('Dependency drift',path)
        summary=dict(name=a.name,checks=len(result['assertions']),candidate=meta['candidate'])
        if a.mode=='combat':
            assert r.read(r.E/a.name/'process-policy.json')['performanceEligible']
            summary['samples']=[]
            for row in result['samples']:
                f=row['frames'];assert len(f)==300 and row['empty']==0
                summary['samples'].append(dict(name=row['name'],median=statistics.median(f),mean=statistics.mean(f),p95=sorted(f)[284],maximum=max(f),over100=sum(x>100 for x in f),script=statistics.mean(row['totalScript']),native=statistics.mean(row['nativeBand']),activity=row['activity'],shots=row.get('encounter'),misses=row['misses']))
        r.save(OUT/(a.name+'-summary.json'),summary);print(json.dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Checks completed; performance conclusion requires comparison'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','build','run']);p.add_argument('--name');p.add_argument('--mode',choices=['checks','combat','native'],default='checks');p.add_argument('--land',default='random_mane');p.add_argument('--full',action='store_true');a=p.parse_args()
    if a.action=='prepare':print(json.dumps(prepare()))
    elif a.action=='build':build()
    else:
        assert a.name;run(a)
