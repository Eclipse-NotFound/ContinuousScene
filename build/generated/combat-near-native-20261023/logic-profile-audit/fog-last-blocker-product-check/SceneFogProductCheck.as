package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Component-only: retained BEFC legacy branch versus the host typed branch.
     * No last-blocker switch/counters; first qualify this exact probe on BEFC.
     */
    public class SceneFogProductCheck {
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
        public static function run(w:*):Object {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)
                throw new Error("Fog production component requires an owned motion instance");
            var main:* =w.main;
            var carrier:* =main.getChildByName("ContinuousSceneCarrier");
            var api:Object=carrier ? carrier["nativeAPI"] : null;
            if(!api)throw new Error("Native API missing");
            if(api.hasOwnProperty("fogLastBlockerEnabled") || api.hasOwnProperty("fogLastBlockerProfile"))
                throw new Error("Instrumented last-blocker API is not a production component host");
            var loc:* =w.loc;var graph:* =w.grafon;var gg:* =w.gg;
            var bitmap:BitmapData=graph.lightBmp;
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class;
            var saved:Array=[];var columns:Array=[];var cases:Array=[];
            var base:BitmapData=null;var expected:BitmapData=null;
            var oldActive:Boolean=loc.active;var oldDark:Boolean=loc.retDark;
            var oldRelight:int=loc.relight_t;var oldWater:Number=loc.opacWater;
            var oldLarge:Boolean=graph.sceneLarge;var oldSpace:* =loc.space;
            var oldSX:int=loc.spaceX;var oldSY:int=loc.spaceY;
            var oldDist1:int=loc.lDist1;var oldDist2:int=loc.lDist2;
            var oldTileX:int=Tile.tileX;var oldTileY:int=Tile.tileY;
            var oldPlayer:Array=[gg.X,gg.Y1,gg.storona,gg.stayY];
            var outside:* =loc.otstoy;
            var outsideState:Array=[outside.visi,outside.t_visi,outside.opac,outside.water];
            var hadTyped:Boolean=api.hasOwnProperty("fogTypedEnabled");var oldTyped:* =api["fogTypedEnabled"];
            var hadBounds:Boolean=api.hasOwnProperty("fogBoundsEnabled");var oldBounds:* =api["fogBoundsEnabled"];
            var result:Object={version:"fog-production-legacy-check-1",valid:false,equal:false,restored:false,
                cases:[],tileCount:0,positiveOpaque:false,positiveWater:false,legacyCovered:0,inactiveCovered:false,
                negativeCovered:0,weakWaterCovered:false,sceneFlagBypassCovered:0,simulationFramesAdvanced:0,
                cacheHitsMeasured:false,reference:"retained BEFC dynamic-type legacy branch; not vanilla 1.02",
                pixels:"exact native lightBmp",performanceEligible:false,
                coverage:"Prior diagnostic hit fixtures plus audited production control flow; no production hit counter"};
            var x:int;var y:int;var tile:*;var item:Array;var spec:Object;
            try {
                if(!(loc.space is Array) || !(loc.spaceX>48 || loc.spaceY>25) || !oldLarge || !bitmap || !Tile)
                    throw new Error("Fog production component requires the complete large native grid");
                for(x=0;x<loc.spaceX;++x) {
                    if(!(loc.space[x] is Array))throw new Error("Native column is not Array");
                    columns.push(loc.space[x]);
                    for(y=0;y<loc.spaceY;++y) {
                        tile=loc.space[x][y];
                        if(!tile || getQualifiedClassName(tile)!="fe.loc::Tile")throw new Error("Native cell is not Tile");
                        saved.push([tile,Number(tile.visi),Number(tile.t_visi),Number(tile.opac),int(tile.water),x,y]);
                    }
                }
                result.tileCount=saved.length;base=bitmap.clone();
                result.geometry={spaceX:oldSX,spaceY:oldSY,tileX:oldTileX,tileY:oldTileY,
                    bitmapWidth:bitmap.width,bitmapHeight:bitmap.height,lDist1:oldDist1,lDist2:oldDist2,
                    sceneLarge:oldLarge,limX:loc.limX,limY:loc.limY};
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
                // Only the flag changes in these two component calls. This is
                // not a normal-room entry/gameplay or topology conversion test.
                for each(terrain in ["opaque","water"])
                    cases.push({name:"scene-flag-false-"+terrain,args:[cx*Tile.tileX,cy*Tile.tileY,600,1000],
                        dark:false,pattern:"low",terrain:terrain,active:true,bounds:true,cx:cx,cy:cy,
                        positive:true,sceneFlagFalse:true});
                var allEqual:Boolean=true;
                for each(spec in cases) {
                    graph.sceneLarge=spec.sceneFlagFalse===true?false:oldLarge;
                    api["fogBoundsEnabled"]=spec.bounds;
                    applyState(saved,loc,spec,oldWater);bitmap.copyPixels(base,base.rect,new Point());loc.relight_t=oldRelight;
                    var initial:Array=[];
                    for each(item in saved)initial.push(Number(item[0].visi),Number(item[0].t_visi));
                    api["fogTypedEnabled"]=false;
                    loc.lighting(spec.args[0],spec.args[1],spec.args[2],spec.args[3]);
                    if(api["fogTypedEnabled"]!==false)throw new Error("Legacy selector changed");
                    var values:Array=[];var changedTiles:int=0;var pos:int=0;
                    var expectedRelight:int=loc.relight_t;var expectedActive:Boolean=loc.active;
                    expected=bitmap.clone();
                    for each(item in saved) {
                        values.push(Number(item[0].visi),Number(item[0].t_visi));
                        if(!sameNumber(item[0].visi,initial[pos]) || !sameNumber(item[0].t_visi,initial[pos+1]))++changedTiles;
                        pos+=2;
                    }
                    applyState(saved,loc,spec,oldWater);bitmap.copyPixels(base,base.rect,new Point());loc.relight_t=oldRelight;
                    var identicalInputs:Boolean=pixels(bitmap,base);pos=0;
                    for each(item in saved) {
                        if(!sameNumber(item[0].visi,initial[pos]) || !sameNumber(item[0].t_visi,initial[pos+1]))identicalInputs=false;
                        pos+=2;
                    }
                    var candidateTyped:Boolean=spec.typed!==false;
                    api["fogTypedEnabled"]=candidateTyped;
                    loc.lighting(spec.args[0],spec.args[1],spec.args[2],spec.args[3]);
                    if(api["fogTypedEnabled"]!==candidateTyped)throw new Error("Typed selector changed");
                    var equalTiles:Boolean=true;var identity:Boolean=true;pos=0;
                    for each(item in saved) {
                        if(!sameNumber(item[0].visi,values[pos]) || !sameNumber(item[0].t_visi,values[pos+1]))equalTiles=false;
                        if(loc.space[item[5]][item[6]]!==item[0])identity=false;
                        pos+=2;
                    }
                    for(x=0;x<oldSX;++x)if(loc.space[x]!==columns[x])identity=false;
                    var pixelEqual:Boolean=pixels(bitmap,expected);
                    var originX:int=int(spec.args[0]);var originY:int=int(spec.args[1]);
                    if(originX==-10000) {originX=gg.X+gg.storona*12;originY=gg.Y1+gg.stayY*.247;}
                    var eligibility:Boolean=candidateTyped && spec.active && graph.sceneLarge && spec.bounds && !spec.dark &&
                        (oldSX>48 || oldSY>25) && originX>=0 && originY>=0 && originX<oldSX*Tile.tileX && originY<oldSY*Tile.tileY;
                    var stateEqual:Boolean=loc.relight_t==expectedRelight && loc.active==expectedActive &&
                        loc.retDark==spec.dark && sameNumber(loc.opacWater,spec.terrain=="water"?1:spec.terrain=="weak-water"?.5:oldWater) &&
                        graph.sceneLarge===(spec.sceneFlagFalse===true?false:oldLarge) &&
                        api["fogBoundsEnabled"]===spec.bounds;
                    identity=identity && w.loc===loc && w.grafon===graph && w.gg===gg && w.main===main &&
                        loc.grafon===graph && loc.gg===gg && loc.space===oldSpace && graph.lightBmp===bitmap &&
                        main.getChildByName("ContinuousSceneCarrier")===carrier && carrier["nativeAPI"]===api &&
                        loc.spaceX==oldSX && loc.spaceY==oldSY && loc.lDist1==oldDist1 && loc.lDist2==oldDist2 &&
                        Tile.tileX==oldTileX && Tile.tileY==oldTileY && gg.X===oldPlayer[0] && gg.Y1===oldPlayer[1] &&
                        gg.storona===oldPlayer[2] && gg.stayY===oldPlayer[3] && loc.otstoy===outside &&
                        sameNumber(outside.visi,outsideState[0]) && sameNumber(outside.t_visi,outsideState[1]) &&
                        sameNumber(outside.opac,outsideState[2]) && outside.water===outsideState[3];
                    var positive:Boolean=(!spec.positive && spec.typed!==false && !spec.weakWater) || changedTiles>0;
                    var noDiagnostic:Boolean=!api.hasOwnProperty("fogLastBlockerEnabled") && !api.hasOwnProperty("fogLastBlockerProfile");
                    var ok:Boolean=equalTiles && pixelEqual && stateEqual && identity && positive && noDiagnostic && identicalInputs;
                    if(spec.typed===false && ok)++result.legacyCovered;
                    if(!spec.active && ok)result.inactiveCovered=true;
                    if(spec.positive && ok) {if(spec.terrain=="opaque")result.positiveOpaque=true;else result.positiveWater=true;}
                    if(spec.negative && ok)++result.negativeCovered;
                    if(spec.weakWater && ok)result.weakWaterCovered=true;
                    if(spec.sceneFlagFalse && ok && !eligibility)++result.sceneFlagBypassCovered;
                    result.cases.push({name:spec.name,args:spec.args,dark:spec.dark,pattern:spec.pattern,terrain:spec.terrain,
                        equal:ok,tilesEqual:equalTiles,pixelsEqual:pixelEqual,stateEqual:stateEqual,identityPreserved:identity,
                        referenceTyped:false,candidateTyped:candidateTyped,bounds:spec.bounds,active:spec.active,identicalArmInputs:identicalInputs,
                        sceneLarge:graph.sceneLarge,expectedLastBlockerEligibility:eligibility,
                        resolvedOrigin:{x:originX,y:originY},changedTiles:changedTiles,positiveChange:positive,
                        noDiagnosticAPI:noDiagnostic,cacheHitsMeasured:false,
                        sceneFlagOnlyBypass:spec.sceneFlagFalse===true});
                    allEqual=allEqual && ok;expected.dispose();expected=null;
                }
                result.equal=allEqual && result.legacyCovered==2 && result.inactiveCovered && result.negativeCovered==2 &&
                    result.positiveOpaque && result.positiveWater && result.weakWaterCovered && result.sceneFlagBypassCovered==2;
                result.valid=true;
            } catch(error:*) {result.error=String(error);}
            finally {
                try {
                    restoreTiles(saved);loc.active=oldActive;loc.retDark=oldDark;loc.relight_t=oldRelight;loc.opacWater=oldWater;
                    graph.sceneLarge=oldLarge;
                    outside.visi=outsideState[0];outside.t_visi=outsideState[1];outside.opac=outsideState[2];outside.water=outsideState[3];
                    if(base)bitmap.copyPixels(base,base.rect,new Point());
                    if(hadTyped)api["fogTypedEnabled"]=oldTyped;else delete api["fogTypedEnabled"];
                    if(hadBounds)api["fogBoundsEnabled"]=oldBounds;else delete api["fogBoundsEnabled"];
                    var restored:Boolean=loc.active==oldActive && loc.retDark==oldDark && loc.relight_t==oldRelight &&
                        sameNumber(loc.opacWater,oldWater) && graph.sceneLarge===oldLarge && w.loc===loc && w.grafon===graph &&
                        graph.lightBmp===bitmap && loc.space===oldSpace && w.gg===gg && loc.otstoy===outside &&
                        (base==null || pixels(bitmap,base)) && api.hasOwnProperty("fogTypedEnabled")==hadTyped &&
                        api.hasOwnProperty("fogBoundsEnabled")==hadBounds && (!hadTyped || api["fogTypedEnabled"]===oldTyped) &&
                        (!hadBounds || api["fogBoundsEnabled"]===oldBounds) &&
                        !api.hasOwnProperty("fogLastBlockerEnabled") && !api.hasOwnProperty("fogLastBlockerProfile");
                    for each(item in saved)if(loc.space[item[5]][item[6]]!==item[0] || !sameNumber(item[0].visi,item[1]) ||
                        !sameNumber(item[0].t_visi,item[2]) || !sameNumber(item[0].opac,item[3]) || item[0].water!==item[4])restored=false;
                    for(x=0;x<columns.length;++x)if(loc.space[x]!==columns[x])restored=false;
                    result.restored=restored;
                } catch(restoreError:*) {result.restoreError=String(restoreError);result.valid=false;}
                if(expected)expected.dispose();if(base)base.dispose();
            }
            return result;
        }
    }
}
