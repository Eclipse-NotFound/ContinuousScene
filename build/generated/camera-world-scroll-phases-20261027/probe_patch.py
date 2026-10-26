"""Observe EXIT_FRAME, allow only demonstrated native camera entry position writes."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-scroll-cost-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('world_scroll_phase_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',HERE/'frame-phase.as.inc')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    for old,new in [
        ('camera-world-scroll-cost-1','camera-world-scroll-phases-1'),
        ('    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.events.Event;'),
        ('report.originalFrameRate=saved.frameRate;report.testFrameRate=120;',
         'report.phaseObservation={listenerAdded:0,listenerRemoved:0,snapshots:0,nativeEntryRepositions:0,errors:[]};\n                stage.addEventListener(Event.EXIT_FRAME,recordExit,false,int.MIN_VALUE);exitListening=true;++report.phaseObservation.listenerAdded;\n                report.originalFrameRate=saved.frameRate;report.testFrameRate=120;'),
        ('require(sameLayers(layerState(),row.condition),"Terrain changed during rendered interval");row.terrain.push(pending.terrain);',
         'var entryState:Array=layerState();verifyFramePhases(entryState,now);\n                    row.terrain.push(lastExit.terrain);row.exitSnapshots.push(lastExit);row.entryStates.push(entryState);'),
        ('worldVisible:[],windowVisible:[],terrain:[],start:snapshot()',
         'worldVisible:[],windowVisible:[],terrain:[],exitSnapshots:[],entryStates:[],start:snapshot()'),
        ('pending={vx:cam.vx','pending={serial:++frameSerial,appliedAt:getTimer(),vx:cam.vx'),
        ('var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};',
         'var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};\n            try {if(exitListening){stage.removeEventListener(Event.EXIT_FRAME,recordExit);exitListening=false;++report.phaseObservation.listenerRemoved;}}catch(exitError:Error){cleanup.errors.push("EXIT_FRAME listener: "+exitError.message);}'),
        ('        private var scrollCondition:int=0;',
         (HERE/'frame-phase.as.inc').read_text('utf-8-sig')+'        private var scrollCondition:int=0;'),
    ]:
        assert old in s,old;s=s.replace(old,new)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
