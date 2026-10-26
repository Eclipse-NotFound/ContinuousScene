"""Only shorten each measured combat segment; native behavior stays intact."""
from pathlib import Path
import shutil

VERSION='camera-atlas-short-combat-1'
CHANGED=['ContinuousSceneMotionProbe.as']
PRESENTER_SHA='AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'

def transform(source):
    before='if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300))return;'
    after='if(age<(cfg.drawControl=="atlas"?120:(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300)))return;'
    old_version='camera-atlas-paged-smg10-combat-1'
    assert source.count(before)==1 and source.count(old_version)==2
    result=source.replace(before,after,1).replace(old_version,VERSION)
    assert result.replace(VERSION,old_version).replace(after,before,1)==source
    return result

def prepare(source,destination):
    assert not destination.exists()
    shutil.copytree(source,destination)
    main=destination/CHANGED[0]
    main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
