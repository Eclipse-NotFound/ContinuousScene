package tests {
    import flash.display.DisplayObject;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Diagnostic only: call after native logic, before the next render.
     * Both control arms enumerate the live chain. Only current Bullet visuals
     * are changed; weapon configuration, physics, alpha, masks and filters are
     * untouched. This deliberately changes appearance and is not a release fix.
     */
    public class SceneBulletBlendProbe {
        private var bulletClass:Class;
        private var world:*;
        private var location:*;
        private var records:Dictionary=new Dictionary();
        private var observed:Dictionary=new Dictionary(true);
        private var excluded:Dictionary=new Dictionary(true);
        private var epoch:int=0;
        private var updates:int=0;
        private var enabledUpdates:int=0;
        private var instances:int=0;
        private var changed:int=0;
        private var restored:int=0;
        private var retired:int=0;
        private var replacements:int=0;
        private var conflictCount:int=0;
        private var errorCount:int=0;
        private var currentBullets:int=0;
        private var currentVisuals:int=0;
        private var currentNonNormal:int=0;
        private var currentControlled:int=0;
        private var currentChainNodes:int=0;
        private var lastEnabled:Boolean=false;
        private var conflicts:Array=[];
        private var errors:Array=[];
        private var originalModes:Object={};

        public function update(w:*,enabled:Boolean):void {
            ++updates;++epoch;
            if(enabled)++enabledUpdates;
            lastEnabled=enabled;
            currentBullets=currentVisuals=currentNonNormal=currentControlled=currentChainNodes=0;
            try {
                if(!w || !w.loc) {restoreAll("no-location");world=null;location=null;return;}
                if(world!==w || location!==w.loc) {
                    restoreAll("location-change");world=w;location=w.loc;
                }
                if(!enabled)restoreAll("control-window");
                if(!bulletClass)bulletClass=getDefinitionByName("fe.weapon.Bullet") as Class;
                if(!bulletClass)throw new Error("Native Bullet class unavailable");
                var seen:Dictionary=new Dictionary(true);
                for(var bullet:*=location.firstObj;bullet;bullet=bullet.nobj) {
                    ++currentChainNodes;
                    if(!(bullet is bulletClass))continue;
                    ++currentBullets;
                    var visual:DisplayObject=bullet.vis as DisplayObject;
                    if(!visual)continue;
                    ++currentVisuals;
                    if(!observed[visual]) {observed[visual]=true;++instances;}
                    if(seen[visual]) {
                        conflict(visual,"shared-visual-in-live-chain",null);
                        var shared:Object=records[visual];
                        if(shared && restoreRecord(shared,"shared-visual"))delete records[visual];
                        continue;
                    }
                    seen[visual]=true;
                    var record:Object=records[visual];
                    if(record && (record.world!==w || record.location!==location || record.bullet!==bullet)) {
                        ++replacements;
                        if(!restoreRecord(record,"identity-change"))continue;
                        delete records[visual];record=null;
                    }
                    if(record && visual.blendMode!="normal") {
                        conflict(visual,"external-blend-change",record);
                        delete records[visual];record=null;
                    }
                    var mode:String=record?String(record.original):visual.blendMode;
                    if(mode!="normal")++currentNonNormal;
                    if(!enabled || excluded[visual])continue;
                    if(!record && mode!="normal") {
                        record={world:w,location:location,bullet:bullet,visual:visual,
                            parentAtClaim:visual.parent,original:mode,seen:epoch,applied:false};
                        // Save the restoration record before the only display write.
                        records[visual]=record;
                        visual.blendMode="normal";record.applied=true;
                        ++changed;originalModes[mode]=int(originalModes[mode])+1;
                    }
                    if(record)record.seen=epoch;
                }
                var stale:Array=[];
                for each(record in records) {
                    if(record.seen!=epoch)stale.push(record);
                    else ++currentControlled;
                }
                for each(record in stale) {
                    ++retired;
                    if(record.bullet && record.bullet.vis!==record.visual)++replacements;
                    if(restoreRecord(record,"destroyed-or-visual-replaced"))delete records[record.visual];
                }
            } catch(error:Error) {
                fail("update",error);
                restoreAll("update-error");
            }
        }

        public function clear():void {
            restoreAll("clear");
            world=null;location=null;lastEnabled=false;
            currentBullets=currentVisuals=currentNonNormal=currentControlled=currentChainNodes=0;
        }

        public function snapshot():Object {
            var pending:int=0;
            for each(var record:Object in records)if(record.applied)++pending;
            return {version:"bullet-blend-diagnostic-1",diagnosticOnly:true,performanceAcceptance:false,
                valid:conflictCount==0 && errorCount==0,enabled:lastEnabled,
                updates:updates,enabledUpdates:enabledUpdates,instances:instances,
                changed:changed,restored:restored,retired:retired,replacements:replacements,
                currentBullets:currentBullets,currentVisuals:currentVisuals,
                currentNonNormal:currentNonNormal,currentControlled:currentControlled,
                currentChainNodes:currentChainNodes,pendingRestore:pending,
                conflicts:conflictCount,errors:errorCount,conflictDetails:conflicts.concat(),
                errorDetails:errors.concat(),originalModes:copyModes(),
                limitations:[
                    "Only Bullet.vis root blendMode is changed; nested artwork, particles and other effects are excluded.",
                    "Sampling after native logic captures the weapon's final birth blend assignment; later callbacks may still create or alter visuals.",
                    "External writes that leave the expected normal value unchanged cannot be detected.",
                    "A timing difference does not establish parent-sized intermediate render targets."
                ]};
        }

        private function restoreAll(reason:String):void {
            var pending:Array=[];
            for each(var record:Object in records)pending.push(record);
            for each(record in pending) {
                if(restoreRecord(record,reason))delete records[record.visual];
            }
            currentControlled=0;
        }

        private function restoreRecord(record:Object,reason:String):Boolean {
            if(!record.applied)return true;
            var visual:DisplayObject=record.visual as DisplayObject;
            try {
                if(visual.blendMode=="normal") {
                    visual.blendMode=record.original;++restored;
                } else conflict(visual,"restore-observed-external-blend:"+reason,record);
                record.applied=false;
                return true;
            } catch(error:Error) {fail("restore:"+reason,error);}
            return false;
        }

        private function conflict(visual:DisplayObject,reason:String,record:Object):void {
            ++conflictCount;excluded[visual]=true;
            if(conflicts.length<80)conflicts.push({reason:reason,visualClass:getQualifiedClassName(visual),
                original:record?record.original:null,observed:visual.blendMode,update:updates});
        }
        private function fail(where:String,error:Error):void {
            ++errorCount;if(errors.length<40)errors.push({where:where,message:error.message,update:updates});
        }
        private function copyModes():Object {
            var result:Object={};for(var key:String in originalModes)result[key]=originalModes[key];return result;
        }
    }
}
