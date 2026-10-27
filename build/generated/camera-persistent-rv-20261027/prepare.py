from pathlib import Path
import ast,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-repeated-20261027'
VERSION='camera-persistent-rv-1';MOD=HERE.parents[2]
RVSOURCE=MOD.parent/'RealisticVision/build/combat-render-output/production-final2'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_rv_generation',BASE/'prepare.py');one=base.one
readers=load('persistent_rv_reader_generation',HERE.parent/'camera-persistent-readers-20261027/prepare.py')
def presenter_source():
    s=readers.persistent_source().replace('class ScenePersistentAtlas','class SceneRasterPresentation')
    assert s.replace(readers.PROVIDER,'')==base.presenter_source()
    return s
def helper_source():return base.helper_source()
def rv_sources():
    receipt=json.loads((RVSOURCE/'build.json').read_text('utf-8-sig'));result={}
    for name,digest in receipt['sources'].items():
        data=(RVSOURCE/'src'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        result[name]=data.decode('utf-8-sig').replace('\r\n','\n')
    s=result['RVWallSurface.as'];clone=readers.rv_source(True)
    clone=clone.replace('SceneNativeRVWallSurface','RVWallSurface')
    clone=one(clone,'      public function diagnosticSources(front:DisplayObjectContainer):Array {left=0;top=0;return foregroundSources(front);}\n','')
    clone=one(clone,'      public var nativeTerrainSources:Function;','      public var nativeTerrainSources:Function;\n      public var nativeReadCalls:int=0,nativeReadProvided:int=0;')
    clone=one(clone,'         var nodes:Array=nativeTerrainSources==null?null:nativeTerrainSources(front);',
        '         ++nativeReadCalls;\n         var nodes:Array=nativeTerrainSources==null?null:nativeTerrainSources(front);\n         if(nodes!=null)++nativeReadProvided;')
    result['RVWallSurface.as']=clone
    s=result['RealisticVisionMod.as']
    s=one(s,'"v0.33.10-render-cache"','"v0.33.10-cs-native-reader-test"')
    s=one(s,'         carrier["api"] = {version:1,','''         carrier["api"] = {version:1,
            terrainReadStats:function():Object {return {calls:self.wallSurface.nativeReadCalls,provided:self.wallSurface.nativeReadProvided,active:self.explorationActive(World.w.loc),mode:self.cfgMode,enabled:self.cfgEnabled,errorCount:self.errCount};},''')
    s=one(s,'         this.wallSurface.update(this.fogShadow,this.fogBase,w.grafon,loc,view,','''         var sceneCarrier:*=w.main.getChildByName("ContinuousSceneCarrier");
         var sceneNative:*=sceneCarrier!=null?sceneCarrier["nativeAPI"]:null;
         this.wallSurface.nativeTerrainSources=sceneNative!=null && "terrainSources" in sceneNative?sceneNative["terrainSources"] as Function:null;
         this.wallSurface.update(this.fogShadow,this.fogBase,w.grafon,loc,view,''')
    result['RealisticVisionMod.as']=s
    return result
def transform(source):
    s=base.transform(source).replace(base.VERSION,VERSION)
    s=one(s,'        private static var atlasPriorEnabled:Boolean=false,atlasPriorPresented:Boolean=false;','        private static var rvProviderInstalled:Boolean=false;\n        private static var atlasPriorEnabled:Boolean=false,atlasPriorPresented:Boolean=false;')
    s=one(s,'setting("realisticvision","enabled",Boolean(cfg.vision));','setting("realisticvision","enabled",Boolean(cfg.vision));setting("realisticvision","mode",2);')
    s=one(s,'                        rasterPresentation.preallocate(w);','''                        rasterPresentation.preallocate(w);
                        var nativeTerrainAPI:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
                        if("terrainSources" in nativeTerrainAPI)throw new Error("Unexpected existing terrain provider");
                        nativeTerrainAPI["terrainSources"]=rasterPresentation.nativeTerrainSources;rvProviderInstalled=true;
                        report.rvReaderBefore=main.getChildByName("RVExplorationAPI")["api"].terrainReadStats();
                        check("rv-current-active",report.rvReaderBefore.active && report.rvReaderBefore.mode=="current" && report.rvReaderBefore.errorCount==0,report.rvReaderBefore);''')
    s=one(s,'                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);','''                report.rvReaderAfter=main.getChildByName("RVExplorationAPI")["api"].terrainReadStats();
                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);''')
    s=one(s,'            if(cfg.drawControl=="atlas") {\n                report.atlasMotionCleanup=',
        '''            if(rvProviderInstalled) {
                delete main.getChildByName("ContinuousSceneCarrier")["nativeAPI"]["terrainSources"];
                rvProviderInstalled=false;report.rvProviderRemoved=true;
            }
            if(cfg.drawControl=="atlas") {
                report.atlasMotionCleanup=''')
    return s
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=one(s,"patch = load('camera_world_patch', HERE/'probe_patch.py')","patch = load('camera_world_patch', HERE/'probe_patch.py')\nrv_build = load('persistent_rv_candidate_builder', HERE/'rv_build.py')")
    s=one(s,"values=reference.options(name)+['--draw-control','atlas']","values=reference.options(name)+['--draw-control','atlas','--vision']")
    s=one(s,"            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)",
        "            rv=rv_build.build(lease,control,r,base)\n            record['rvBuild']=rv\n            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)")
    s=one(s,"            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())",
        "            shutil.copy2(rv['output'],m.RUNTIME/'mods/RealisticVision/release/RealisticVisionMod.swf')\n            assert r.sha(m.RUNTIME/'mods/RealisticVision/release/RealisticVisionMod.swf')==rv['sha256']\n            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())")
    s=one(s,"if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key",
        "if key not in ('application.xml','mods/loader-manifest.txt','mods/RealisticVision/release/RealisticVisionMod.swf'):assert actual[key]==digest,key")
    s=one(s,"            policy=r.read(folder/'process-policy.json')",
        "            assert actual['mods/RealisticVision/release/RealisticVisionMod.swf']==rv['sha256']\n            rv_build.verify(rv,r,base)\n            policy=r.read(folder/'process-policy.json')")
    s=one(s,"summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True)",
        "summary.update(resultSHA256=r.sha(folder/'storage/result.json'),probeSHA256=probe['probeSHA256'],inputsUnchanged=True,runtimeInputsUnchanged=True,rvCandidateSHA256=rv['sha256'])")
    s=one(s,"2880 persistent atlas camera intervals, active quiet world; no deployment","1200 complete native combat intervals with candidate RV reader; no deployment")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    entries=[('SceneRasterPresentation.as',presenter_source()),('tests/SceneCombatAtlasPixels.as',helper_source()),('run.py',runner_source())]
    entries += [('rv-src/'+name,source) for name,source in rv_sources().items()]
    for name,s in entries:
        p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared isolated D44 RV reader integration; formal RV files untouched')
