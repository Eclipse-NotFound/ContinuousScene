"""Same-instance A/B camera fixture; generated from the frozen native-once recipe."""
from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-native-once-20261028'
VERSION='camera-environment-paired-1'
ORDER='[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0]'
NAMES='["native-static","native-horizontal","native-vertical","native-combined","cached-static","cached-horizontal","cached-vertical","cached-combined"]'

def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('paired_native_generator',BASE/'prepare.py');one=base.one

def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array='+ORDER+';')
    s=one(s,'        private var plannedAge:int=-1;','''        private var plannedAge:int=-1;
        private var environmentState:Object;
        private var hadEnvironmentSwitch:Boolean;
        private var savedEnvironmentSwitch:*;''')
    s=one(s,'measurementFrames:960,','measurementFrames:1920,')
    s=one(s,'"All intervals and observer work retained; no new rendering optimization applied."',
        '"Same-instance native/cached key branches; common diagnostic selector and all boundary intervals retained. Not a production host."')
    s=one(s,'                report.environmentChecks=environmentCheck();','''                require(grafon.sceneLarge,"Paired environment fixture requires a continuous scene");
                environmentState=api.state(location.land);
                require(environmentState!=null && environmentState.loc===location,"Missing paired environment state");
                hadEnvironmentSwitch=environmentState.hasOwnProperty("_csUseEnvironmentKeyCacheV1");
                savedEnvironmentSwitch=environmentState._csUseEnvironmentKeyCacheV1;
                environmentState._csUseEnvironmentKeyCacheV1=false;
                report.nativeEnvironmentChecks=environmentCheck();
                require(!report.nativeEnvironmentChecks.cachePresent,"Native branch unexpectedly initialized cache");
                environmentState._csUseEnvironmentKeyCacheV1=true;
                report.environmentChecks=environmentCheck();
                require(report.environmentChecks.cachePresent,"Cached branch did not initialize cache");
                environmentState._csUseEnvironmentKeyCacheV1=false;''')
    s=one(s,'report.nativeSchedules==961 && report.nativeCaptures==960','report.nativeSchedules==1921 && report.nativeCaptures==1920')
    s=one(s,'                    row.gg.push(pending.gg);row.scene.push(pending.scene);',
        '                    row.gg.push(pending.gg);row.scene.push(pending.scene);row.cacheModes.push(pending.cacheMode);')
    s=one(s,'mode:["native-static","native-horizontal","native-vertical","native-combined"][condition]',
        'mode:'+NAMES+'[condition]')
    s=one(s,'hidden:false,moving:condition!=0,startAtMs:previous,',
        'hidden:false,moving:(condition%4)!=0,cacheEnabled:condition>=4,axis:condition%4,cacheModes:[],startAtMs:previous,')
    s=one(s,'x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y',
        'x:row.axis==2?views[0].x:target.x,y:row.axis==1?views[0].y:target.y')
    s=one(s,'            ++report.nativeCaptures;','''            require(environmentState._csUseEnvironmentKeyCacheV1===row.cacheEnabled,"Wrong native key branch during capture");
            ++report.nativeCaptures;''')
    s=one(s,'pending={vx:cam.vx,vy:cam.vy,','pending={cacheMode:environmentState._csUseEnvironmentKeyCacheV1,vx:cam.vx,vy:cam.vy,')
    s=one(s,'                var condition:int=order[nextSegment];','''                var selection:int=order[nextSegment],condition:int=selection%4;
                environmentState._csUseEnvironmentKeyCacheV1=selection>=4;''')
    s=one(s,'            disposeOwned();\n            if(saved!=null && saved.ready)', '''            disposeOwned();
            try {
                if(environmentState!=null) {
                    if(hadEnvironmentSwitch)environmentState._csUseEnvironmentKeyCacheV1=savedEnvironmentSwitch;
                    else delete environmentState._csUseEnvironmentKeyCacheV1;
                    require(environmentState.hasOwnProperty("_csUseEnvironmentKeyCacheV1")==hadEnvironmentSwitch &&
                        (!hadEnvironmentSwitch || environmentState._csUseEnvironmentKeyCacheV1===savedEnvironmentSwitch),"Environment selector was not restored");
                }
                cleanup.environmentSwitchRestored=true;
            } catch(eSwitch:Error) {cleanup.errors.push("environment selector: "+eSwitch.message);}
            if(saved!=null && saved.ready)''')
    s=one(s,'                var a:BitmapData=capture(),b:BitmapData=capture();','''                environmentState._csUseEnvironmentKeyCacheV1=false;
                grafon.sceneNativeEnvironment(location,player.X,player.Y);
                var a:BitmapData=capture(),b:BitmapData=capture();
                environmentState._csUseEnvironmentKeyCacheV1=true;
                grafon.sceneNativeEnvironment(location,player.X,player.Y);
                var cached:BitmapData=capture();
                environmentState._csUseEnvironmentKeyCacheV1=false;
                grafon.sceneNativeEnvironment(location,player.X,player.Y);
                var restored:BitmapData=capture();
                result.cachedCompare=compare(a,cached);result.restoredCompare=compare(a,restored);
                require(result.cachedCompare.equal && result.restoredCompare.equal,"Key branch changed pixel output");''')
    assert s.count('cam.calc(player)')==1
    return s

def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=one(s,"HERE/'lineage.py', RC_RECEIPT,","HERE/'lineage.py',HERE/'prepare_host.py',HERE/'audit.py',HERE/'build.py',HERE/'source-equivalent.as.inc', RC_RECEIPT,")
    s=one(s,"parser.add_argument('--mode',required=True,choices=['normal','scene'])","parser.add_argument('--mode',required=True,choices=['scene'])")
    s=one(s,'            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)', '''            host_build=r.read(HERE/'build.json');host_audit=r.read(HERE/'audit-proof.json')
            assert host_build['base']==baseline['pfe.swf'] and host_build['diagnosticOnly'] and host_audit['diagnosticOnly']
            assert host_build['audit']==r.sha(HERE/'audit-proof.json') and host_audit['passed']
            assert host_audit['changed']==['fe.graph.Grafon::0:1:sceneNativeEnvironment'] and host_audit['unchangedBodies']==5770
            assert host_audit['unchangedClasses']==1016 and host_build['deployed'] is False and host_audit['deployed'] is False
            assert host_build['candidate']==host_audit['candidateSHA256']==r.sha(HERE/'pfe.swf')
            host_inputs={str(HERE/p):r.sha(HERE/p) for p in ['build.json','audit-proof.json','pfe.swf']}
            expected=dict(baseline);expected['pfe.swf']=host_build['candidate']
            record.update(baseline=baseline,expectedRuntime=expected,hostInputs=host_inputs,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,runtimeInputs=runtime,memoryBefore=memory)''')
    s=one(s,"            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)",
        "            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)\n            shutil.copy2(HERE/'pfe.swf',m.RUNTIME/'pfe.swf')")
    assert s.count('for key,digest in baseline.items():')==2
    s=s.replace('for key,digest in baseline.items():','for key,digest in expected.items():')
    s=one(s,'            verify_probe(path,baseline,scripts,compiler,fixture)\n            if not',
        '            verify_probe(path,baseline,scripts,compiler,fixture)\n            assert host_inputs=={p:r.sha(Path(p)) for p in host_inputs}\n            if not')
    s=one(s,"lease.note='960 native camera axis intervals, active quiet world; no deployment'",
        "lease.note='1920 same-instance native/cached intervals, selector restored; diagnostic host not deployed'")
    s=one(s,"    parser.add_argument('--wait-ready-seconds',type=int,default=0)",
        "    parser.add_argument('--wait-ready-seconds',type=int,default=0)\n    parser.add_argument('--host-root',type=Path,default=HERE)")
    s=one(s,'    args=parser.parse_args()', '''    args=parser.parse_args()
    host_root=args.host_root.resolve()
    assert host_root in [HERE, HERE.parent/'camera-environment-paired-binary-20261028'], 'Unreviewed host producer' ''')
    for name in ['build.json','audit-proof.json','pfe.swf']:
        s=s.replace("HERE/'"+name+"'", "host_root/'"+name+"'")
    s=one(s,"host_inputs={str(HERE/p):r.sha(HERE/p) for p in ['build.json','audit-proof.json','pfe.swf']}",
        "host_inputs={str(host_root/p):r.sha(host_root/p) for p in ['build.json','audit-proof.json','pfe.swf']}\n            host_inputs.update(host_build['sourceInputs'])\n            assert host_inputs=={p:r.sha(Path(p)) for p in host_inputs}")
    s=one(s,'record.update(baseline=baseline,expectedRuntime=expected,hostInputs=host_inputs,',
        'record.update(baseline=baseline,expectedRuntime=expected,hostRoot=str(host_root),hostProducer=host_build[\'version\'],hostInputs=host_inputs,')
    s=one(s,"PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT", '''PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT
DEPLOY_RECEIPT=HERE.parents[2]/'state/alicorn-alert-deployment-20261028.json'
PINS['pfe.swf']='4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
PINS['mods/ContinuousScene/release/ContinuousSceneMod.swf']='9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31' ''')
    s=one(s,'def runner_inputs():', '''def runner_inputs():
    assert r.sha(DEPLOY_RECEIPT)=='2B2CBB6A7D79DC8CBB8FF52FD94CA3B9B7E5445B7BEFF251703B1056B5AB6BB3'
    deployed=r.read(DEPLOY_RECEIPT)
    assert deployed['installedReadbackPassed'] and deployed['verification']['ok']
    assert deployed['host']==PINS['pfe.swf'] and deployed['mod']==PINS['mods/ContinuousScene/release/ContinuousSceneMod.swf']''')
    s=one(s,"HERE/'source-equivalent.as.inc', RC_RECEIPT,", "HERE/'source-equivalent.as.inc', RC_RECEIPT, DEPLOY_RECEIPT,")
    s=one(s,'m.HiddenProcess=recorded_hidden_process', '''SILENCE_SOURCE=HERE.parent/'camera-live-current-silent-20261028/silence.py'
silence=load('paired_native_audio_settings',SILENCE_SOURCE)
NATIVE_SILENCE=[]''')
    s=one(s,'def recorded_hidden_process(*args,**kwargs):\n    process=original_hidden_process(*args,**kwargs)', '''def recorded_hidden_process(lease,*args,**kwargs):
    try:
        assert len(args)==1 and len(args[0])==4
        NATIVE_SILENCE.append(silence.seed(args[0][-1],m.RUNTIME))
        control.memory_gate()
    except BaseException:
        # before_launch ran, but the constructor below has not been called.
        # Constructor failures retain the registry's conservative uncertainty.
        lease.child_stopped()
        raise
    process=original_hidden_process(*args,**kwargs)''')
    s=one(s,'RC_RECEIPT, DEPLOY_RECEIPT,','RC_RECEIPT, DEPLOY_RECEIPT, SILENCE_SOURCE,')
    s=one(s,"            run_error=None\n            try:m.run_owned(m.parse_args(record['options']),lease)", '''            run_error=None
            previous_hidden_process=m.HiddenProcess
            def game_hidden_process(*args,**kwargs):
                return recorded_hidden_process(lease,*args,**kwargs)
            m.HiddenProcess=game_hidden_process
            try:m.run_owned(m.parse_args(record['options']),lease)''')
    s=one(s,"            finally:\n                record['startupResourcePolicies']=STARTUP_POLICIES", "            finally:\n                m.HiddenProcess=previous_hidden_process\n                record['startupResourcePolicies']=STARTUP_POLICIES")
    s=one(s,"record['startupResourcePolicies']=STARTUP_POLICIES", "record['startupResourcePolicies']=STARTUP_POLICIES\n                record['nativeSilence']=NATIVE_SILENCE")
    s=one(s,"record['nativeSilence']=NATIVE_SILENCE", "record['nativeSilence']=NATIVE_SILENCE\n                record['nativeSilenceSource']=dict(path=str(SILENCE_SOURCE),sha256=scripts[str(SILENCE_SOURCE)])")
    return s

def prepare():
    load('paired_host_generator',HERE/'prepare_host.py').prepare()
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source()),('lineage.py',(BASE/'lineage.py').read_text('utf-8-sig'))]:
        path=HERE/name
        if path.suffix=='.py':ast.parse(s)
        if path.exists():assert path.read_text('utf-8-sig')==s,name
        else:path.write_text(s,'utf-8')

if __name__=='__main__':
    prepare();print('Prepared same-instance native/cached recipe; no compiler or game launched')
