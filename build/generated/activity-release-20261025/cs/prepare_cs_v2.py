"""Prepare only: exact 7F1F six-class source, bounded leases and idle release.

No compiler, AIR, binary reads, production-source edits or deployment. The
separate fe.unit.NativeSceneIdleAccess helper is required at integration time.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[3]
ROOT = MOD.parent.parent
ORIGIN = MOD/'build/generated/activity-telemetry-20261022/original-source'
MANIFEST = MOD/'build/large-map/source-manifest.json'
MANIFEST_SHA = '832319A1E57B5EEFEAB25818DDB07F726D6FA0A46B8CFDDF68DFC8927F426A95'
FORMAL_CS_SHA = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
VERSION = 'activity-lease-1'
EXPECTED = {
    'ContinuousSceneDoc.as': '2FBFFE1895829A6D8DC866A170C92CDBF000DC99B1A08DFE92F0891432C2C462',
    'ContinuousSceneMod.as': 'D97C62521892DBF46DBAC9D38BFE6CB721FB49D0F8FEA5CFEA4B5E796851C450',
    'NativeSceneActivity.as': '01182FACDFB7AFBA7A03CCFF1C3C28E14219E8FE654118149C50FCF7261AC0F7',
    'NativeSceneAdapter.as': '6541C722618DEC9BB637BA6082A950CC4A01029B1EB01B65D992516D1D7B90C3',
    'NativeSceneWalls.as': 'DB9F65FC20DDE979E36E203E78EE58FA8A5C75C0B268BE9B0A24111276BA06EF',
    'SingleSceneDocument.as': '5A9AAD9936C5FE49D2B6606353A64974F0380460139EC375292ECF7CA79413DF',
}

LEASE_API = '''        public static function activityLeaseVersion():String {return "activity-lease-1";}
        public static function activityLease(u:*,frames:int=45):Boolean {
            if(!u || frames<=0 || frames>45)return false;
            var s:Object=rooms[u.loc];
            if(!s)return false;
            var r:Object=s.records[u];
            if(!r)return false;
            var deadline:Number=Number(s.tick)+frames;
            if(deadline>r.leaseUntil)r.leaseUntil=deadline;
            resume(r);delete s.sleeping[u];
            return true;
        }
'''

ACTIVITY_EDITS = (
    ('    import flash.utils.getDefinitionByName;\n',
     '    import flash.utils.getDefinitionByName;\n    import fe.unit.NativeSceneIdleAccess;\n'),
    ('r={hp:u.hp,engaged:false,until:0,clips:[]};',
     'r={hp:u.hp,engaged:false,until:0,clips:[],leaseUntil:0,externalWake:false,released:false};'),
    ('                if(u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0)r.engaged=true;',
     '                var freshEngagement:Boolean=u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0;\n'
     '                if(freshEngagement)r.engaged=true;\n'
     '                var nativeIdle:*=null;\n'
     '                if(r.released) {\n'
     '                    nativeIdle=NativeSceneIdleAccess.mayRest(u);\n'
     '                    if(nativeIdle!==true){r.engaged=true;r.released=false;}\n'
     '                }'),
    ('|| u.fraction==loc.gg.fraction || u.sost!=1 || r.engaged\n',
     '|| u.fraction==loc.gg.fraction || u.sost!=1\n'),
    ('                if(active)r.until=s.tick+45;',
     '                // Distance, visibility, status and projectile guards above remain native.\n'
     '                // A lease and the old grace timer are independent, never self-renewing.\n'
     '                if(r.engaged && !freshEngagement && !active && !r.externalWake\n'
     '                    && r.leaseUntil<=s.tick) {\n'
     '                    if(nativeIdle===null)nativeIdle=NativeSceneIdleAccess.mayRest(u);\n'
     '                    if(nativeIdle===true){r.engaged=false;r.released=true;}\n'
     '                }\n'
     '                active=active || r.engaged;\n'
     '                if(active)r.until=s.tick+45;'),
    ('                active=active || s.tick<r.until;',
     '                active=active || s.tick<r.until || s.tick<r.leaseUntil;'),
    ('            if(r){r.engaged=true;resume(r);}',
     '            if(r){r.externalWake=true;r.engaged=true;r.released=false;resume(r);}'),
    ('        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {',
     LEASE_API+'        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {'),
)
MOD_EDITS = (
    ('                wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats};',
     '                wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats,\n'
     '                activityLease:NativeSceneActivity.activityLease,activityLeaseVersion:NativeSceneActivity.activityLeaseVersion};'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def transform(name, data, reverse=False):
    edits = ACTIVITY_EDITS if name == 'NativeSceneActivity.as' else MOD_EDITS if name == 'ContinuousSceneMod.as' else ()
    text = data.decode('utf-8')
    for old, new in reversed(edits) if reverse else edits:
        before, after = (new, old) if reverse else (old, new)
        assert text.count(before) == 1, (name, 'reverse' if reverse else 'forward', before)
        text = text.replace(before, after, 1)
    return text.encode('utf-8')


def inputs():
    assert sha(MANIFEST.read_bytes()) == MANIFEST_SHA
    manifest = json.loads(MANIFEST.read_text('utf-8-sig'))
    assert sorted(p.name for p in ORIGIN.iterdir() if p.is_file()) == sorted(EXPECTED)
    result = {}
    for name, expected in EXPECTED.items():
        data = (ORIGIN/name).read_bytes()
        assert sha(data) == expected == manifest['mods\\ContinuousScene\\src\\'+name], name
        result[name] = data
    return result


def timing_model():
    """Small policy model, not execution of AS3 or evidence of gameplay safety."""
    passed = []

    def state(engaged=False, until=0, lease=0, external=False, sleeping=False, released=False):
        return dict(engaged=engaged, until=until, leaseUntil=lease, externalWake=external,
                    sleeping=sleeping, resumes=0, released=released)

    def step(record, tick, protected=False, fresh=False, idle=True):
        if fresh: record['engaged'] = True
        if record['released'] and idle is not True:
            record['engaged'] = True; record['released'] = False
        active = protected
        if (record['engaged'] and not fresh and not active and not record['externalWake']
                and record['leaseUntil'] <= tick and idle is True):
            record['engaged'] = False; record['released'] = True
        active = active or record['engaged']
        if active: record['until'] = tick+45
        active = active or tick < record['until'] or tick < record['leaseUntil']
        record['sleeping'] = not active
        return active

    def lease(record, tick, frames=45):
        if record is None or frames <= 0 or frames > 45: return False
        record['leaseUntil'] = max(record['leaseUntil'], tick+frames)
        record['resumes'] += 1; record['sleeping'] = False
        return True

    record = state(engaged=True, until=100)
    assert step(record, 56) and not record['engaged'] and record['until'] == 100
    assert all(step(record, tick) and record['until'] == 100 for tick in range(57, 100))
    assert not step(record, 100) and record['until'] == 100
    passed.append('released-engagement-keeps-existing-grace-without-renewing')
    for reason in ('pause-disabled', 'player', 'npc', 'boss', 'fraction', 'not-alive', 'damaged',
                   'stun', 'bind', 'levitation', 'emergency', 'effects', 'moving-interaction',
                   'player-distance', 'viewport', 'projectile'):
        record = state(engaged=True)
        assert step(record, 50, protected=True) and record['engaged'] and record['until'] == 95
        passed.append('existing-protection-'+reason)
    for reason in ('new-damage', 'target', 'cut', 'poison'):
        record = state()
        assert step(record, 50, fresh=True) and record['engaged'] and record['until'] == 95
        passed.append('fresh-engagement-'+reason)
    for idle in (False, None, 1, 'true'):
        record = state(engaged=True)
        assert step(record, 50, idle=idle) and record['engaged']
    passed.append('idle-reader-must-return-strict-true')
    record = state(engaged=True, external=True)
    assert all(step(record, tick) and record['engaged'] for tick in range(1, 301))
    passed.append('legacy-external-wake-is-permanent')
    record = state(sleeping=True)
    assert lease(record, 100) and not record['sleeping'] and not record['engaged'] and record['until'] == 0
    assert all(step(record, tick) and record['until'] == 0 for tick in range(101, 145))
    assert not step(record, 145) and record['until'] == 0
    passed.append('unengaged-lease-has-no-extra-grace-or-latch')
    record = state(sleeping=True)
    assert lease(record, 100, 45) and lease(record, 101, 1) and record['leaseUntil'] == 145
    assert lease(record, 120, 45) and record['leaseUntil'] == 165 and record['resumes'] == 3
    passed.append('leases-only-extend-and-always-resume')
    record = state(engaged=True, lease=145)
    assert step(record, 144) and record['engaged'] and record['until'] == 189
    assert step(record, 145) and not record['engaged'] and record['until'] == 189
    assert all(step(record, tick) and record['until'] == 189 for tick in range(146, 189))
    assert not step(record, 189)
    passed.append('engaged-lease-expiry-retains-last-native-grace')
    for frames in (-1, 0, 46):
        record = state(sleeping=True); before = dict(record)
        assert not lease(record, 10, frames) and record == before
    assert not lease(None, 10)
    passed.append('invalid-lease-does-not-mutate')
    for tick, sleeping in ((80, False), (150, True)):
        record = state(until=100, sleeping=sleeping, released=True)
        assert step(record, tick, idle=False) and record['engaged'] and not record['released']
        assert record['until'] == tick+45
        assert step(record, tick+1, idle=True) and not record['engaged'] and record['released']
        passed.append('native-alarm-after-release-'+('sleep' if sleeping else 'grace'))
    return dict(passed=True, kind='Python policy model only', cases=passed, count=len(passed),
                actualAS3Run=False, helperSemanticsNotValidated=True)


def artifacts():
    original = inputs(); candidate = {name: transform(name, data) for name, data in original.items()}
    restored = {name: transform(name, data, True) for name, data in candidate.items()}
    assert restored == original
    changed = sorted(name for name in original if candidate[name] != original[name])
    assert changed == ['ContinuousSceneMod.as', 'NativeSceneActivity.as']
    activity = candidate['NativeSceneActivity.as'].decode('utf-8')
    assert activity.count('r.until=s.tick+45;') == 1
    assert activity.index('if(active)r.until=s.tick+45;') < activity.index('active=active || s.tick<r.until || s.tick<r.leaseUntil;')
    assert 'r.engaged' not in LEASE_API and 'r.until' not in LEASE_API and 'externalWake' not in LEASE_API
    diff = ''.join(''.join(difflib.unified_diff(original[name].decode('utf-8').splitlines(True),
        candidate[name].decode('utf-8').splitlines(True), fromfile='7F1F/'+name, tofile='candidate/'+name)) for name in changed)
    proof = dict(version=VERSION, preparedOnly=True, productionBinaryRead=False, declaredFormalCsSHA256=FORMAL_CS_SHA,
        historicalSourceDirectory=str(ORIGIN), manifestPath=str(MANIFEST), manifestSHA256=MANIFEST_SHA,
        prepareScriptSHA256=sha(Path(__file__).read_bytes()), originalSHA256={name: sha(data) for name, data in original.items()},
        candidateSHA256={name: sha(data) for name, data in candidate.items()},
        reverseSHA256={name: sha(data) for name, data in restored.items()}, reverseByteExact=True,
        historicalClassCount=6, changed=changed, unchanged=[name for name in EXPECTED if name not in changed],
        requiredExternalHelper='fe.unit.NativeSceneIdleAccess.mayRest(u):Boolean, strict true only; unknown/error must return false',
        helperSourceIncluded=False, helperRequiresIndependentReview=True,
        sourceSemantics=dict(legacyWakePermanent=True, leaseDoesNotSetEngaged=True,
            leaseDoesNotExtendNativeGrace=True, graceNeverRenewsItself=True,
            originalProtectionExpressionPreservedExceptSeparatedEngaged=True, originalProjectileRectangleUnchanged=True,
            releaseRequiresAllProtectionFalse=True, newEngagementBlocksReleaseSameFrame=True, releasedIdleRevalidatedEveryTick=True,
            noDiagnosticHotPathCounters=True),
        staticTimingModel=timing_model(), compiled=False, runtimeTested=False, deployed=False)
    outputs = {HERE/'original'/name: data for name, data in original.items()}
    outputs.update({HERE/'source-v2'/name: data for name, data in candidate.items()})
    outputs[HERE/'candidate-v2.diff'] = diff.encode('utf-8')
    outputs[HERE/'source-proof-v2.json'] = (json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    return outputs, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    args = parser.parse_args(); outputs, proof = artifacts()
    for path, data in outputs.items():
        assert path.resolve().is_relative_to(HERE)
        if args.check or path.exists(): assert path.read_bytes() == data, 'Refuse to overwrite different frozen output: '+str(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    print(json.dumps(dict(version=VERSION, checkOnly=args.check, changed=proof['changed'],
        reverseByteExact=proof['reverseByteExact'], originalClasses=6, modelCases=proof['staticTimingModel']['count'],
        sourceProofSHA256=sha((HERE/'source-proof-v2.json').read_bytes()), compiled=False, runtimeTested=False), indent=2))


if __name__ == '__main__': main()
