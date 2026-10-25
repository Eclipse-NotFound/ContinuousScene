"""Prepare only the two-class 7ACD activity-lease source candidate. No compiler/game."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'scene-compat-20261024' / 'tdfc-los'
PINS_SHA = '644576F031ED41AD50BC200718E2CD77668F8552F1878678BDC7EC848A85D0FB'
PROOF_SHA = '5BDA28CAFA0D5378298916A173B0CA0333C26AEFFB83B23011BE8BE9F6385E77'
BASE_SHA = '7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5'
CHANGED = ('TdfcRuntime.as', 'PerceptionModel.as')

RUNTIME_HELPERS = '''  // Lease support is explicit. Old CS keeps its original permanent wake path.
  private static function sceneLeaseAvailable(g:*):Boolean {
   try { return g.sceneNativeCall("activityLeaseVersion",[]) === "activity-lease-1"; }
   catch(e:Error) {} return false;
  }
  private static function sceneLeaseClass(u:*):Boolean {
   try {
    var name:String=getQualifiedClassName(u);
    return name=="fe.unit::UnitRaider" || name=="fe.unit::UnitMerc" || name=="fe.unit::UnitSlaver";
   } catch(e:Error) {} return false;
  }
  private static function sceneNeedsActivity(b:BrainState,t:int):Boolean {
   try {
    if(!b || !b.profile || b.profile.supported!==true) return true;
    var memory:Number=Number(b.profile.memory);
    if(!isFinite(memory) || memory<=0) return true;
    if(t-b.lastSeen<memory || perception.needsActivity(b,t)) return true;
    if(!b.action) return true;
    if(b.action.kind=="dodge" && t<b.until) return true;
    // Let ordinary decide/apply finish any previous non-idle commitment.
    if(b.action.kind!=="idle") return true;
    if(b.order && (b.order.kind!=="idle" || b.order.move!==false)) return true;
    if(b.groundCommitted || b.cover!=null || b.observed || b.confirmed || b.heard) return true;
    return false;
   } catch(e:Error) {} return true;
  }
  private static function sceneHold(g:*,u:*):void {
   try { if(g.sceneNativeCall("activityLease",[u,45])===true) return; }
   catch(e:Error) {}
   // Missing record/API/failure must keep the already-supported legacy wake.
   g.sceneNativeCall("wake",[u]);
  }
'''

OLD_SLEEP = '''     for each(var u:* in units) {
      if(sceneSleep && sceneSleep[u]) {
       var remembered:BrainState=states[u];
       if(remembered && remembered.lastSeen>=0)sceneGrafon.sceneNativeCall("wake",[u]);
       else continue;
      }
'''
NEW_SLEEP = '''     var sceneLeases:Boolean=sceneSleep!=null && sceneLeaseAvailable(sceneGrafon);
     var retained:Dictionary=new Dictionary(true),retainedBrains:Array=[],pausedFresh:Array=[];
     for each(var u:* in units) {
      var remembered:BrainState=states[u];
      if(sceneSleep && sceneSleep[u]) {
       if(sceneLeases && remembered && sceneLeaseClass(u)) {
        if(sceneNeedsActivity(remembered,tick)) sceneHold(sceneGrafon,u);
        else {
         var dormantSample:Object=GameBridge.snapshot(u);
         if(!GameBridge.hostile(dormantSample,g)) continue;
         if(!remembered.sample || dormantSample.hp<remembered.sample.hp || dormantSample.target!=null) sceneHold(sceneGrafon,u);
         else {
          if(!pausedUnits[u]) ActionExecutor.restore(remembered);
          // Keep identity, memory and absolute cooldown ticks. Only refresh the
          // physical sample used by report recipients and squad spacing.
          remembered.previous=remembered.sample;remembered.sample=dormantSample;
          pausedFresh.push(remembered);retained[u]=true;retainedBrains.push(remembered);
          continue;
         }
        }
       } else {
        if(remembered && remembered.lastSeen>=0)sceneGrafon.sceneNativeCall("wake",[u]);
        else continue;
       }
      }
'''
OLD_PRUNE = '''     for each(var old:BrainState in all)if(!present[old.unit]){ActionExecutor.restore(old);delete states[old.unit];}
     all=fresh;perception.deliver(all,tick);perception.schedule(all,tick);squads.frame(all,tick);
'''
NEW_PRUNE = '''     // Present means actively updated; retained also includes paused brains.
     for each(var old:BrainState in all)if(!retained[old.unit]){ActionExecutor.restore(old);delete states[old.unit];}
     for each(var oldPaused:BrainState in pausedBrains)if(!retained[oldPaused.unit]){ActionExecutor.restore(oldPaused);delete states[oldPaused.unit];}
     all=fresh;pausedBrains=pausedFresh;pausedUnits=new Dictionary(true);
     for each(var pausedBrain:BrainState in pausedBrains)pausedUnits[pausedBrain.unit]=true;
     var participants:Array=sceneLeases?retainedBrains:all;
     perception.deliver(participants,tick);perception.schedule(all,tick,sceneLeases?participants:null);squads.frame(participants,tick);
'''
PERCEPTION_HELPER = '''  // Pure query. A due-but-undelivered report protects BOTH endpoint identities.
  // Do not consume, reorder or advance pending messages here.
  public function needsActivity(b:BrainState,t:int):Boolean {
   if(!b) return true;
   try {
    for each(var p:Object in pending) {
     if(!p) return true;
     if(p.to!==b && p.source!==b) continue;
     var recipient:BrainState=p.to as BrainState,source:BrainState=p.source as BrainState;
     if(!recipient || !source || !recipient.sample || !source.sample || !recipient.profile) return true;
     var at:Number=Number(p.at),seen:Number=Number(p.seen),memory:Number=Number(recipient.profile.memory);
     if(!isFinite(at) || !isFinite(seen) || !isFinite(memory) || memory<=0) return true;
     if(recipient.sample.fraction!=p.fraction || source.sample.fraction!=p.fraction) continue;
     if(recipient.lastSeen>=seen || t-seen>memory) continue;
     return true;
    }
    return false;
   } catch(e:Error) {} return true;
  }
'''

EDITS = {
    'TdfcRuntime.as': [
        (' import flash.utils.getTimer;\n', ' import flash.utils.getTimer;\n import flash.utils.getQualifiedClassName;\n'),
        ('  private static var all:Array=[];\n', '  private static var all:Array=[];\n  private static var pausedBrains:Array=[];\n  private static var pausedUnits:Dictionary=new Dictionary(true);\n'),
        ('   states=new Dictionary(true);all=[];room=loc;perception.reset();squads.reset();TdfcLog.line("room","reset");\n',
         '   for each(var pausedBrain:BrainState in pausedBrains)ActionExecutor.restore(pausedBrain);\n   states=new Dictionary(true);all=[];pausedBrains=[];pausedUnits=new Dictionary(true);room=loc;perception.reset();squads.reset();TdfcLog.line("room","reset");\n'),
        ('  private static function onFrame(e:Event):void {\n', RUNTIME_HELPERS+'  private static function onFrame(e:Event):void {\n'),
        (OLD_SLEEP, NEW_SLEEP),
        ('      b.previous=b.sample;b.sample=s;fresh.push(b);present[u]=true;ActionExecutor.assess(b,tick);\n',
         '      b.previous=b.sample;b.sample=s;fresh.push(b);present[u]=true;retained[u]=true;retainedBrains.push(b);ActionExecutor.assess(b,tick);\n'),
        (OLD_PRUNE, NEW_PRUNE),
        ('      var context:Object=squads.context(b,all,tick);\n', '      var context:Object=squads.context(b,participants,tick);\n'),
        ('      ActionExecutor.apply(b,b.confirmed?g:target,loc,tick);\n',
         '      ActionExecutor.apply(b,b.confirmed?g:target,loc,tick);\n      if(sceneLeases && sceneLeaseClass(b.unit) && sceneNeedsActivity(b,tick))sceneHold(sceneGrafon,b.unit);\n'),
    ],
    'PerceptionModel.as': [
        ('  public function schedule(all:Array,t:int):void {\n', PERCEPTION_HELPER+'  public function schedule(all:Array,t:int,recipients:Array=null):void {\n'),
        ('    for each(var r:BrainState in all) {\n', '    for each(var r:BrainState in (recipients==null?all:recipients)) {\n'),
    ],
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def normalized(data: bytes) -> str:
    return data.decode('utf-8').replace('\r\n', '\n')

def transform(name: str, text: str, reverse: bool = False) -> str:
    edits = EDITS[name]
    for old, new in reversed(edits) if reverse else edits:
        source, target = (new, old) if reverse else (old, new)
        if text.count(source) != 1:
            raise AssertionError(f'{name}: exact anchor count {text.count(source)} != 1')
        text = text.replace(source, target, 1)
    return text

def inputs() -> tuple[dict, dict[str, bytes]]:
    pins_file, proof_file = FROZEN/'source-pins.json', FROZEN/'source-proof.json'
    assert sha(pins_file.read_bytes()) == PINS_SHA
    assert sha(proof_file.read_bytes()) == PROOF_SHA
    pins = json.loads(pins_file.read_text(encoding='utf-8'))
    assert pins['baseSWFSHA256'] == BASE_SHA and len(pins['sources']) == 22
    files = {p.relative_to(FROZEN/'original').as_posix(): p.read_bytes()
             for p in (FROZEN/'original').rglob('*.as')}
    assert set(files) == set(pins['sources'])
    for name, data in files.items():
        assert sha(data) == pins['sources'][name], name
    return pins, files

def prepare() -> dict:
    pins, original = inputs()
    out = HERE/'tdfc-candidate'
    out.mkdir(exist_ok=True)
    produced, patch_lines, negatives = {}, [], []
    for name, data in original.items():
        if name in CHANGED:
            before = normalized(data)
            after = transform(name, before)
            assert transform(name, after, True) == before
            # Match the exact input newline style, then demand byte identity.
            newline = '\r\n' if b'\r\n' in data else '\n'
            rebuilt = transform(name, after, True).replace('\n', newline).encode('utf-8')
            assert rebuilt == data
            result = after.replace('\n', newline).encode('utf-8')
            for index, (anchor, replacement) in enumerate(EDITS[name]):
                broken = before.replace(anchor, anchor+'/* changed anchor */', 1)
                # A surrounding extra comment is not necessarily an invalid
                # anchor; remove one exact character INSIDE the anchor instead.
                broken = before.replace(anchor, anchor[:-1], 1)
                try:
                    transform(name, broken)
                except AssertionError:
                    negatives.append({'file':name, 'anchor':index, 'rejected':True})
                else:
                    raise AssertionError(f'negative accepted: {name}/{index}')
            patch_lines.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                   fromfile='original/'+name, tofile='candidate/'+name))
        else:
            result = data
        destination = out/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != result:
            raise AssertionError(f'existing candidate differs: {destination}')
        destination.write_bytes(result)
        produced[name] = sha(result)
    assert sorted(n for n in produced if produced[n] != pins['sources'][n]) == sorted(CHANGED)
    assert set(p.relative_to(out).as_posix() for p in out.rglob('*.as')) == set(original)
    receipt = {
        'version':'activity-release-tdfc-source-1', 'baseSHA256':BASE_SHA,
        'sourcePinsSHA256':PINS_SHA, 'sourceProofSHA256':PROOF_SHA,
        'transformSHA256':sha(Path(__file__).read_bytes()), 'changed':list(CHANGED),
        'sourceCount':22, 'unchangedSources':20, 'original':pins['sources'], 'candidate':produced,
        'reverseExact':True, 'negativeChecks':negatives,
        'leaseAPI':{'versionMethod':'activityLeaseVersion', 'version':'activity-lease-1',
                    'method':'activityLease', 'args':['unit',45], 'success':'strict true',
                    'clock':'CS Location ticks; independent leaseUntil', 'legacyFallback':'wake'},
        'compiled':False, 'runtimeVerified':False, 'performanceEligible':False, 'deployed':False,
    }
    (HERE/'tdfc-candidate.patch').write_text(''.join(patch_lines), encoding='utf-8', newline='\n')
    (HERE/'tdfc-source-proof.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return receipt

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare', action='store_true', required=True)
    ap.parse_args()
    r = prepare()
    print(json.dumps({k:r[k] for k in ('version','sourceCount','unchangedSources','changed','reverseExact','compiled','runtimeVerified')}, ensure_ascii=False))
