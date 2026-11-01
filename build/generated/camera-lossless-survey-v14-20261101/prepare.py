"""Make an isolated snapshot-reuse trial from the exact deployed TDFC source line.

No current TDFC worktree source or release is overwritten.  The public snapshot
API remains fresh; only runtime-owned, two-frame-old enemy samples are reused.
"""
from pathlib import Path
import hashlib, json, shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'tdfc-threat'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(OLD/'TDFCMod.swf')=='7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5'
src=HERE/'candidate-src'
src.mkdir(exist_ok=True)
for p in OLD.rglob('*.as'):
    out=src/p.relative_to(OLD);out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
bridge=(src/'GameBridge.as').read_text('utf-8-sig')
start=bridge.index('  public static function snapshot(')
end=bridge.index('  public static function hostile(',start)
method=bridge[start:end]
begin=method.index('return {')+len('return {')
literal=method[begin:method.index('};',begin)]
# Split only top-level property commas, retaining original expression/read order.
parts=[];depth=0;quote=None;at=0
for i,c in enumerate(literal):
    if quote:
        if c==quote and literal[i-1]!='\\':quote=None
    elif c in ('"',"'"):quote=c
    elif c in '([{':depth+=1
    elif c in ')]}':depth-=1
    elif c==',' and depth==0:parts.append(literal[at:i]);at=i+1
parts.append(literal[at:])
assignments=[];keys=[]
for part in parts:
    key,expression=part.strip().split(':',1);keys.append(key)
    if key=='cls':expression='sceneClass(u)'
    assignments.append('   out.'+key+'='+expression+';')
assert len(keys)==len(set(keys))==45
prefix=method[method.index('   var w:'):method.index('   return {')]
extra='  public static function snapshotInto(u:*,out:Object):Object {\n'+prefix+'\n'.join(assignments)+'\n   return out;\n  }\n'
bridge=bridge[:end]+extra+bridge[end:]
(src/'GameBridge.as').write_text(bridge,'utf-8')
runtime=(src/'TdfcRuntime.as').read_text('utf-8-sig')
runtime=runtime.replace('  private static var cost:Number=0;', '''  private static var cost:Number=0;
  public static var scenePoolEnabled:Boolean=false;
  public static var sceneValidate:Boolean=false;
  public static var sceneChecks:int=0,sceneFailures:int=0;
  private static var sceneCalls:int=0,sceneReuses:int=0;
  public static function sceneStats():Object {return {tick:tick,cost:cost,active:all.length,calls:sceneCalls,reuses:sceneReuses,checks:sceneChecks,failures:sceneFailures,status:status};}
  private static function sceneSnapshot(u:*,b:BrainState):Object {
   ++sceneCalls;
   var recycled:Object=scenePoolEnabled && b?b.previous:null;
   if(recycled==null)return GameBridge.snapshot(u);
   ++sceneReuses;
   var reference:Object=sceneValidate?GameBridge.snapshot(u):null;
   var out:Object=GameBridge.snapshotInto(u,recycled);
   if(reference)for(var key:String in reference) {
    ++sceneChecks;var a:*=reference[key],v:*=out[key];
    if(a!==v && !(a is Number && v is Number && isNaN(a) && isNaN(v)))++sceneFailures;
   }
   return out;
  }''')
runtime=runtime.replace('sceneTest.api=GameBridge;', 'sceneTest.api=GameBridge;sceneTest.runtime=TdfcRuntime;')
runtime=runtime.replace('status="运行";var start:int=getTimer();tick++;','status="运行";var start:int=getTimer();tick++;sceneCalls=0;sceneReuses=0;')
old='if(u===gg)continue;var s:Object=GameBridge.snapshot(u);if(!GameBridge.hostile(s,g))continue;\n      var b:BrainState=states[u];'
new='if(u===gg)continue;var b:BrainState=states[u];var s:Object=sceneSnapshot(u,b);if(!GameBridge.hostile(s,g))continue;\n      '
assert runtime.count(old)==1
runtime=runtime.replace(old,new)
(src/'TdfcRuntime.as').write_text(runtime,'utf-8')

previous=HERE.parent/'camera-screen-cache-v13-20261101'
probe=(previous/'ContinuousSceneMotionMod.as').read_text('utf-8-sig')
probe=probe.replace('private static var fill:ScreenTerrainCache=new ScreenTerrainCache(7);','private static var tdfc:*,tdfcBridge:*;')
probe=probe.replace('camera-screen-cache-13','camera-lossless-survey-14')
probe=probe.replace('main.stage.frameRate=120;phase=10;', '''var tcarrier:*=main.getChildByName("ContinuousSceneTdfcThreat");
            assertThat("tdfc-candidate-interface",tcarrier && tcarrier.runtime);
            tdfc=tcarrier.runtime;tdfcBridge=tcarrier.api;tdfc.scenePoolEnabled=true;tdfc.sceneValidate=true;
            snapshotChecks();
            main.stage.frameRate=120;phase=10;''')
a=probe.index('        private static function makeSchedule()')
b=probe.index('        private static function enterBlock()',a)
probe=probe[:a]+'''        private static function makeSchedule():void {
            assertThat("runtime-snapshot-equivalence",tdfc.sceneChecks>0 && tdfc.sceneFailures==0,tdfc.sceneStats());
            tdfc.sceneValidate=false;
            for each(var axis:String in ["static","x","y"])
                for each(var draw:String in ["base","pool","pool","base"])
                    schedule.push({fps:options.fps || 120,axis:axis,mode:draw,frames:300});
            report.schedule=schedule;index=0;enterBlock();
        }
'''+probe[b:]
probe=probe.replace('age=0;previousAt=0;rows=[];phase=20;', 'age=0;previousAt=0;rows=[];phase=20;tdfc.scenePoolEnabled=(mode=="pool");')
a=probe.index('        private static function drawPolicy()')
b=probe.index('        private static function after(',a)
probe=probe[:a]+probe[b:]
probe=probe.replace('                    drawPolicy();','                    var ts:Object=tdfc.sceneStats();')
probe=probe.replace('getTimer()-now,System.totalMemory]);','getTimer()-now,System.totalMemory,ts.cost,ts.active,ts.calls,ts.reuses]);')
probe=probe.replace('mark.rows=rows;mark.fill=fill.stats();','mark.rows=rows;mark.tdfc=tdfc.sceneStats();')
a=probe.index('                        if(mode=="fill")')
b=probe.index('                        mark.actualFrameRate',a)
probe=probe[:a]+probe[b:]
a=probe.index('        private static function captureWorld()')
b=probe.index('        private static function finish(',a)
probe=probe[:a]+'''        private static function snapshotChecks():void {
            var calls:int=0,fields:int=0;
            var values:Array=loc.units.concat([null,{}, {X:NaN,Y:25,scX:70,storona:-1,currentWeapon:{tip:3,hold:0,rot:NaN}}, {X:-200,Y:-3,fraction:100,sost:1,npc:true}]);
            for each(var u:* in values) {
                var a:Object=tdfcBridge.snapshot(u),b:Object=tdfcBridge.snapshotInto(u,{});
                for(var k:String in a) {
                    var av:*=a[k],bv:*=b[k];
                    if(av!==bv && !(av is Number && bv is Number && isNaN(av) && isNaN(bv)))throw new Error("snapshot mismatch "+k);
                    ++fields;
                }
                if(tdfcBridge.snapshot(u)===a)throw new Error("public snapshot must remain fresh");
                ++calls;
            }
            report.snapshotChecks={units:calls,fields:fields};
            assertThat("snapshot-field-equivalence",calls>50 && fields>2000,report.snapshotChecks);
        }
'''+probe[b:]
probe=probe.replace('            fill.clear();','            if(tdfc)tdfc.scenePoolEnabled=false;')
probe=probe.replace('"memoryBytes"];','"memoryBytes","tdfcCostMs","tdfcActive","tdfcCalls","tdfcReuses"];')
(HERE/'ContinuousSceneMotionMod.as').write_text(probe,'utf-8')
shutil.copy2(previous/'CameraProbePlatform.as',HERE/'CameraProbePlatform.as')
work=(previous/'work.py').read_text('utf-8-sig')
work=work.replace("motion.prepare()", "motion.prepare()\n        shutil.copy2(HERE/'TDFCMod.swf',runtime/'mods/TDFC/release/TDFCMod.swf')")
work=work.replace("'nativePresentation':args.native_presentation", "'nativePresentation':args.native_presentation,'fps':args.fps")
work=work.replace("p.add_argument('--small',action='store_true');", "p.add_argument('--small',action='store_true');p.add_argument('--fps',type=int,default=120);")
work=work.replace("'probe':sha(HERE/'ContinuousSceneMotionMod.swf'),'command':command", "'probe':sha(HERE/'ContinuousSceneMotionMod.swf'),'tdfc':sha(HERE/'TDFCMod.swf'),'command':command")
work=work.replace("assert receipt['probe']==sha(HERE/'ContinuousSceneMotionMod.swf')", "assert receipt['probe']==sha(HERE/'ContinuousSceneMotionMod.swf')\n    assert receipt['tdfc']==sha(HERE/'TDFCMod.swf')")
work=work.replace('object viewport optimization','lossless snapshot survey')
(HERE/'work.py').write_text(work,'utf-8')
(HERE/'source-origin.json').write_text(json.dumps({'formalTDFC':sha(OLD/'TDFCMod.swf'),'baseSources':{str(p.relative_to(OLD)):sha(p) for p in OLD.rglob('*.as')},'candidateSources':{str(p.relative_to(src)):sha(p) for p in src.rglob('*.as')},'fields':keys},indent=2),'utf-8')
print(json.dumps({'prepared':True,'fields':len(keys),'sourceFiles':len(list(src.rglob('*.as')))}))
