"""Compile an isolated production CS carrier draft; never modify src or release.

Requires explicit --build. Copies the prior frozen product sources once, changes
only the stats export, and compiles ContinuousSceneDoc into this folder.
No game, host patch, or deployment is launched here.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2]
ROOT=HERE.parents[4]
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
TOOLS=ROOT/'mods/Sandevistan/build/tools'
HOST='B84F24280B3C676F4068E1CDC5A6EBEE89988F62BCF7A44D4DD71A4771360184'
MOD_SHA='9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31'
PRIOR=HERE.parent/'sats-visible-final-20261028'
PRIOR_PRODUCT='F64C23FA50C2FF7FB92A1A16EE26B9989DAA1D5479E8435DBFD50D1B49F1EDDA'
PRIOR_RECEIPT='94E6AA5E920BD0C78B186A2A3032DE6BEFBF65DA2F44E88B6AA284C5FC4D2EFD'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true',required=True)
    parser.parse_args()
    assert __debug__ and HERE.name=='sats-visible-release-20261028'
    frozen=HERE/'frozen-product-src'
    output=HERE/'ContinuousSceneMod.swf'
    config=HERE/'product-compiler.xml'
    log=HERE/'product-compiler.log'
    receipt=HERE/'product-build.json'
    assert not any(p.exists() for p in (frozen,output,config,log,receipt)), 'Preserve prior/partial product build'
    production={str(ROOT/'pfe.swf'):HOST,str(MOD/'release/ContinuousSceneMod.swf'):MOD_SHA}
    assert production=={p:sha(p) for p in production}, 'Installed baseline changed'
    original={p.relative_to(MOD/'src').as_posix():p for p in (MOD/'src').rglob('*.as')
              if 'tests' not in p.relative_to(MOD/'src').parts}
    assert 'ContinuousSceneDoc.as' in original and 'ContinuousSceneMod.as' in original
    assert sha(PRIOR/'product-build.json')==PRIOR_RECEIPT,'Prior product receipt changed'
    prior_build=json.loads((PRIOR/'product-build.json').read_text('utf-8-sig'))
    assert prior_build['compiled'] and prior_build['outputSHA256']==PRIOR_PRODUCT
    source={name:PRIOR/'frozen-product-src'/name for name in prior_build['frozenSource']}
    assert prior_build['frozenSource']=={name:sha(path) for name,path in source.items()},'Prior frozen source changed'
    assert set(source)==set(original)|{'SatsVisibleGuard.as'},'Production source inventory changed'
    for name,path in original.items():
        if name!='ContinuousSceneMod.as':assert sha(path)==sha(source[name]),'Source diverged from frozen product: '+name
    overlays={'ContinuousSceneMod.as':HERE/'product-src/ContinuousSceneMod.as',
              'SatsVisibleGuard.as':HERE/'SatsVisibleGuard.as'}
    assert 'SatsVisibleGuard.as' not in original, 'Production source already integrated; explicitly rebase'
    inputs={str(p):sha(p) for p in [Path(__file__),PRIOR/'product-build.json',*source.values(),*original.values(),*overlays.values(),
        JAVA,TOOLS/'flexsdk/lib/mxmlc.jar',TOOLS/'airsdk/frameworks/libs/air/airglobal.swc',
        MOD/'build/motion-test.py',ROOT/'mods/ModLoader/tools/test_registry.py']}
    entry=overlays['ContinuousSceneMod.as'].read_text('utf-8-sig')
    prior=original['ContinuousSceneMod.as'].read_text('utf-8-sig')
    assert prior.count('public static const VERSION:String="0.9.1";')==1
    assert prior.count('            main.addChild(carrier); log("v"+VERSION+" loaded");')==1
    expected=prior.replace('public static const VERSION:String="0.9.1";',
                           'public static const VERSION:String="0.9.2";',1).replace(
        '            main.addChild(carrier); log("v"+VERSION+" loaded");',
        '            main.addChild(carrier); log("v"+VERSION+" loaded");\n            SatsVisibleGuard.install(main);',1)
    assert entry==expected, 'Product entry differs beyond version and handler installation'
    assert sha(overlays['ContinuousSceneMod.as'])==sha(source['ContinuousSceneMod.as']),'Entry differs from frozen product'
    prior_guard=source['SatsVisibleGuard.as'].read_text('utf-8-sig')
    install='            carrier["nativeAPI"]["satsVisibleV3"]=handle;'
    assert prior_guard.count(install)==1
    assert overlays['SatsVisibleGuard.as'].read_text('utf-8-sig')==prior_guard.replace(
        install,install+'\n            carrier["nativeAPI"]["satsVisibleStatsV3"]=stats;',1), 'Guard differs beyond stats export'
    sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
    from test_registry import Registration
    motion=load('sats_product_motion_guard',MOD/'build/motion-test.py')
    with Registration(owner='ContinuousScene / SATS V3 product draft / 01a13816',
            purpose='Compile production carrier draft only',run_dir=HERE,evidence=HERE,wait=300) as lease:
        assert motion.memory_status()['availableCommit']>=2*1024**3
        frozen.mkdir()
        selected=dict(source,**overlays)
        for name,path in selected.items():
            target=frozen/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write(path.read_bytes())
        frozen_inputs={name:sha(frozen/name) for name in selected}
        config_text=('<flex-config><target-player>32.0</target-player><compiler>'
            '<external-library-path><path-element>'+str(TOOLS/'airsdk/frameworks/libs/air/airglobal.swc').replace('\\','/')+
            '</path-element></external-library-path><source-path><path-element>'+str(frozen).replace('\\','/')+
            '</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler></flex-config>')
        with config.open('x',encoding='utf-8',newline='\n') as stream:stream.write(config_text)
        command=[str(JAVA),'-Xmx512m','-Dfile.encoding=UTF-8','-jar',str(TOOLS/'flexsdk/lib/mxmlc.jar'),
            '+flexlib='+str(TOOLS/'flexsdk/frameworks'),'-load-config='+str(config),'-swf-version=32',
            '-use-network=false','-static-link-runtime-shared-libraries=true','-output='+str(output),
            str(frozen/'ContinuousSceneDoc.as')]
        result=dict(version='0.9.2',compiled=False,deployed=False,runtimeVerified=False,
            productOnly=True,hostBaseline=HOST,modBaseline=MOD_SHA,handlerAction='satsVisibleV3',
            statsExport='satsVisibleStatsV3',priorProduct=PRIOR_PRODUCT,onlyPriorChange='export existing stats object',
            inputs=inputs,frozenSource=frozen_inputs,configSHA256=sha(config),command=command,
            sourceFilesChanged=['ContinuousSceneMod.as','SatsVisibleGuard.as'],
            note='Production carrier and helper only; no private probe, test code, save or input driver linked.')
        process=None
        try:
            with log.open('xb') as stream:
                lease.before_launch('Owned SATS product compiler, heap 512 MiB')
                process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                lease.child(process.pid)
                begin=time.monotonic()
                while process.poll() is None:
                    assert time.monotonic()-begin<180 and motion.memory_status()['availableCommit']>=512*1024**2
                    try:process.wait(.25)
                    except subprocess.TimeoutExpired:pass
                assert process.returncode==0,'Product compilation failed'
            assert inputs=={p:sha(p) for p in inputs},'Source/tool changed during compile'
            assert frozen_inputs=={name:sha(frozen/name) for name in frozen_inputs},'Frozen source changed'
            assert production=={p:sha(p) for p in production},'Production changed during compile'
            result.update(compiled=True,outputSHA256=sha(output))
            lease.outcome='passed';lease.note='Production carrier draft compiled; not runtime verified or deployed'
        finally:
            if process:
                if process.poll() is None:process.kill();process.wait(15)
                lease.child_stopped()
            record(receipt,result)
    print(json.dumps({k:result[k] for k in ('version','compiled','deployed','outputSHA256')}))


if __name__=='__main__':
    main()
