"""Bounded native CPU/allocation samples; never infer frame speed from counts."""
from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib, argparse

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'mods/ContinuousScene/knowledge/experiments/evidence'

def group(key):
    if 'FrameCostProbe' in key or 'ContinuousSceneMotionMod' in key: return 'probe'
    if 'UnitTurret/animate' in key: return 'turret-animation-context'
    if 'sceneNativeEnvironment' in key: return 'native-environment'
    if 'TdfcRuntime' in key: return 'tdfc'
    if 'addiction::' in key: return 'addiction'
    if 'rconnect' in key.lower() or 'NetHud' in key: return 'rconnect'
    if '[render]' in key or '[pre-render]' in key: return 'native-render'
    if 'hitTile' in key or '/drawDecal' in key or '/sceneDecal' in key: return 'terrain-hit-chain'
    if 'fe.weapon::Bullet' in key or 'fe.weapon::Weapon' in key: return 'weapon-bullet-chain'
    if 'fe.unit::' in key: return 'native-unit-other'
    if key == '[]': return 'empty-stack'
    return 'other'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='combat-cost-target-v29-20261101-r1')
    evidence=BASE/parser.parse_args().name
    rawpath = evidence / 'storage/result.json'
    raw = json.loads(rawpath.read_text('utf-8-sig'))
    frame = raw['frameCost']
    windows = [w for w in frame['windows'] if w['valid']]
    out = dict(ok=raw['ok'], rawSHA256=hashlib.sha256(rawpath.read_bytes()).hexdigest().upper(),
               valid=len(windows), total=len(frame['windows']), errors=frame['errors'],
               scope='Native samples with internal allocations enabled. Not FPS acceptance. Live sizes omit dead weak references and may count shared resources.',
               groups={}, top={}, byAxis={}, fixture=raw.get('fixtureKnockback'),
               fixedTarget=raw.get('fixtureFixedTarget'),fixtureActualEnd=raw.get('fixtureActualEnd'),
               qualification=[b.get('visibleQualification') for b in raw['blocks']],
               combat=[{'actualShotFrames':b['combatEnd']['actualShotFrames']-b['combatStart']['actualShotFrames'],
                        'targetFrames':b['combatEnd']['targetFrames']-b['combatStart']['targetFrames']}
                       for b in raw['blocks'] if b.get('combatEnd')])
    for kind in ['cpu','alloc','liveSizes']:
        combined, groups = Counter(), Counter()
        axes = defaultdict(Counter)
        for w in windows:
            combined.update(w[kind])
            for key, value in w[kind].items():
                groups[group(key)] += value
                axes[w['mode']][group(key)] += value
        out['groups'][kind] = dict(groups.most_common())
        out['top'][kind] = combined.most_common(24)
        out['byAxis'][kind] = {k:dict(v.most_common()) for k,v in axes.items()}
    with (evidence/'allocation-summary.json').open('x',encoding='utf-8') as stream:
        json.dump(out,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k not in ('top','byAxis')},ensure_ascii=False))
    print(json.dumps(out['top']['cpu'],ensure_ascii=False))

if __name__ == '__main__': main()
