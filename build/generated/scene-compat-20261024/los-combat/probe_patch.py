"""Only boundary LOS toggles/observations plus the reviewed two clock anchors."""
from pathlib import Path
import importlib.util
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'tdfc-los-combat-1'
API_VERSION = 'tdfc-los-empty-cell-1'
spec = importlib.util.spec_from_file_location('los_clock_patch', HERE.parent/'environment-control/probe_patch.py')
clock = importlib.util.module_from_spec(spec); spec.loader.exec_module(clock)

FIELDS = '''
        private static var losApi:*,losCarrier:*,losOriginal:*,losOwned:Boolean=false;
'''

METHODS = '''
        private static function losKey(name:String):QName {return new QName("",name);}
        private static function losRead(expected:* = null):Object {
            var carrier:*=main.getChildByName("ContinuousSceneTdfcThreat");
            if(!carrier || (losOwned && (carrier!==losCarrier || carrier["api"]!==losApi)))
                throw new Error("LOS carrier or API identity changed");
            var api:*=carrier["api"];
            if(!api || api[losKey("sceneLosEmptyCacheVersion")]!=="tdfc-los-empty-cell-1")
                throw new Error("Exact LOS diagnostic API required");
            var enabled:*=api[losKey("sceneLosEmptyCacheEnabled")];
            if(!(enabled is Boolean) || (expected!==null && enabled!==expected))
                throw new Error("LOS public toggle changed unexpectedly");
            return {version:String(api[losKey("sceneLosEmptyCacheVersion")]),enabled:enabled,
                calls:Number(api[losKey("sceneLosEmptyCacheCalls")]),
                fallback:Number(api[losKey("sceneLosEmptyCacheFallbackCalls")]),
                hits:Number(api[losKey("sceneLosEmptyCacheHits")]),
                lookups:Number(api[losKey("sceneLosEmptyCacheLookups")])};
        }
        private static function losBegin(window:int):Object {
            if(window<0 || window>3 || cfg.drawControl!="rcnative" || !cfg.nativeInputMotion || !cfg.nativeSprint)
                throw new Error("Only the original four-window dense combat fixture is allowed");
            if(!losOwned) {
                var initial:Object=losRead(false);
                losCarrier=main.getChildByName("ContinuousSceneTdfcThreat");losApi=losCarrier["api"];
                losOriginal=initial.enabled;losOwned=true;
                report.tdfcLos={version:"tdfc-los-combat-1",initial:initial,order:[false,true,true,false],
                    boundaryOnly:true,counterReset:false,componentCalls:false,cleanup:null};
            }
            var enabled:Boolean=window==1 || window==2;
            var begin:int=getTimer(),before:Object=losRead(window==0?false:window==1?false:true);
            losApi[losKey("sceneLosEmptyCacheEnabled")]=enabled;
            var after:Object=losRead(enabled),end:int=getTimer();
            return {index:window,enabled:enabled,before:before,after:after,
                switchBeginAtMs:begin,switchEndAtMs:end,switchMs:end-begin,end:null,delta:null};
        }
        private static function losEnd(target:Object):void {
            var value:Object=target.tdfcLos,end:Object=losRead(value.enabled),delta:Object={};
            for each(var name:String in ["calls","fallback","hits","lookups"]) {
                var n:Number=Number(end[name])-Number(value.after[name]);
                if(!isFinite(n) || n<0 || n!=Math.floor(n) || (!value.enabled && n!=0))
                    throw new Error("Invalid LOS counter delta: "+name);
                delta[name]=n;
            }
            value.end=end;value.delta=delta;value.observedEndAtMs=getTimer();
        }
        private static function losRestore():Object {
            var out:Object={owned:losOwned,restored:!losOwned,original:losOriginal,before:null,after:null};
            if(!losOwned)return out;
            try {out.before=losRead();}
            finally {
                // Restore the exact API we changed even if its carrier was replaced.
                // Never write the replacement carrier's API.
                losApi[losKey("sceneLosEmptyCacheEnabled")]=losOriginal;
                out.after=losApi[losKey("sceneLosEmptyCacheEnabled")];
                out.restored=out.after===losOriginal;
                if(report.tdfcLos)report.tdfcLos.cleanup=out;
                losOwned=false;
            }
            return out;
        }
'''

PATCHES = (
    ('        private static var continuousPreviousSampleAt:int=-1;', FIELDS),
    ('            var rcSwitch:Object=null;', '\n            var losWindow:Object=losBegin(index);'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '\n            row.tdfcLos=losWindow;'),
    ('                    report.samples.push(row); // Dense v2: short heartbeat only during sampling.',
     '\n                    losEnd(row);'),
    ('            closeProbeTiming(true);', '''
            try {
                var losCleanup:Object=losRestore();
                if(!losCleanup.restored)throw new Error("LOS toggle restoration failed");
            } catch(losCleanupError:*) {error=(error?error+"\\n":"")+"LOS cleanup: "+String(losCleanupError);}
'''),
    ('        private static function readRcOffline(enabled:Boolean):Object {', METHODS),
)


def transform(source):
    assert 'tdfcLos' not in source and 'losBegin' not in source
    changed = clock.transform(source)
    for anchor, insertion in PATCHES:
        assert changed.count(anchor) == 1, anchor
        # New methods precede readRcOffline; all other additions follow their anchor.
        changed = changed.replace(anchor, insertion+anchor if insertion == METHODS else anchor+insertion)
    restored = changed
    for anchor, insertion in reversed(PATCHES):
        block = insertion+anchor if insertion == METHODS else anchor+insertion
        assert restored.count(block) == 1
        restored = restored.replace(block, anchor)
    assert restored == clock.transform(source)
    return changed


def prepare(source: Path, destination: Path):
    assert not destination.exists()
    shutil.copytree(source, destination)
    file = destination/'ContinuousSceneMotionProbe.as'
    file.write_text(transform(file.read_text(encoding='utf-8-sig')), encoding='utf-8')
