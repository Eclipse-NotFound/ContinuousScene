"""Prepare a source-frozen, diagnostic-only activity telemetry module.

No JVM, AIR, production edits, or deployment. The parent task compiles this
explicit six-class source closure after review. Original scheduling expressions
remain in place; insertions are removable and reverse-checked byte for byte.
"""
from pathlib import Path
import hashlib,json

B=Path(__file__).resolve().parent
MOD=B.parent
ROOT=MOD.parent.parent
OUT=B/'generated/activity-telemetry-20261022'
BASE=B/'large-map/ContinuousSceneMod.swf'
BASE_SHA='7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST_SHA='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FILES=['ContinuousSceneDoc.as','ContinuousSceneMod.as','NativeSceneAdapter.as',
       'NativeSceneActivity.as','NativeSceneWalls.as','SingleSceneDocument.as']

def sha_bytes(data):return hashlib.sha256(data).hexdigest().upper()
def sha(path):return sha_bytes(Path(path).read_bytes())

HELPERS=r'''
        // Diagnostic helpers deliberately catch their own errors: observation
        // must not interrupt the original scheduler or change its decisions.
        private static function telemetryStart(s:Object,w:*,left:Number,top:Number,right:Number,bottom:Number):void {
            try {
                if(!s.telemetry)s.telemetry={reads:0,errors:0,wakeCalls:0,wakeNew:0,globalMax:0,
                    interval:telemetryInterval(),last:null};
                var d:Object=s.telemetry;
                d.last={tick:s.tick,scenePauseDistant:w.grafon.scenePauseDistant,
                    view:{left:left,top:top,right:right,bottom:bottom,scale:w.cam.scaleV,
                        vx:w.cam.vx,vy:w.cam.vy,screenX:w.cam.screenX,screenY:w.cam.screenY,
                        playerX:w.loc.gg.X,playerY:w.loc.gg.Y},
                    threats:0,maxThreat:null,maxThreatArea:-1,invalidThreats:0,
                    engaged:0,threatActive:0,graceActive:0,baseActive:0,farActive:0,
                    farReasons:{},farNew:[],farNewCount:0,
                    engagedNew:{hp:0,target:0,cut:0,poison:0,wake:0,total:0}};
                ++d.interval.frames;
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryInterval():Object {
            return {frames:0,maxAwake:-1,minAsleep:-1,maxima:[],maximaOmitted:0,
                maxThreat:null,maxThreatArea:-1,invalidThreats:0,wakeCalls:0,wakeNew:0,
                farWakeNewCount:0,farWakeNew:[],
                engagedNew:{hp:0,target:0,cut:0,poison:0,wake:0,total:0}};
        }
        private static function telemetryError(s:Object):void {
            try {if(s && s.telemetry)++s.telemetry.errors;}catch(ignored:Error){}
        }
        private static function telemetryThreat(s:Object,p:*,rectangle:Object):void {
            try {
                var d:Object=s.telemetry,last:Object=d.last;
                ++last.threats;
                var area:Number=(rectangle.r-rectangle.l)*(rectangle.b-rectangle.t);
                if(!isFinite(area) || !isFinite(rectangle.l) || !isFinite(rectangle.r) ||
                    !isFinite(rectangle.t) || !isFinite(rectangle.b)) {
                    ++last.invalidThreats;++d.interval.invalidThreats;
                }
                var detail:Object={x:p.X,y:p.Y,dx:p.dx,dy:p.dy,vel:p.vel,babah:p.babah,off:p.off,
                        liv:p.liv,isExpl:p.isExpl,explRadius:p.explRadius,spring:p.spring,
                        checkLine:p.checkLine,dist:p.dist,weapon:p.weap?p.weap.id:p.weapId,
                        owner:p.owner?p.owner.id:null,
                        ownerClass:p.owner?flash.utils.getQualifiedClassName(p.owner):null,
                        bulletClass:flash.utils.getQualifiedClassName(p),
                        rectangle:{l:rectangle.l,r:rectangle.r,t:rectangle.t,b:rectangle.b},area:area};
                // The native scheduler only reads l/r/t/b. This extra value is
                // a plain snapshot, never a live projectile or owner reference.
                rectangle.telemetry=detail;
                if(area>last.maxThreatArea || last.maxThreat==null) {
                    last.maxThreat=detail;last.maxThreatArea=area;
                    if(area>d.interval.maxThreatArea || d.interval.maxThreat==null) {
                        d.interval.maxThreatArea=area;d.interval.maxThreat=detail;
                    }
                }
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryEngaged(s:Object,u:*,r:Object,hp:Boolean,target:Boolean,cut:Boolean,poison:Boolean,viaWake:Boolean=false):void {
            try {
                var d:Object=s.telemetry;
                if(!d || !d.last)return;
                var flags:Object={hp:hp,target:target,cut:cut,poison:poison,wake:viaWake};
                var frameCounts:Object=d.last.engagedNew,intervalCounts:Object=d.interval.engagedNew;
                for(var key:String in flags)if(flags[key]) {
                    frameCounts[key]=int(frameCounts[key])+1;
                    intervalCounts[key]=int(intervalCounts[key])+1;
                }
                ++d.last.engagedNew.total;++d.interval.engagedNew.total;
                r.telemetryEngaged={tick:s.tick,sources:flags};
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryUnit(s:Object,w:*,loc:*,u:*,r:Object,wasAsleep:Boolean,baseActive:Boolean,matched:Object,grace:Boolean,active:Boolean,left:Number,top:Number,right:Number,bottom:Number):void {
            try {
                var last:Object=s.telemetry.last;
                if(r.engaged)++last.engaged;
                if(baseActive)++last.baseActive;
                if(matched)++last.threatActive;
                if(grace)++last.graceActive;
                if(!active)return;
                var near:Boolean=(Math.abs(u.X-loc.gg.X)<1900 && Math.abs(u.Y-loc.gg.Y)<1300)
                    || (u.X+u.scX>=left && u.X-u.scX<=right && u.Y>=top && u.Y-u.scY<=bottom);
                if(near)return;
                ++last.farActive;
                var reason:String=!w.grafon.scenePauseDistant?"pause-disabled":u===loc.gg || u.player?"player":
                    u.npc?"npc":u.boss?"boss":u.fraction<=0 || u.fraction>=100 || u.fraction==loc.gg.fraction?"nonhostile":
                    u.sost!=1?"not-alive":r.engaged?"engaged":u.hp<u.maxhp?"damaged":
                    u.stun>0 || u.bind!=null || u.levit || u.t_emerg>0?"status":u.effects.length>0?"effects":
                    u.inter && u.inter.isMove?"interaction":matched?"projectile":grace?"grace":"unclassified";
                last.farReasons[reason]=int(last.farReasons[reason])+1;
                if(wasAsleep) {
                    ++last.farNewCount;
                    if(last.farNew.length<8)last.farNew.push({id:u.id,cls:flash.utils.getQualifiedClassName(u),
                        x:u.X,y:u.Y,hp:u.hp,maxhp:u.maxhp,target:u.celUnit?u.celUnit.id:null,
                        reason:reason,engaged:!!r.engaged,engagedOrigin:r.telemetryEngaged,
                        until:r.until,tick:s.tick,trigger:matched?matched.telemetry:null});
                }
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryFinish(s:Object):void {
            try {
                var d:Object=s.telemetry,last:Object=d.last,interval:Object=d.interval;
                last.awake=s.awake;last.asleep=s.asleep;
                if(s.awake>d.globalMax)d.globalMax=s.awake;
                if(s.awake>interval.maxAwake) {
                    interval.maxAwake=s.awake;
                    var row:Object={tick:s.tick,awake:s.awake,asleep:s.asleep,
                        scenePauseDistant:last.scenePauseDistant,view:last.view,
                        threats:last.threats,maxThreat:last.maxThreat,invalidThreats:last.invalidThreats,
                        engaged:last.engaged,baseActive:last.baseActive,threatActive:last.threatActive,
                        graceActive:last.graceActive,farActive:last.farActive,farReasons:last.farReasons,
                        farNewCount:last.farNewCount,farNew:last.farNew,engagedNew:telemetryCopyCounts(last.engagedNew)};
                    if(interval.maxima.length<64)interval.maxima.push(row);
                    else {++interval.maximaOmitted;interval.maxima[63]=row;}
                }
                if(interval.minAsleep<0 || s.asleep<interval.minAsleep)interval.minAsleep=s.asleep;
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryWake(s:Object,u:*,r:Object,wasAsleep:Boolean,wasEngaged:Boolean):void {
            try {
                if(!s.telemetry)return;
                ++s.telemetry.wakeCalls;++s.telemetry.interval.wakeCalls;
                if(wasAsleep){++s.telemetry.wakeNew;++s.telemetry.interval.wakeNew;}
                if(r && !wasEngaged && r.engaged)telemetryEngaged(s,u,r,false,false,false,false,true);
                // wake() deletes sleeping before the next update. Capture it
                // here so that a remote wake cannot disappear between reads.
                if(wasAsleep && s.telemetry.last) {
                    var view:Object=s.telemetry.last.view;
                    var near:Boolean=(Math.abs(u.X-view.playerX)<1900 && Math.abs(u.Y-view.playerY)<1300)
                        || (u.X+u.scX>=view.left && u.X-u.scX<=view.right && u.Y>=view.top && u.Y-u.scY<=view.bottom);
                    if(!near) {
                        var interval:Object=s.telemetry.interval;
                        ++interval.farWakeNewCount;
                        if(interval.farWakeNew.length<8)interval.farWakeNew.push({id:u.id,
                            cls:flash.utils.getQualifiedClassName(u),x:u.X,y:u.Y,hp:u.hp,maxhp:u.maxhp,
                            target:u.celUnit?u.celUnit.id:null,reason:"wake",tick:s.tick,
                            engaged:!!(r && r.engaged),engagedOrigin:r?r.telemetryEngaged:null});
                    }
                }
            }catch(error:Error){telemetryError(s);}
        }
        private static function telemetryCopyCounts(value:Object):Object {
            return {hp:value.hp,target:value.target,cut:value.cut,poison:value.poison,wake:value.wake,total:value.total};
        }
        private static function telemetryCurrent(value:Object):Object {
            var result:Object={};
            for(var key:String in value)result[key]=value[key];
            // wake() may be called after stats() within the same native frame.
            // No other last-frame field is changed outside update().
            result.engagedNew=telemetryCopyCounts(value.engagedNew);
            return result;
        }
'''

STATS=r'''        public static function stats():Object {
            if(!current)return null;
            var result:Object={awake:current.awake,asleep:current.asleep};
            try {
                var d:Object=current.telemetry;
                if(d) {
                    result.version="activity-telemetry-1";
                    result.diagnosticOnly=true;result.performanceAcceptance=false;
                    result.telemetry={read:++d.reads,tick:current.tick,errors:d.errors,
                        globalMaxAwake:d.globalMax,wakeCalls:d.wakeCalls,wakeNew:d.wakeNew,
                        current:telemetryCurrent(d.last),interval:d.interval,
                        notes:["awake/asleep are the original update counters; wake() can remove sleeping entries later in the same frame.",
                            "Interval counters reset on every activityStats read. Current-frame counters are not reset.",
                            "Threat/grace/base counts are exclusive causes; engaged counts include all retained records seen this update.",
                            "Far-new samples are limited to eight per frame, and saved on interval awake records only."]};
                    // Do not mutate returned objects after a later frame.
                    d.interval=telemetryInterval();
                }
            }catch(error:Error){telemetryError(current);result.telemetryError=true;}
            return result;
        }'''

def prepare():
    assert sha(BASE)==sha(MOD/'release/ContinuousSceneMod.swf')==BASE_SHA,'CS baseline drift'
    assert sha(ROOT/'pfe.swf')==HOST_SHA,'Host baseline drift'
    manifest_path=B/'large-map/source-manifest.json'
    receipt_path=MOD/'state/deployment-v090.json'
    manifest=json.loads(manifest_path.read_text('utf-8-sig'))
    receipt=json.loads(receipt_path.read_text('utf-8-sig'))
    assert receipt['status']=='verified' and receipt['after']['mods/ContinuousScene/release/ContinuousSceneMod.swf']==BASE_SHA
    original={}
    for name in FILES:
        source=MOD/'src'/name;data=source.read_bytes()
        key=str(source.relative_to(ROOT)).replace('/','\\')
        assert sha_bytes(data)==manifest[key],('Non-production source',name)
        original[name]=data
    before=original['NativeSceneActivity.as'].decode('utf-8-sig')
    changes=[]
    def replace(source,old,new):
        assert source.count(old)==1,(old[:90],source.count(old))
        changes.append((old,new));return source.replace(old,new,1)
    source=before
    source=replace(source,'            var threats:Array=[];',
        '            telemetryStart(s,w,left,top,right,bottom);\n            var threats:Array=[];')
    old='''                    t:Math.min(p.Y,p.Y+p.dy*4)-radius,b:Math.max(p.Y,p.Y+p.dy*4)+radius});'''
    source=replace(source,old,old+'''
                telemetryThreat(s,p,threats[threats.length-1]);''')
    old='''                if(u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0)r.engaged=true;'''
    source=replace(source,old,'''                var diagWasAsleep:Boolean=Boolean(s.sleeping[u]);
                if(!r.engaged && (u.hp<r.hp || u.celUnit!=null || u.cut>0 || u.poison>0))
                    telemetryEngaged(s,u,r,u.hp<r.hp,u.celUnit!=null,u.cut>0,u.poison>0);
'''+old)
    old='''                if(!active)for each(var threat:Object in threats)
                    if(u.X>=threat.l && u.X<=threat.r && u.Y>=threat.t && u.Y-u.scY<=threat.b){active=true;break;}
                if(active)r.until=s.tick+45;
                active=active || s.tick<r.until;'''
    source=replace(source,old,'''                var diagBase:Boolean=active;
                var diagMatched:Object=null;
                if(!active)for each(var threat:Object in threats)
                    if(u.X>=threat.l && u.X<=threat.r && u.Y>=threat.t && u.Y-u.scY<=threat.b){active=true;diagMatched=threat;break;}
                var diagGrace:Boolean=!active && s.tick<r.until;
                if(active)r.until=s.tick+45;
                active=active || s.tick<r.until;
                telemetryUnit(s,w,loc,u,r,diagWasAsleep,diagBase,diagMatched,diagGrace,active,left,top,right,bottom);''')
    source=replace(source,'            return s.sleeping;','            telemetryFinish(s);\n            return s.sleeping;')
    old='''            if(r){r.engaged=true;resume(r);}
            delete s.sleeping[u];'''
    source=replace(source,old,'''            var diagAsleep:Boolean=Boolean(s.sleeping[u]);
            var diagEngaged:Boolean=r && r.engaged;
'''+old+'''
            telemetryWake(s,u,r,diagAsleep,diagEngaged);''')
    old='''        public static function stats():Object {return current?{awake:current.awake,asleep:current.asleep}:null;}'''
    source=replace(source,old,HELPERS+STATS)
    reversed_source=source
    for old,new in reversed(changes):
        assert reversed_source.count(new)==1
        reversed_source=reversed_source.replace(new,old,1)
    assert reversed_source==before,'Telemetry removal did not reproduce original source'
    for directory in ['original-source','source']:(OUT/directory).mkdir(parents=True,exist_ok=True)
    for name,data in original.items():
        for directory in ['original-source','source']:(OUT/directory/name).write_bytes(data)
    (OUT/'source/NativeSceneActivity.as').write_text(source,encoding='utf-8',newline='')
    data=dict(version='activity-telemetry-source-1',diagnosticOnly=True,performanceAcceptance=False,
        compiled=False,deployed=False,baseline=BASE_SHA,host=HOST_SHA,
        productionReceiptSHA256=sha(receipt_path),productionSourceManifestSHA256=sha(manifest_path),
        builderSHA256=sha(__file__),sourceClosure=FILES,
        before={n:sha(OUT/'original-source'/n) for n in FILES},
        after={n:sha(OUT/'source'/n) for n in FILES},
        changed=['NativeSceneActivity.as'],reverseInsertionCheck=True,
        algorithm='Original active expression, threat bounds, 45-frame grace, engaged latch and wake scheduling preserved',
        limitations=['Diagnostic logging adds overhead; not eligible for performance acceptance.',
            'Current-frame awake/asleep counters deliberately keep original behavior; asynchronous wake calls update the dictionary but not those counters.',
            'Only the six manifest-verified production classes are copied; no source-only alicorn, test source, or other module HEAD is included.'])
    (OUT/'source-provenance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False),flush=True)

if __name__=='__main__':prepare()
