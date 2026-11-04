"""Merge the parallel session's pending MEMORY block into the current file.

The pending payload is a fragment (header + the aim-v3 block only, 4.9 KB), not
a full file: applying it verbatim would truncate the 86 KB snapshot. So take its
block, splice it in after the title, verify both sides survived, and only then
drop the pending entry.
"""
from pathlib import Path
import json
import sys

MOD = Path(__file__).resolve().parents[1]
TARGET = MOD / 'state/MEMORY.md'
PENDING = MOD / 'state/MEMORY.md.dshpending'
START = '<!-- aim-look-v3-implemented-20261104 -->'
END = '<!-- /aim-look-v3-implemented-20261104 -->'
TITLE = '# ContinuousScene — 当前快照'


def main():
    current = TARGET.read_text(encoding='utf-8')
    payload = (PENDING / 'content').read_text(encoding='utf-8')
    if START in current:
        sys.exit('block already present; nothing to do')
    start = payload.index(START)
    end = payload.index(END) + len(END)
    block = payload[start:end].strip()
    if TITLE not in current:
        sys.exit('unexpected MEMORY.md shape')
    head = TITLE + '\n\n'
    rest = current[len(head):]
    merged = head + block + '\n\n' + rest
    TARGET.write_text(merged, encoding='utf-8')
    check = TARGET.read_text(encoding='utf-8')
    report = {
        'written': str(TARGET),
        'bytesBefore': len(current.encode('utf-8')),
        'bytesAfter': len(merged.encode('utf-8')),
        'pendingFragmentBytes': len(payload.encode('utf-8')),
        'hasAimV3Block': START in check and END in check,
        'hasCullingBlock': '<!-- cull-scale-20261104 -->' in check,
        'hasBulletGridBlock': '<!-- bullet-grid-20261104 -->' in check,
    }
    (PENDING / 'merge-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not (report['hasAimV3Block'] and report['hasCullingBlock'] and report['hasBulletGridBlock']):
        sys.exit('merge lost a block')


if __name__ == '__main__':
    main()
