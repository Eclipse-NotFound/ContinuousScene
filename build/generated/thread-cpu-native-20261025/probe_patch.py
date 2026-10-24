"""Exact 29AF fixture: add in-memory clock anchors only, no per-frame change."""
from pathlib import Path
import hashlib
import shutil

MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as']
EDITS = (
    ('                report.continuousSampling={version:"motion-continuous-wall-1",startedAtMs:caseBegin};',
     '\n                report.environmentClock={version:"environment-clock-1",start:{sampleAtMs:caseBegin,'
     'timerBeforeMs:getTimer(),epochMs:new Date().time,timerAfterMs:getTimer()},end:null};'
     '\n                report.threadClockCases=[];'),
    ('            var rcSwitch:Object=null;',
     '\n            report.threadClockCases.push({index:index,sampleAtMs:caseBegin,'
     'timerBeforeMs:getTimer(),epochMs:new Date().time,timerAfterMs:getTimer()});'),
    ('                    if(++index<cases.length)startCase();else {',
     '\n                        report.environmentClock.end={sampleAtMs:row.sampleAtMs[row.sampleAtMs.length-1],'
     'timerBeforeMs:getTimer(),epochMs:new Date().time,timerAfterMs:getTimer()};'),
)

def transform(source):
    assert 'environmentClock' not in source and 'threadClockCases' not in source
    changed = source
    for anchor, insertion in EDITS:
        assert changed.count(anchor) == 1, anchor
        changed = changed.replace(anchor, anchor + insertion, 1)
    restored = changed
    for anchor, insertion in reversed(EDITS):
        assert restored.count(anchor + insertion) == 1
        restored = restored.replace(anchor + insertion, anchor, 1)
    assert restored == source
    return changed

def prepare(source: Path, destination: Path):
    assert not destination.exists()
    original = source / CHANGED[0]
    assert hashlib.sha256(original.read_bytes()).hexdigest().upper() == MAIN_RAW_SHA
    shutil.copytree(source, destination)
    (destination / CHANGED[0]).write_text(transform(original.read_text('utf-8-sig')), 'utf-8')
