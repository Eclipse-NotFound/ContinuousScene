package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Owned-instance, same-state component check; timing never forces lighting. */
    public class SceneFogLastBlockerProbe {
        private static const VERSION:String="fog-last-blocker-1";
        private static const SWITCH:String="fogLastBlockerEnabled";
        private static const PROFILE:String="fogLastBlockerProfile";
        private static const FIELDS:Array=["startedCalls","calls","enabledCalls","disabledCalls","eligibleCalls",
            "fallbackCalls","rayCandidates","eligibleRays","cacheProbes","cacheHits","cacheUpdates","nativeRays",
            "ordinarySteps","totalMs","maxMs"];
        private var world:*;
        private var api:Object;
        private var current:Object;
        private var oldSwitch:*;
        private var oldProfile:*;
        private var hadSwitch:Boolean;
        private var hadProfile:Boolean;
        private var enabled:Boolean=false;

        public function bind(w:*):void {
            if(api) {same(w);return;}
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)
                throw new Error("Fog last-blocker check requires an owned motion instance");
            var carrier:* =w.main.getChildByName("ContinuousSceneCarrier");
            if(!carrier || !carrier["nativeAPI"])throw new Error("Fog last-blocker native API missing");
            world=w;api=carrier["nativeAPI"];
            if(api["fogTypedEnabled"]===false || api["fogBoundsEnabled"]===false)
                throw new Error("Fog last-blocker timing requires the formal typed and bounded paths");
            hadSwitch=api.hasOwnProperty(SWITCH);oldSwitch=api[SWITCH];
            hadProfile=api.hasOwnProperty(PROFILE);oldProfile=api[PROFILE];
            begin(false);
        }
        private function same(w:*):void {
            var carrier:* =w.main.getChildByName("ContinuousSceneCarrier");
            if(w!==world || !carrier || carrier["nativeAPI"]!==api || api[PROFILE]!==current || api[SWITCH]!==enabled)
                throw new Error("Fog last-blocker diagnostic state changed externally");
        }
        public function begin(value:Boolean):Object {
            if(!api)throw new Error("Fog last-blocker diagnostic not bound");
            if(current)same(world);
            enabled=value;current={};api[SWITCH]=enabled;api[PROFILE]=current;
            return snapshot();
        }
        public function snapshot():Object {
            same(world);
            var initialized:Boolean="version" in current;
            if(initialized && (current.version!==VERSION || current.diagnosticOnly!==true || current.performanceEligible!==false))
                throw new Error("Fog last-blocker host counters have wrong schema");
            var result:Object={version:VERSION,enabled:enabled,initialized:initialized};
            for each(var key:String in FIELDS) {
                var value:Number=initialized?Number(current[key]):0;
                if(!isFinite(value) || value<0)throw new Error("Invalid fog last-blocker counter: "+key);
                result[key]=value;
            }
            if(result.calls!=result.startedCalls || result.calls!=result.enabledCalls+result.disabledCalls ||
                result.enabledCalls!=result.eligibleCalls+result.fallbackCalls ||
                result.rayCandidates!=result.cacheHits+result.nativeRays ||
                result.cacheHits>result.cacheProbes || result.cacheProbes>result.eligibleRays ||
                result.eligibleRays>result.rayCandidates || result.cacheUpdates>result.nativeRays ||
                (enabled?result.disabledCalls:result.enabledCalls)!=0 ||
                (!enabled && (result.eligibleRays!=0 || result.cacheProbes!=0 || result.cacheHits!=0 || result.cacheUpdates!=0)))
                throw new Error("Fog last-blocker counters or branch mismatch");
            if(initialized)result.last={enabled:current.lastEnabled,eligible:current.lastEligible,
                rays:current.lastRayCandidates,eligibleRays:current.lastEligibleRays,probes:current.lastCacheProbes,
                hits:current.lastCacheHits,updates:current.lastCacheUpdates,nativeRays:current.lastNativeRays,
                ordinarySteps:current.lastOrdinarySteps};
            return result;
        }
        public function clear():Object {
            if(!api)return {restored:true,bound:false};
            same(world);
            if(hadSwitch)api[SWITCH]=oldSwitch;else delete api[SWITCH];
            if(hadProfile)api[PROFILE]=oldProfile;else delete api[PROFILE];
            var ok:Boolean=api.hasOwnProperty(SWITCH)==hadSwitch && api.hasOwnProperty(PROFILE)==hadProfile &&
                (!hadSwitch || api[SWITCH]===oldSwitch) && (!hadProfile || api[PROFILE]===oldProfile);
            var result:Object={restored:ok,bound:true,hadSwitch:hadSwitch,hadProfile:hadProfile};
            api=null;world=null;current=null;oldSwitch=null;oldProfile=null;
            if(!ok)throw new Error("Fog last-blocker cleanup failed");
            return result;
        }
        private static function sameNumber(a:Number,b:Number):Boolean {return a===b || isNaN(a) && isNaN(b);}
        private static function pixels(a:BitmapData,b:BitmapData):Boolean {
            var difference:* =a.compare(b);
            var equal:Boolean=difference===0;
            if(difference is BitmapData)difference.dispose();
            return equal;
        }
        private static function restoreTiles(saved:Array):void {
            for each(var item:Array in saved) {
                item[0].visi=item[1];item[0].t_visi=item[2];item[0].opac=item[3];item[0].water=item[4];
            }
        }
        private static function applyState(saved:Array,loc:*,spec:Object,water:Number):void {
            restoreTiles(saved);loc.retDark=spec.dark;loc.active=spec.active;
            loc.opacWater=spec.terrain=="water"?1:spec.terrain=="weak-water"?.5:water;
            for each(var item:Array in saved) {
                if(spec.pattern=="low") {item[0].visi=0;item[0].t_visi=0;}
                else if(spec.pattern=="near-one") {item[0].visi=.99;item[0].t_visi=.2;}
                else if(spec.pattern=="negative-low") {item[0].visi=-.5;item[0].t_visi=-.5;}
                else if(spec.pattern=="negative-near") {item[0].visi=-.005;item[0].t_visi=-.005;}
                if(spec.terrain!="native") {
                    item[0].opac=0;item[0].water=0;
                    if(item[5]>=spec.cx-9 && item[5]<=spec.cx+9 && item[6]>=spec.cy-9 && item[6]<=spec.cy+9 &&
                        item[5]%3==0 && item[6]%3==0 && (item[5]!=spec.cx || item[6]!=spec.cy)) {
                        if(spec.terrain=="water" || spec.terrain=="weak-water")item[0].water=1;else item[0].opac=1;
                    }
                }
            }
        }
        public function verify(w:*):Object {
            same(w);
            var loc:* =w.loc;
            var bitmap:BitmapData=w.grafon.lightBmp;
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class;
            var saved:Array=[];var cases:Array=[];
            var base:BitmapData=null;var expected:BitmapData=null;
            var oldActive:Boolean=loc.active;var oldDark:Boolean=loc.retDark;
            var oldRelight:int=loc.relight_t;var oldWater:Number=loc.opacWater;
            var beforeProfile:Object=current;var beforeEnabled:Boolean=enabled;
            var hadTyped:Boolean=api.hasOwnProperty("fogTypedEnabled");var oldTyped:* =api["fogTypedEnabled"];
            var hadBounds:Boolean=api.hasOwnProperty("fogBoundsEnabled");var oldBounds:* =api["fogBoundsEnabled"];
            var result:Object={version:"fog-last-blocker-same-state-1",valid:false,equal:false,restored:false,
                cases:[],tileCount:0,positiveOpaque:false,positiveWater:false,legacyCovered:0,inactiveCovered:false,
                negativeCovered:0,weakWaterCovered:false,simulationFramesAdvanced:0,
                pixels:"exact native lightBmp",performanceEligible:false};
            var x:int;var y:int;var tile:*;var item:Array;var spec:Object;
            try {
                if(!(loc.space is Array) || !(loc.spaceX>48 || loc.spaceY>25) || !bitmap || !Tile)
                    throw new Error("Fog last-blocker positive coverage needs a complete large native grid");
                for(x=0;x<loc.spaceX;++x) {
                    if(!(loc.space[x] is Array))throw new Error("Native column is not Array");
                    for(y=0;y<loc.spaceY;++y) {
                        tile=loc.space[x][y];
                        if(!tile || getQualifiedClassName(tile)!="fe.loc::Tile")throw new Error("Native cell is not Tile");
                        saved.push([tile,Number(tile.visi),Number(tile.t_visi),Number(tile.opac),int(tile.water),x,y]);
                    }
                }
                result.tileCount=saved.length;base=bitmap.clone();
                var targets:Array=[[-10000,-10000,-1,-1],[w.gg.X,w.gg.Y,300,1000],[0,0,0,80],
                    [loc.limX-1,loc.limY-1,100,2000],[1920,4000,300,1000],[-100,200,100,300],
                    [loc.limX+200,loc.limY+200,100,300],[w.gg.X,w.gg.Y,0,0],
                    [w.gg.X,w.gg.Y,600,2000],[w.gg.X+40,w.gg.Y,600,2000],
                    [w.gg.X-40,w.gg.Y-40,600,2000],[w.gg.X,w.gg.Y,2000,2000],[w.gg.X,w.gg.Y,3000,2000]];
                var patterns:Array=["current","low","near-one"];
                for(var dark:int=0;dark<2;++dark)for each(var pattern:String in patterns)
                    for(var n:int=0;n<targets.length;++n)
                        cases.push({name:"native-"+dark+"-"+pattern+"-"+n,args:targets[n],dark:dark==1,
                            pattern:pattern,terrain:"native",active:true,bounds:true});
                var cx:int=int(loc.spaceX/2);var cy:int=int(loc.spaceY/2);
                if(cx<10 || cy<10)throw new Error("Sparse opacity coverage needs 20 cells in both dimensions");
                for each(var terrain:String in ["opaque","water"])
                    for each(pattern in ["low","near-one"])
                        cases.push({name:"sparse-"+terrain+"-"+pattern,args:[cx*Tile.tileX,cy*Tile.tileY,600,1000],
                            dark:false,pattern:pattern,terrain:terrain,active:true,bounds:true,cx:cx,cy:cy,positive:pattern=="low"});
                cases.push({name:"bounds-disabled",args:[w.gg.X,w.gg.Y,600,2000],dark:false,
                    pattern:"low",terrain:"native",active:true,bounds:false});
                cases.push({name:"inactive",args:[w.gg.X,w.gg.Y,600,2000],dark:false,
                    pattern:"low",terrain:"native",active:false,bounds:true});
                for(var legacyDark:int=0;legacyDark<2;++legacyDark)
                    cases.push({name:"legacy-"+legacyDark,args:[w.gg.X,w.gg.Y,600,2000],dark:legacyDark==1,
                        pattern:"low",terrain:"native",active:true,bounds:true,typed:false});
                // Append only: the original 86 cases and their order remain.
                for each(pattern in ["negative-low","negative-near"])
                    cases.push({name:"sparse-opaque-"+pattern,args:[cx*Tile.tileX,cy*Tile.tileY,600,1000],
                        dark:false,pattern:pattern,terrain:"opaque",active:true,bounds:true,cx:cx,cy:cy,positive:true,negative:true});
                cases.push({name:"sparse-weak-water-low",args:[cx*Tile.tileX,cy*Tile.tileY,600,1000],
                    dark:false,pattern:"low",terrain:"weak-water",active:true,bounds:true,cx:cx,cy:cy,weakWater:true});
                var allEqual:Boolean=true;
                for each(spec in cases) {
                    api["fogTypedEnabled"]=spec.typed!==false;
                    api["fogBoundsEnabled"]=spec.bounds;
                    applyState(saved,loc,spec,oldWater);bitmap.copyPixels(base,base.rect,new Point());loc.relight_t=oldRelight;
                    begin(false);loc.lighting(spec.args[0],spec.args[1],spec.args[2],spec.args[3]);
                    var a:Object=snapshot();var values:Array=[];
                    var expectedRelight:int=loc.relight_t;var expectedActive:Boolean=loc.active;
                    expected=bitmap.clone();
                    var expectedLowChanges:int=0;
                    for each(item in saved) {
                        values.push(Number(item[0].visi),Number(item[0].t_visi));
                        if(spec.pattern=="low" && (Number(item[0].visi)!=0 || Number(item[0].t_visi)!=0))++expectedLowChanges;
                    }
                    applyState(saved,loc,spec,oldWater);bitmap.copyPixels(base,base.rect,new Point());loc.relight_t=oldRelight;
                    begin(true);loc.lighting(spec.args[0],spec.args[1],spec.args[2],spec.args[3]);
                    var b:Object=snapshot();var equalTiles:Boolean=true;var pos:int=0;
                    for each(item in saved) {
                        if(!sameNumber(item[0].visi,values[pos]) || !sameNumber(item[0].t_visi,values[pos+1]))equalTiles=false;
                        pos+=2;
                    }
                    var pixelEqual:Boolean=pixels(bitmap,expected);
                    var counters:Boolean=a.calls==(spec.active && spec.typed!==false?1:0) && b.calls==a.calls;
                    var originX:int=int(spec.args[0]);var originY:int=int(spec.args[1]);
                    if(originX==-10000) {
                        originX=w.gg.X+w.gg.storona*12;originY=w.gg.Y1+w.gg.stayY*.247;
                    }
                    var typedActive:Boolean=spec.active && spec.typed!==false;
                    var expectedEligible:Boolean=typedActive && spec.bounds && !spec.dark &&
                        originX>=0 && originY>=0 && originX<loc.spaceX*Tile.tileX && originY<loc.spaceY*Tile.tileY;
                    var fallback:Boolean=b.eligibleCalls==(expectedEligible?1:0) &&
                        b.fallbackCalls==(typedActive && !expectedEligible?1:0) &&
                        (expectedEligible || b.eligibleRays==0 && b.cacheProbes==0 && b.cacheHits==0 && b.cacheUpdates==0);
                    var legacyPositive:Boolean=spec.typed!==false || expectedLowChanges>0;
                    if(spec.typed===false && counters && fallback && legacyPositive)++result.legacyCovered;
                    if(!spec.active && counters && fallback)result.inactiveCovered=true;
                    var stateEqual:Boolean=loc.relight_t==expectedRelight && loc.active==expectedActive &&
                        loc.retDark==spec.dark && sameNumber(loc.opacWater,spec.terrain=="water"?1:spec.terrain=="weak-water"?.5:oldWater);
                    var positive:Boolean=!spec.positive || b.cacheHits>0 && b.cacheUpdates>0 && b.eligibleCalls==1;
                    var weak:Boolean=!spec.weakWater || b.eligibleCalls==1 && b.nativeRays>0 && b.ordinarySteps>0 &&
                        b.cacheUpdates==0 && b.cacheProbes==0 && b.cacheHits==0;
                    if(spec.positive && positive) {
                        if(spec.terrain=="opaque")result.positiveOpaque=true;else result.positiveWater=true;
                    }
                    var ok:Boolean=equalTiles && pixelEqual && stateEqual && counters && positive && fallback && legacyPositive && weak;
                    if(spec.negative && ok)++result.negativeCovered;
                    if(spec.weakWater && ok)result.weakWaterCovered=true;
                    result.cases.push({name:spec.name,args:spec.args,dark:spec.dark,pattern:spec.pattern,terrain:spec.terrain,
                        equal:ok,tilesEqual:equalTiles,pixelsEqual:pixelEqual,stateEqual:stateEqual,actualCoverage:counters,
                        typed:spec.typed!==false,bounds:spec.bounds,active:spec.active,fallbackCoverage:fallback,legacyPositive:legacyPositive,
                        expectedEligible:expectedEligible,resolvedOrigin:{x:originX,y:originY},weakWaterCoverage:weak,
                        requiresNegativeHit:Boolean(spec.negative),negativeCoverage:!spec.negative || ok,
                        changedFromLowTiles:expectedLowChanges,
                        requiresCacheHit:Boolean(spec.positive),positiveCacheHit:positive,original:a,candidate:b});
                    allEqual=allEqual && ok;expected.dispose();expected=null;
                }
                result.equal=allEqual && result.legacyCovered==2 && result.inactiveCovered &&
                    result.negativeCovered==2 && result.weakWaterCovered;result.valid=true;
            } catch(error:*) {result.error=String(error);}
            finally {
                try {
                    restoreTiles(saved);loc.active=oldActive;loc.retDark=oldDark;loc.relight_t=oldRelight;loc.opacWater=oldWater;
                    if(base)bitmap.copyPixels(base,base.rect,new Point());
                    if(hadTyped)api["fogTypedEnabled"]=oldTyped;else delete api["fogTypedEnabled"];
                    if(hadBounds)api["fogBoundsEnabled"]=oldBounds;else delete api["fogBoundsEnabled"];
                    current=beforeProfile;enabled=beforeEnabled;api[PROFILE]=current;api[SWITCH]=enabled;
                    var restored:Boolean=loc.active==oldActive && loc.retDark==oldDark && loc.relight_t==oldRelight &&
                        sameNumber(loc.opacWater,oldWater) && w.loc===loc && w.grafon.lightBmp===bitmap &&
                        (base==null || pixels(bitmap,base)) && api.hasOwnProperty("fogTypedEnabled")==hadTyped &&
                        api.hasOwnProperty("fogBoundsEnabled")==hadBounds && (!hadTyped || api["fogTypedEnabled"]===oldTyped) &&
                        (!hadBounds || api["fogBoundsEnabled"]===oldBounds);
                    for each(item in saved)if(!sameNumber(item[0].visi,item[1]) || !sameNumber(item[0].t_visi,item[2]) ||
                        !sameNumber(item[0].opac,item[3]) || item[0].water!==item[4])restored=false;
                    same(w);result.restored=restored;
                } catch(restoreError:*) {result.restoreError=String(restoreError);result.valid=false;}
                if(expected)expected.dispose();if(base)base.dispose();
            }
            return result;
        }
    }
}
