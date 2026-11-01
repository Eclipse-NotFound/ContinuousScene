"""Separate sampled GC contexts from other CPU stacks; do not infer wall time."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

sys.dont_write_bytecode = True
from combat_allocation_summary import group

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / 'knowledge/experiments/evidence/combat-cost-target-v29-20261101-r1/storage/result.json'


def main():
    raw = json.loads(RAW.read_text('utf-8-sig'))
    windows = [w for w in raw['frameCost']['windows'] if w['valid']]
    gc, rest, gc_stacks = Counter(), Counter(), Counter()
    gc_labels = {'[sweep]', '[reap]', '[mark]'}
    for window in windows:
        for stack, count in window['cpu'].items():
            frames = json.loads(stack)
            if any(label in gc_labels for label in frames):
                gc[group(stack)] += count
                gc_stacks[stack] += count
            else:
                rest[group(stack)] += count
    out = dict(
        rawSHA256=hashlib.sha256(RAW.read_bytes()).hexdigest().upper(),
        validWindows=len(windows),
        gcFrameLabels=sorted(gc_labels),
        totalSamples=sum(gc.values()) + sum(rest.values()),
        gcSamples=sum(gc.values()),
        otherSamples=sum(rest.values()),
        gcContexts=dict(gc.most_common()),
        otherContexts=dict(rest.most_common()),
        gcStacks=gc_stacks.most_common(),
        limits='Internal allocation sampling was enabled and adds overhead. CPU sample counts are not wall-time shares. The caller triggering GC does not identify all allocation producers.',
    )
    assert out['totalSamples'] == 1157
    with (HERE / 'cpu-gc-breakdown.json').open('x', encoding='utf-8') as stream:
        json.dump(out, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != 'gcStacks'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
