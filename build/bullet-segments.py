"""Diagnostic-only Bullet.run segments on the restored BEFC host; never deploy.

The four timings are inclusive, contiguous branches of one run call. In
particular, units includes all hit callbacks, and directHitTileInclusiveMs is
already included in terrainInclusiveMs. Millisecond resolution and profiler
overhead make this unsuitable for accepting a performance improvement.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
OUT = B / 'generated/bullet-segments-20261021'
BASE = B / 'generated/fog-typed'
SOURCE = OUT / 'original/scripts/fe/weapon/Bullet.as'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
SOURCE_SHA = 'FC6A0A71649EC70747F05D32A3F47A953EF1C53DAA84DA04321F4F2DAEF156AF'
XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
FIELDS = [
    'calls', 'terrainInclusiveMs', 'unitsInclusiveMs', 'boxesInclusiveMs',
    'targetExplosionInclusiveMs', 'directHitTileInclusiveMs',
    'directHitTileCalls', 'unitVisits', 'unitEligible', 'unitHitBodyEntries',
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e = load('bullet_segments_enemy', B / 'enemy-speed.py')


def instrument(source):
    """Pure source transformation; preserve everything outside run verbatim."""
    assert 'csBS' not in source, 'Diagnostic local names already present'
    begin, end = e.parser._body(source, 'run')
    body = source[begin + 1:end]
    declarations = '''
         var _loc2_:Unit = null;
         var _loc3_:Tile = null;
         var _loc4_:* = undefined;'''
    body = e.once(body, declarations, '')

    # Phase switches precede original statements; return/continue/break and the
    # actual BEFC AABB-before-RConnect predicate remain exactly as exported.
    body = e.once(body, '         for each(_loc2_ in loc.units)', '''         if(csBSStats != null)
         {
            csBSNow = flash.utils.getTimer();
            csBSTerrain += csBSNow - csBSStart;
            csBSStart = csBSNow;
         }
         csBSPhase = 1;
         for each(_loc2_ in loc.units)''')
    body = e.once(body, '''         for each(_loc2_ in loc.units)
         {''', '''         for each(_loc2_ in loc.units)
         {
            ++csBSVisits;''')
    eligible = '''            if(!(_loc2_.sost == 4 || _loc2_.disabled || _loc2_.trigDis || _loc2_.loc != loc))
            {'''
    body = e.once(body, eligible, eligible + '\n               ++csBSEligible;')
    hit = '''               if(X >= _loc2_.X1 && X <= _loc2_.X2 && Y >= _loc2_.Y1 && Y <= _loc2_.Y2 && UnitTurret.rconnectSecurityHit(this.owner,_loc2_,this.targetObj || _loc2_.fraction != this.owner.fraction))
               {'''
    body = e.once(body, hit, hit + '\n                  ++csBSHits;')
    boxes = '         if(loc.celObj && loc.celObj is Box && this.crack && Boolean(this.owner) && this.owner.player)'
    body = e.once(body, boxes, '''         if(csBSStats != null)
         {
            csBSNow = flash.utils.getTimer();
            csBSUnits += csBSNow - csBSStart;
            csBSStart = csBSNow;
         }
         csBSPhase = 2;
''' + boxes)
    target = '         if(this.celX > -10000 && this.celY > -10000 && this.explRadius > 0)'
    body = e.once(body, target, '''         if(csBSStats != null)
         {
            csBSNow = flash.utils.getTimer();
            csBSBoxes += csBSNow - csBSStart;
            csBSStart = csBSNow;
         }
         csBSPhase = 3;
''' + target)
    call = '                     loc.hitTile(_loc3_,this.destroy,X,Y,this.tipDecal);'
    body = e.once(body, call, '''                     if(csBSStats != null)
                     {
                        ++csBSHitTileCalls;
                        csBSHitTileStart = flash.utils.getTimer();
                     }
''' + call + '''
                     if(csBSStats != null)
                     {
                        csBSHitTile += flash.utils.getTimer() - csBSHitTileStart;
                     }''')

    prologue = declarations + '''
         var csBSCarrier:Object = null;
         var csBSApi:Object = null;
         var csBSStats:Object = null;
         var csBSPhase:int = 0;
         var csBSStart:int = 0;
         var csBSNow:int = 0;
         var csBSTerrain:int = 0;
         var csBSUnits:int = 0;
         var csBSBoxes:int = 0;
         var csBSTarget:int = 0;
         var csBSVisits:int = 0;
         var csBSEligible:int = 0;
         var csBSHits:int = 0;
         var csBSHitTile:int = 0;
         var csBSHitTileCalls:int = 0;
         var csBSHitTileStart:int = 0;
         if(World.w != null && World.w.main != null)
            csBSCarrier = World.w.main.getChildByName("ContinuousSceneCarrier");
         if(csBSCarrier != null)
            csBSApi = csBSCarrier["nativeAPI"];
         if(csBSApi != null && "bulletSegments" in csBSApi)
            csBSStats = csBSApi["bulletSegments"] as Object;
         if(csBSStats != null)
            csBSStart = flash.utils.getTimer();
         try
         {'''
    epilogue = '''
         }
         finally
         {
            if(csBSStats != null)
            {
               csBSNow = flash.utils.getTimer() - csBSStart;
               if(csBSPhase == 0) csBSTerrain += csBSNow;
               else if(csBSPhase == 1) csBSUnits += csBSNow;
               else if(csBSPhase == 2) csBSBoxes += csBSNow;
               else csBSTarget += csBSNow;
               if(!("version" in csBSStats))
               {
                  csBSStats.version = "bullet-segments-1";
                  csBSStats.diagnosticOnly = true;
                  csBSStats.performanceEligible = false;
                  csBSStats.directHitTileIncludedInTerrain = true;
'''
    for field in FIELDS:
        epilogue += '                  csBSStats.' + field + ' = 0;\n'
    epilogue += '''               }
               ++csBSStats.calls;
               csBSStats.terrainInclusiveMs += csBSTerrain;
               csBSStats.unitsInclusiveMs += csBSUnits;
               csBSStats.boxesInclusiveMs += csBSBoxes;
               csBSStats.targetExplosionInclusiveMs += csBSTarget;
               csBSStats.directHitTileInclusiveMs += csBSHitTile;
               csBSStats.directHitTileCalls += csBSHitTileCalls;
               csBSStats.unitVisits += csBSVisits;
               csBSStats.unitEligible += csBSEligible;
               csBSStats.unitHitBodyEntries += csBSHits;
            }
         }
      '''
    # FFDec adds NEED_ACTIVATION and 21 local slots for finally. Keep the
    # original invocation frame instead: flush before both original returns
    # and at normal completion. Any runtime exception invalidates the run.
    prologue = e.once(prologue, '         try\n         {', '')
    epilogue = e.once(epilogue, '\n         }\n         finally\n         {', '\n')
    epilogue = e.once(epilogue, '\n            }\n         }\n      ', '\n            }\n      ')
    assert body.count('return;') == 2
    body = body.replace('return;', epilogue + '\n                     return;')
    result = source[:begin + 1] + prologue + body + epilogue + source[end:]
    check_begin, check_end = e.parser._body(result, 'run')
    assert source[:begin + 1] == result[:check_begin + 1]
    assert source[end:] == result[check_end:]
    assert result.count('loc.hitTile(_loc3_,this.destroy,X,Y,this.tipDecal);') == 1
    assert result.count(hit) == 1, 'Actual AABB/RConnect predicate changed'
    # FFDec treats a fully qualified function expression as a dynamic property
    # chain ("flash" -> "utils") unless explicitly imported. Bind the native
    # function at compile time; do not rely on a nonexistent global flash object.
    result = result.replace('flash.utils.getTimer()', 'getTimer()')
    return e.once(result, '   import fe.*;', '   import fe.*;\n   import flash.utils.getTimer;')


def prepare():
    assert e.digest(ROOT / 'pfe.swf') == e.digest(BASE / 'pfe.swf') == HOST_SHA
    assert e.digest(BASE / 'pfe.xml') == XML_SHA
    assert e.digest(SOURCE) == SOURCE_SHA
    target = OUT / 'source/fe/weapon/Bullet.as'
    old_sources = list((OUT / 'source').rglob('*.as'))
    assert all(p == target for p in old_sources), 'Unexpected import source; refusing whole-class contamination'
    result = instrument(SOURCE.read_text('utf-8-sig'))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, 'utf-8')
    meta = dict(
        diagnosticOnly=True, performanceEligible=False, deployed=False,
        compiled=False, base=HOST_SHA, baseXml=XML_SHA,
        originalSource=SOURCE_SHA, source=e.digest(target),
        changedMethods=['fe.weapon.Bullet::0:1:run'],
        statsVersion='bullet-segments-1', fields=FIELDS,
        semantics={
            'terrainInclusiveMs': 'Movement, terrain/water/bounds and their nested callbacks',
            'unitsInclusiveMs': 'Original ordered unit enumeration, filters and all hit callbacks',
            'boxesInclusiveMs': 'Two original targeted box checks and callbacks; not a box scan',
            'targetExplosionInclusiveMs': 'Original target proximity/random explosion branch',
            'directHitTileInclusiveMs': 'Direct run-to-hitTile only; already inside terrain',
            'unitVisits': 'Each original for-each item before any targetObj replacement',
            'unitEligible': 'Entries passing original dead/disabled/trigDis/location filters',
            'unitHitBodyEntries': 'Entries passing original AABB and RC predicate; not damage count',
        },
        limitations=[
            'getTimer has integer-millisecond resolution; short calls may measure zero.',
            'Local counters and timing add diagnostic overhead; exceptional runs are rejected.',
            'Inclusive callback time is not enumeration/self time.',
            'Nested or reentrant Bullet.run calls are inclusive and can overlap.',
            'Stats object must be supplied by isolated probe; absent object disables aggregation.',
        ],
    )
    (OUT / 'provenance.json').write_text(json.dumps(meta, indent=2), 'utf-8')
    return meta


def build(wait=300):
    with e.motion.Registration(
        owner='ContinuousScene / bullet segment diagnosis / 01a13816',
        purpose='Diagnostic-only Bullet.run build, no game run or deployment',
        run_dir=OUT, evidence=OUT / 'build.json', resource='game', wait=wait,
    ) as record:
        assert not e.motion.air_pids(), 'Other AIR present; untouched'
        meta = prepare()
        ff = lambda *args: subprocess.run([
            str(e.JAVA), '-Xmx1400m', '-jar',
            str(e.TOOLS / 'ffdec/ffdec-cli.jar'), *map(str, args),
        ], check=True)
        audit = B / 'bullet-segments-audit.py'
        assert audit.is_file(), 'Required strict byte-retention audit unavailable'
        ff('-importScript', BASE / 'pfe.swf', OUT / 'compiled.swf', OUT / 'source')
        ff('-swf2xml', OUT / 'compiled.swf', OUT / 'compiled.xml')
        subprocess.run([
            sys.executable, '-B', str(audit), '--retain',
            '--base', str(BASE / 'pfe.xml'),
            '--candidate', str(OUT / 'compiled.xml'),
            '--out', str(OUT / 'retained.xml'),
        ], check=True)
        # XML serialization re-encodes hundreds of untouched vector assets.
        # Keep every original SWF tag and splice only the audited game ABC.
        ff('-xml2swf', OUT / 'retained.xml', OUT / 'serialized.swf')
        ff('-swf2xml', OUT / 'serialized.swf', OUT / 'serialized.xml')
        subprocess.run([
            sys.executable, '-B', str(audit), '--splice-abc',
            '--base', str(BASE / 'pfe.xml'),
            '--candidate', str(OUT / 'serialized.xml'),
            '--base-swf', str(BASE / 'pfe.swf'),
            '--candidate-swf', str(OUT / 'serialized.swf'),
            '--out', str(OUT / 'pfe.swf'),
        ], check=True)
        ff('-swf2xml', OUT / 'pfe.swf', OUT / 'pfe.xml')
        subprocess.run([
            sys.executable, '-B', str(audit), '--base', str(BASE / 'pfe.xml'),
            '--candidate', str(OUT / 'pfe.xml'),
            '--base-swf', str(BASE / 'pfe.swf'),
            '--candidate-swf', str(OUT / 'pfe.swf'),
            '--out', str(OUT / 'semantic-audit.json'),
        ], check=True)
        assert e.digest(ROOT / 'pfe.swf') == HOST_SHA, 'Installed host changed during diagnostic build'
        meta.update(compiled=True, candidate=e.digest(OUT / 'pfe.swf'),
                    candidateXml=e.digest(OUT / 'pfe.xml'),
                    audit=e.digest(OUT / 'semantic-audit.json'))
        (OUT / 'build.json').write_text(json.dumps(meta, indent=2), 'utf-8')
        record.outcome = 'passed'
        record.note = 'Bullet.run diagnostic compiled and byte-retention audit passed; runtime pending'
        print(json.dumps(meta), flush=True)
        return meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--wait', type=int, default=300)
    args = parser.parse_args()
    if args.build:
        build(args.wait)
    else:
        print(json.dumps(prepare()))
