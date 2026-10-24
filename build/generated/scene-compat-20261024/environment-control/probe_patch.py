"""Add two in-memory clock anchors to the exact frozen 39A dense probe."""
from pathlib import Path
import shutil

VERSION = 'environment-control-1'
PATCHES = (
    ('                report.continuousSampling={version:"motion-continuous-wall-1",startedAtMs:caseBegin};',
     '\n                report.environmentClock={version:"environment-clock-1",start:{sampleAtMs:caseBegin,'
     'timerBeforeMs:getTimer(),epochMs:new Date().time,timerAfterMs:getTimer()},end:null};'),
    ('                    if(++index<cases.length)startCase();else {',
     '\n                        report.environmentClock.end={sampleAtMs:row.sampleAtMs[row.sampleAtMs.length-1],'
     'timerBeforeMs:getTimer(),epochMs:new Date().time,timerAfterMs:getTimer()};'),
)


def transform(source):
    assert 'environmentClock' not in source
    changed = source
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, anchor
        changed = changed.replace(anchor, anchor + insertion)
    restored = changed
    for anchor, insertion in reversed(PATCHES):
        assert restored.count(anchor + insertion) == 1
        restored = restored.replace(anchor + insertion, anchor)
    assert restored == source, 'Only two additive clock records are allowed'
    return changed


def prepare(source: Path, destination: Path):
    assert not destination.exists()
    shutil.copytree(source, destination)
    file = destination / 'ContinuousSceneMotionProbe.as'
    file.write_text(transform(file.read_text(encoding='utf-8-sig')), encoding='utf-8')
