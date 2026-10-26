"""Same scroll experiment with exact host setter suppression and strict entry state."""
from pathlib import Path
import importlib.util
import shutil
HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-world-scroll-phases-20261027/probe_patch.py'
spec=importlib.util.spec_from_file_location('native_scroll_phase_seed',PATCH_SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ORIGINAL=base.HELPER
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=base.CHANGED
EXTRA_INPUTS=(*base.EXTRA_INPUTS,base.PATCH_SOURCE,base.ORIGINAL,HERE/'prepare.py',
              HERE/'inspect_host.py',HERE/'host_patch.py',HERE/'build_host.py',
              HERE/'host-build.json',HERE/'audit-proof.json',HERE/'pfe.swf',HERE/'pfe.xml')

def helper_source():
    s=ORIGINAL.read_text('utf-8-sig');assert s==base.helper_source()
    old='''            if(!sameArray(entry,pending.terrain)) {
                var nativeEntry:Array=pending.terrain.concat();nativeEntry[2]=Number(pending.vx);nativeEntry[3]=Number(pending.vy);
                require(sameArray(entry,nativeEntry),"Unexpected next-frame scroll state: "+entry+" expected="+pending.terrain);
                ++report.phaseObservation.nativeEntryRepositions;
            }'''
    changes=[
        ('camera-world-scroll-phases-1','camera-world-scroll-native-1'),
        ('report.phaseObservation={listenerAdded:', 'report.nativePositionChecks=0;\n                report.phaseObservation={listenerAdded:'),
        (old,'            require(sameArray(entry,pending.terrain),"Host changed world coordinates between helper calls");'),
        ('            cam.calc(player); // Accurate host calc includes exactly one native sceneTick.',
         '            cam.calc(player); // Exact host retains one native sceneTick, but skips the two world setters under scrollRect.\n'
         '            if(scrollCondition!=0) {\n'
         '                require(world.visual.x==0 && world.visual.y==0,"Host scroll guard did not keep the world stationary");\n'
         '                ++report.nativePositionChecks;\n'
         '            }'),
    ]
    for before,after in changes:
        assert s.count(before)==1,before;s=s.replace(before,after)
    return s

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/CHANGED[1]).exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0];main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/CHANGED[1])
