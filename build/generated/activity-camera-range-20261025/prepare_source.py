"""Prepare/check only: exact 7F1F six-class source plus one camera-range helper.

No compiler, AIR, SWF reads, production writes, lease-release or game execution.
The source evidence is printed as JSON; no file outside the allowed source folder
is written. Existing prepared files must be exact matches and are not replaced.
"""
from pathlib import Path
import argparse
import hashlib
import json

HERE=Path(__file__).resolve().parent
MOD=HERE.parents[2]
ORIGIN=MOD/'build/generated/activity-telemetry-20261022/original-source'
MANIFEST=MOD/'build/large-map/source-manifest.json'
MANIFEST_SHA='832319A1E57B5EEFEAB25818DDB07F726D6FA0A46B8CFDDF68DFC8927F426A95'
FORMAL_CS_SHA='7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
VERSION='activity-camera-range-1'
HELPER='SceneActivityCameraRange.as'
HELPER_SHA='898D0C6C260A49FC3DD5FF8B374933845A168948F3FACAA90A669FB903A99227'
EXPECTED={
    'ContinuousSceneDoc.as':'2FBFFE1895829A6D8DC866A170C92CDBF000DC99B1A08DFE92F0891432C2C462',
    'ContinuousSceneMod.as':'D97C62521892DBF46DBAC9D38BFE6CB721FB49D0F8FEA5CFEA4B5E796851C450',
    'NativeSceneActivity.as':'01182FACDFB7AFBA7A03CCFF1C3C28E14219E8FE654118149C50FCF7261AC0F7',
    'NativeSceneAdapter.as':'6541C722618DEC9BB637BA6082A950CC4A01029B1EB01B65D992516D1D7B90C3',
    'NativeSceneWalls.as':'DB9F65FC20DDE979E36E203E78EE58FA8A5C75C0B268BE9B0A24111276BA06EF',
    'SingleSceneDocument.as':'5A9AAD9936C5FE49D2B6606353A64974F0380460139EC375292ECF7CA79413DF',
}
API='''        public static function activityCameraRangeVersion():String {return SceneActivityCameraRange.version();}
        public static function activityCameraRangeSet(enabled:Boolean):Object {return SceneActivityCameraRange.setEnabled(enabled);}
        public static function activityCameraRangeVerify():Object {
            var w:*=NativeSceneAdapter.host();
            return SceneActivityCameraRange.verify(w,w && w.loc ? sleeping(w.loc) : null);
        }
        public static function activityCameraRangeSnapshot():Object {return SceneActivityCameraRange.snapshot();}
'''
ACTIVITY_EDITS=(
    ('            var threats:Array=[];',
     '            var cameraRange:Object=SceneActivityCameraRange.observing() ? SceneActivityCameraRange.plan(w,loc,s.tick,left,top,right,bottom) : null;\n'
     '            var useCameraRange:Boolean=cameraRange!=null && cameraRange.applied===true;\n'
     '            if(useCameraRange) {left=cameraRange.planned.left;top=cameraRange.planned.top;right=cameraRange.planned.right;bottom=cameraRange.planned.bottom;}\n'
     '            var threats:Array=[];'),
    ('|| (Math.abs(u.X-loc.gg.X)<1900 && Math.abs(u.Y-loc.gg.Y)<1300)',
     '|| (!useCameraRange && (Math.abs(u.X-loc.gg.X)<1900 && Math.abs(u.Y-loc.gg.Y)<1300))'),
    ('        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {',
     API+'        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {'),
)
MOD_EDITS=(
    ('                wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats};',
     '                wake:NativeSceneActivity.wake,activityStats:NativeSceneActivity.stats,\n'
     '                activityCameraRangeVersion:NativeSceneActivity.activityCameraRangeVersion,\n'
     '                activityCameraRangeSet:NativeSceneActivity.activityCameraRangeSet,\n'
     '                activityCameraRangeVerify:NativeSceneActivity.activityCameraRangeVerify,\n'
     '                activityCameraRangeSnapshot:NativeSceneActivity.activityCameraRangeSnapshot};'),
)

def sha(data):return hashlib.sha256(data).hexdigest().upper()

def transform(name,data,reverse=False):
    edits=ACTIVITY_EDITS if name=='NativeSceneActivity.as' else MOD_EDITS if name=='ContinuousSceneMod.as' else ()
    text=data.decode('utf-8')
    for old,new in reversed(edits) if reverse else edits:
        before,after=(new,old) if reverse else (old,new)
        assert text.count(before)==1,(name,'reverse' if reverse else 'forward',before)
        text=text.replace(before,after,1)
    return text.encode('utf-8')

def inputs():
    assert sha(MANIFEST.read_bytes())==MANIFEST_SHA
    manifest=json.loads(MANIFEST.read_text('utf-8-sig'))
    assert sorted(p.name for p in ORIGIN.iterdir() if p.is_file())==sorted(EXPECTED)
    result={}
    for name,digest in EXPECTED.items():
        data=(ORIGIN/name).read_bytes()
        assert sha(data)==digest==manifest['mods\\ContinuousScene\\src\\'+name],name
        result[name]=data
    return result

def protected_segments(original,prepared):
    old,new=original.decode('utf-8'),prepared.decode('utf-8')
    spans={
        'projectileThreats':('            var threats:Array=[];','            for each(var u:* in loc.units) {'),
        'engagementAndProtected':('                var r:Object=s.records[u];','                    || (Math.abs(u.X-loc.gg.X)<1900'),
        'threatGraceAndSleep':('                if(!active)for each(var threat:Object in threats)','        public static function sleeping(loc:*):Object {'),
        'sleepingAndWake':('        public static function sleeping(loc:*):Object {','        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {'),
        'freezeResumeAndStats':('        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {',None),
    }
    result={}
    for label,(start,end) in spans.items():
        part=old[old.index(start):old.index(end)] if end else old[old.index(start):]
        assert part in new,(label,'protected source changed')
        result[label]=dict(sha256=sha(part.encode('utf-8')),bytes=len(part.encode('utf-8')),byteIdentical=True)
    return result

def prepare(write=False):
    source=inputs();target=HERE/'source-candidate'
    assert target.is_dir() and sha((target/HELPER).read_bytes())==HELPER_SHA
    assert not any(p.is_dir() for p in target.iterdir())
    assert set(p.name for p in target.iterdir())<=set(EXPECTED)|{HELPER}
    output={name:transform(name,data) for name,data in source.items()}
    for name,data in output.items():
        assert transform(name,data,reverse=True)==source[name],name
    protected=protected_segments(source['NativeSceneActivity.as'],output['NativeSceneActivity.as'])
    for name,data in output.items():
        path=target/name
        if path.exists():assert path.read_bytes()==data,('refuse overwrite',name)
        elif write:path.write_bytes(data)
        else:raise AssertionError(('prepared source missing',name))
    changed=sorted(name for name in source if source[name]!=output[name])
    assert changed==['ContinuousSceneMod.as','NativeSceneActivity.as']
    assert len(list(target.iterdir()))==7
    assert inputs()==source
    return dict(version=VERSION,sourceOnly=True,compiled=False,airRun=False,deployed=False,
        formalCSReferenceSHA256=FORMAL_CS_SHA,manifest=str(MANIFEST),manifestSHA256=MANIFEST_SHA,
        origin=str(ORIGIN),sourceCount=6,candidateCount=7,sourceSHA256=EXPECTED,
        candidateSHA256={p.name:sha(p.read_bytes()) for p in sorted(target.iterdir())},
        changed=changed,added=[HELPER],reverseExact=True,protectedSegments=protected,
        disabledByDefault=True,activityReleaseNotIncluded=True,sourceInputsUnchanged=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Only create the six missing candidate source files; never overwrite.')
    args=parser.parse_args()
    print(json.dumps(prepare(write=args.prepare),ensure_ascii=False,indent=2))
