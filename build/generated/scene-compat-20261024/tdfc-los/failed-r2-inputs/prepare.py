"""Source-only LOS candidate. Never compiles, launches, or installs anything."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2]
MOD = BUILD.parent
ROOT = MOD.parents[1]
ORIGIN = BUILD / 'generated/tdfc-threat'
VERSION = 'tdfc-los-empty-cell-1'

OLD_CLEAR = '''  public static function clear(loc:*,x:Number,y:Number,tx:Number,ty:Number):Boolean {
   var n:int=Math.ceil(Math.max(Math.abs(tx-x),Math.abs(ty-y))/9);
   for(var i:int=1;i<n;i++) if(solid(loc,x+(tx-x)*i/n,y+(ty-y)*i/n)) return false;
   return true;
  }
'''

NEW_CLEAR = '''  // Isolated diagnostic only; the frozen production path remains the default.
  public static const sceneLosEmptyCacheVersion:String="tdfc-los-empty-cell-1";
  public static var sceneLosEmptyCacheEnabled:Boolean=false;
  public static var sceneLosEmptyCacheCalls:uint=0;
  public static var sceneLosEmptyCacheFallbackCalls:uint=0;
  public static var sceneLosEmptyCacheHits:uint=0;
  public static var sceneLosEmptyCacheLookups:uint=0;
  private static var sceneLosLocationClass:Class;
  private static var sceneLosTileClass:Class;
  private static function sceneLosNative(loc:*):Boolean {
   var accepted:Boolean=false;
   try {
    if(getQualifiedClassName(loc)=="fe.loc::Location") {
     if(sceneLosLocationClass==null)sceneLosLocationClass=ApplicationDomain.currentDomain.getDefinition("fe.loc.Location") as Class;
     if(sceneLosTileClass==null)sceneLosTileClass=ApplicationDomain.currentDomain.getDefinition("fe.loc.Tile") as Class;
     accepted=sceneLosLocationClass!=null && loc.constructor===sceneLosLocationClass && sceneLosTileClass!=null && sceneLosTileClass["tileX"]===40 && sceneLosTileClass["tileY"]===40;
    }
   } catch(e:Error) { accepted=false; }
   return accepted;
  }
  public static function clear(loc:*,x:Number,y:Number,tx:Number,ty:Number):Boolean {
   var n:int=Math.ceil(Math.max(Math.abs(tx-x),Math.abs(ty-y))/9);
   var eligible:Boolean=false,maxX:Number=0,maxY:Number=0;
   if(sceneLosEmptyCacheEnabled && sceneLosNative(loc)) {
    maxX=Number(loc.spaceX)*40;maxY=Number(loc.spaceY)*40;
    eligible=isFinite(x) && isFinite(y) && isFinite(tx) && isFinite(ty) && isFinite(maxX) && isFinite(maxY)
     && maxX>0 && maxY>0 && maxX<=2147483647 && maxY<=2147483647
     && x>=0 && y>=0 && tx>=0 && ty>=0 && x<maxX && tx<maxX && y<maxY && ty<maxY;
   }
   if(!eligible) {
    if(sceneLosEmptyCacheEnabled)sceneLosEmptyCacheFallbackCalls++;
    for(var i:int=1;i<n;i++) if(solid(loc,x+(tx-x)*i/n,y+(ty-y)*i/n)) return false;
    return true;
   }
   var cached:Boolean=false,left:int=0,top:int=0,right:int=0,bottom:int=0;
   var px:Number=0,py:Number=0,ix:int=0,iy:int=0,t:*=null;
   var hits:uint=0,lookups:uint=0,unblocked:Boolean=true;
   for(i=1;i<n;i++) {
    px=x+(tx-x)*i/n;py=y+(ty-y)*i/n;
    // getAbsTile accepts int coordinates before it divides by Tile.tileX/Y.
    ix=int(px);iy=int(py);
    if(cached && ix>=left && ix<right && iy>=top && iy<bottom) { hits++;continue; }
    lookups++;t=tile(loc,px,py);
    if(t==null) { unblocked=false;break; }
    if(num(t,"phis")==1) {
     // Keep the original point and short-circuit order for partial solid tiles.
     if(px>=num(t,"phX1",-1e9) && px<=num(t,"phX2",1e9) && py>=num(t,"phY1",-1e9) && py<=num(t,"phY2",1e9)) { unblocked=false;break; }
    } else {
     left=int(Math.floor(ix/40))*40;top=int(Math.floor(iy/40))*40;
     right=left+40;bottom=top+40;cached=true;
    }
   }
   sceneLosEmptyCacheCalls++;
   sceneLosEmptyCacheHits+=hits;sceneLosEmptyCacheLookups+=lookups;
   return unblocked;
  }
'''

IMPORT = ' import flash.system.ApplicationDomain;\n'

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def hashes(folder: Path) -> dict:
    return {p.name: sha(p) for p in sorted(folder.glob('*.as'))}

def write_new(path: Path, data: bytes) -> None:
    if path.exists():
        assert path.read_bytes() == data, f'refusing to overwrite different frozen data: {path}'
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def patched(original: bytes) -> bytes:
    text = original.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    old = OLD_CLEAR.replace('\n', newline)
    new = NEW_CLEAR.replace('\n', newline)
    addition = IMPORT.replace('\n', newline)
    anchor = ' import flash.utils.Dictionary;' + newline
    assert text.count(old) == 1 and text.count(anchor) == 1
    result = text.replace(old, new, 1).replace(anchor, anchor + addition, 1)
    reverse = result.replace(new, old, 1).replace(anchor + addition, anchor, 1)
    assert reverse.encode('utf-8') == original, 'reverse removal must restore every original byte'
    return result.encode('utf-8')

def validate_inputs() -> dict:
    pins = json.loads((HERE / 'source-pins.json').read_text('utf-8'))
    assert len(pins['sources']) == 20
    assert hashes(ORIGIN) == pins['sources']
    assert sha(ORIGIN / 'TDFCMod.swf') == pins['baseSWFSHA256']
    assert sha(ROOT / 'mods/TDFC/release/TDFCMod.swf') == pins['baseSWFSHA256']
    assert sha(BUILD / 'tdfc-threat.py') == pins['historicalRecipeSHA256']
    assert sha(BUILD / 'profile-vision.py') == pins['parserSHA256']
    receipt = MOD / 'state/performance-deployment-20261020.json'
    assert sha(receipt) == pins['receiptSHA256']
    deployed = json.loads(receipt.read_text('utf-8'))
    assert deployed['status'] == 'verified'
    assert deployed['targets']['mods/TDFC/release/TDFCMod.swf'][2] == pins['baseSWFSHA256']
    return pins

def prepare() -> dict:
    pins = validate_inputs()
    # Re-run only the historic pure-source recipe into OUR new directory.
    # No .build() call and no Java/AIR subprocess. The old source is read-only.
    spec = importlib.util.spec_from_file_location('tdfc_los_history', BUILD / 'tdfc-threat.py')
    historical = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(historical)
    replay = HERE / 'historical-recipe-replay'
    if not replay.exists():
        historical.OUT = replay
        historical.prepare()
    assert hashes(replay) == pins['sources'], 'historical recipe no longer reproduces 7ACD source snapshot'
    for name in pins['sources']:
        raw = (ORIGIN / name).read_bytes()
        write_new(HERE / 'original' / name, raw)
        write_new(HERE / 'source' / name, patched(raw) if name == 'GameBridge.as' else raw)
    original = (HERE / 'original/GameBridge.as').read_text('utf-8').splitlines(True)
    candidate = (HERE / 'source/GameBridge.as').read_text('utf-8').splitlines(True)
    diff = ''.join(difflib.unified_diff(original, candidate, fromfile='7ACD/GameBridge.as', tofile=VERSION+'/GameBridge.as'))
    write_new(HERE / 'candidate.diff', diff.encode('utf-8'))
    proof = check(write_proof=False)
    write_new(HERE / 'source-proof.json', (json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    return proof

def check(write_proof: bool = False) -> dict:
    pins = validate_inputs()
    assert hashes(HERE / 'original') == pins['sources']
    before, after = hashes(HERE / 'original'), hashes(HERE / 'source')
    assert set(after) == set(before)
    changed = [name for name in before if before[name] != after[name]]
    assert changed == ['GameBridge.as']
    assert (HERE / 'source/GameBridge.as').read_bytes() == patched((HERE / 'original/GameBridge.as').read_bytes())
    assert hashes(HERE / 'historical-recipe-replay') == before
    return {'version': VERSION, 'status': 'source-prepared-only', 'compiled': False, 'ranAIR': False,
            'productionEligible': False, 'baseSWFSHA256': pins['baseSWFSHA256'],
            'historicalRecipeReproducesAllSources': True, 'sourceCount': len(before),
            'changedSources': changed, 'unchangedSourceCount': len(before)-1,
            'reverseRemovalRestoresOriginalBytes': True, 'before': before, 'after': after,
            'sourcePinsSHA256': sha(HERE/'source-pins.json'), 'prepareSHA256': sha(Path(__file__)),
            'historicalRecipeSHA256': pins['historicalRecipeSHA256'], 'receiptSHA256': pins['receiptSHA256']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'check'])
    args = parser.parse_args()
    value = prepare() if args.mode == 'prepare' else check()
    print(json.dumps({k:v for k,v in value.items() if k not in ('before','after')}, ensure_ascii=False, indent=2))
