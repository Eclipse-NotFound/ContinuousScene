from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-atlas-20261027'
VERSION='camera-persistent-atlas-checks-1'

def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('persistent_checked_base',BASE/'prepare.py')
one=base.one

def classic_source():return base.presentation.classic_source()

def persistent_source():
    s=base.presentation.persistent_source()
    s=one(s,'// beginFrame already restored native tiles. Nothing cached is shown\n            // at rest; native mutations remain visible immediately. Movement\n            // resumes through the complete revision/visibility synchronization.',
          '// The optional idle bypass explicitly restores native tiles.\n            // Forced presentation remains bound through subsequent native frames.')
    s=one(s,'for each(page in pages)if(required[page.key])for(var displayLayer:int=0;displayLayer<4;++displayLayer)page.layers[displayLayer].visible=page.content[displayLayer];',
          'for each(page in pages)for(var displayLayer:int=0;displayLayer<4;++displayLayer)page.layers[displayLayer].visible=Boolean(required[page.key]) && page.content[displayLayer];')
    return s

def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'                            var allocateAt:int=getTimer();classic.preallocate(world);persistent.preallocate(world);',
          '''                            report.atlasContracts=ScenePersistentAtlasChecks.run(stage);
                            require(report.atlasContracts.complete && report.atlasContracts.passed,"Persistent atlas contract fixture failed");
                            var allocateAt:int=getTimer();classic.preallocate(world);persistent.preallocate(world);''')
    s=one(s,'            try {setRenderer(0);classic.clear();persistent.clear();} catch(atlasError:Error){cleanup.errors.push("atlas restore: "+atlasError.message);}',
          '''            try {setRenderer(0);} catch(modeError:Error){cleanup.errors.push("atlas mode restore: "+modeError.message);}
            try {classic.clear();} catch(classicError:Error){cleanup.errors.push("classic release: "+classicError.message);}
            try {persistent.clear();} catch(persistentError:Error){cleanup.errors.push("persistent release: "+persistentError.message);}''')
    return s

def runner_source():
    return base.runner_source().replace(base.VERSION,VERSION).replace('len(after) == 88','len(after) == 89').replace("len(value['frozenSourceSHA256']) == 88","len(value['frozenSourceSHA256']) == 89")

if __name__=='__main__':
    assert (HERE/'tests/ScenePersistentAtlasChecks.as').is_file()
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('SceneClassicAtlas.as',classic_source()),('ScenePersistentAtlas.as',persistent_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared event/revision/restore fixture and three-arm persistent-atlas camera comparison')
