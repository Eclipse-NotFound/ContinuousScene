package tests {
    import flash.desktop.NativeApplication;
    import flash.system.ApplicationDomain;
    import flash.utils.getQualifiedClassName;

    /** Synchronous terminal component: real Location/Tile, no World.step. */
    public class SceneTdfcLosChecks {
        public static const VERSION:String="tdfc-los-components-1";
        public static const EXPECTED_CASES:int=38;
        private static const FIELDS:Array=["phis","phX1","phX2","phY1","phY2"];
        private static const API_FIELDS:Array=["sceneLosEmptyCacheEnabled","sceneLosEmptyCacheCalls",
            "sceneLosEmptyCacheFallbackCalls","sceneLosEmptyCacheHits","sceneLosEmptyCacheLookups"];
        private static function key(s:String):QName {return new QName("",s);}
        private static function same(a:*,b:*):Boolean {
            return a===b || a is Number && b is Number && isNaN(Number(a)) && isNaN(Number(b));
        }
        private static function counts(api:*):Object {
            return {calls:uint(api[key("sceneLosEmptyCacheCalls")]),fallback:uint(api[key("sceneLosEmptyCacheFallbackCalls")]),
                hits:uint(api[key("sceneLosEmptyCacheHits")]),lookups:uint(api[key("sceneLosEmptyCacheLookups")])};
        }
        private static function state(rows:Array):Array {
            var values:Array=[];
            for each(var row:Object in rows)for each(var field:String in FIELDS)values.push(row.tile[field]);
            return values;
        }
        private static function equalArrays(a:Array,b:Array):Boolean {
            if(a.length!=b.length)return false;
            for(var i:int=0;i<a.length;i++)if(!same(a[i],b[i]))return false;
            return true;
        }
        private static function pair(ctx:Object,name:String,x:Number,y:Number,tx:Number,ty:Number,
            expected:*=null,fallback:Boolean=false,requireHits:Boolean=false):void {
            var api:*=ctx.api, before:Object=counts(api), old:Array=state(ctx.rows);
            api[key("sceneLosEmptyCacheEnabled")]=false;
            var reference:*=api[key("clear")](ctx.loc,x,y,tx,ty);
            api[key("sceneLosEmptyCacheEnabled")]=true;
            var candidate:*=api[key("clear")](ctx.loc,x,y,tx,ty);
            api[key("sceneLosEmptyCacheEnabled")]=false;
            var after:Object=counts(api),delta:Object={calls:after.calls-before.calls,fallback:after.fallback-before.fallback,
                hits:after.hits-before.hits,lookups:after.lookups-before.lookups};
            var unchanged:Boolean=equalArrays(old,state(ctx.rows));
            var good:Boolean=reference is Boolean && candidate is Boolean && reference===candidate
                && (expected===null || reference===expected) && unchanged
                && delta.fallback==(fallback?1:0) && delta.calls==(fallback?0:1)
                && (!requireHits || delta.hits>0);
            ctx.out.cases.push({name:name,passed:good,reference:reference,candidate:candidate,expected:expected,
                input:[String(x),String(y),String(tx),String(ty)],expectedFallback:fallback,
                requireHits:requireHits,delta:delta,tileFieldsUnchanged:unchanged});
            ctx.out.nativeCalls+=2;ctx.out.cacheHits+=delta.hits;
            if(reference===false)ctx.out.blockedCases++;
            if(fallback)ctx.out.fallbackCases++;
        }
        private static function empty(rows:Array):void {
            for each(var row:Object in rows) {
                row.tile.phis=0;row.tile.phX1=row.x*40;row.tile.phX2=(row.x+1)*40;
                row.tile.phY1=row.y*40;row.tile.phY2=(row.y+1)*40;
            }
        }
        public static function run(w:*,check:Function=null):Object {
            var out:Object={version:VERSION,passed:false,terminalOnly:true,performanceEligible:false,
                cases:[],nativeCalls:0,cacheHits:0,blockedCases:0,fallbackCases:0,
                noWorldStep:true,restore:{passed:false},limitations:[
                    "Real native Tile collision fields are temporarily changed; no physics, rendering, RNG, or World.step is invoked during the component.",
                    "Door coverage is a real Tile closed/open/closed collider sequence, not Door animation or interaction coverage.",
                    "The candidate lazily caches host Class references. Those private references persist; terminate this isolated process after restoring public state.",
                    "No elapsed time here qualifies as frame-performance or loading evidence."
                ]};
            var api:*=null,loc:*=null,oldPause:*=null,havePause:Boolean=false;
            var rows:Array=[],columns:Array=[],savedApi:Object={},haveApi:Boolean=false;
            var oldSpace:*=null,oldGG:*=null,oldGrafon:*=null;
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-motion-")!=0)throw new Error("Owned isolated application required");
                if(!w || !w.main || !w.loc || !w.grafon || !w.gg || !w.grafon.sceneLarge)
                    throw new Error("Actual initialized continuous map required");
                var domain:ApplicationDomain=w.main.loaderInfo.applicationDomain;
                var locationClass:Class=domain.getDefinition("fe.loc.Location") as Class;
                var tileClass:Class=domain.getDefinition("fe.loc.Tile") as Class;
                loc=w.loc;oldSpace=loc.space;oldGG=w.gg;oldGrafon=w.grafon;
                if(Object(loc).constructor!==locationClass || tileClass[key("tileX")]!==40 || tileClass[key("tileY")]!==40)
                    throw new Error("Wrong native Location/Tile identity or dimensions");
                var carrier:*=w.main.getChildByName("ContinuousSceneTdfcThreat");
                if(!carrier)throw new Error("Existing TDFC carrier not loaded");
                api=carrier["api"];
                if(api[key("sceneLosEmptyCacheVersion")]!=="tdfc-los-empty-cell-1")throw new Error("Wrong LOS candidate");
                for each(var field:String in API_FIELDS)savedApi[field]=api[key(field)];
                haveApi=true;
                if(savedApi.sceneLosEmptyCacheEnabled!==false)throw new Error("Candidate must enter disabled");
                oldPause=w.onPause;havePause=true;w.onPause=true;
                if(loc.spaceX<16 || loc.spaceY<16)throw new Error("Native fixture rectangle unavailable");
                var bx:int=10,by:int=10,x:Number=bx*40,y:Number=by*40;
                for(var cx:int=bx;cx<bx+5;cx++) {
                    columns.push({x:cx,value:loc.space[cx]});
                    for(var cy:int=by;cy<by+5;cy++) {
                        var tile:*=loc.space[cx][cy];
                        if(tile==null || Object(tile).constructor!==tileClass)throw new Error("Expected actual native Tile");
                        var row:Object={x:cx,y:cy,tile:tile,values:{}};
                        for each(field in FIELDS)row.values[field]=tile[field];
                        rows.push(row);
                    }
                }
                out.identity={applicationID:app,locationClass:getQualifiedClassName(loc),tileClass:getQualifiedClassName(rows[0].tile),
                    actualHostDomain:true,carrierName:carrier.name,nativeTileCount:rows.length,spaceX:loc.spaceX,spaceY:loc.spaceY};
                var ctx:Object={api:api,loc:loc,rows:rows,out:out};
                empty(rows);
                pair(ctx,"empty-horizontal",x+.25,y+100,x+199.75,y+100,true,false,true);
                pair(ctx,"empty-vertical",x+100,y+.25,x+100,y+199.75,true,false,true);
                pair(ctx,"empty-diagonal",x+.25,y+.5,x+199.75,y+199.5,true,false,true);
                pair(ctx,"empty-reverse",x+199.75,y+100,x+.25,y+100,true,false,true);
                pair(ctx,"zero-length",x+80.25,y+80.25,x+80.25,y+80.25,true);
                pair(ctx,"short-line",x+80.25,y+80.25,x+84.25,y+80.25,true);
                for each(var epsilon:Number in [0,.001,.5,.999]) {
                    pair(ctx,"grid-x-"+epsilon,x+39+epsilon,y+100,x+160+epsilon,y+100,true,false,true);
                    pair(ctx,"grid-y-"+epsilon,x+100,y+39+epsilon,x+100,y+160+epsilon,true,false,true);
                }
                var blocker:*=loc.space[bx+2][by+2];blocker.phis=1;
                pair(ctx,"wall-horizontal",x+.25,y+100,x+199.75,y+100,false);
                pair(ctx,"wall-vertical",x+100,y+.25,x+100,y+199.75,false);
                pair(ctx,"wall-diagonal",x+.25,y+.5,x+199.75,y+199.5,false);
                blocker.phY1=y+100;
                pair(ctx,"half-lower-clear",x+.25,y+90,x+199.75,y+90,true,false,true);
                pair(ctx,"half-lower-blocked",x+.25,y+110,x+199.75,y+110,false);
                blocker.phY1=y+80;blocker.phX1=x+100;
                pair(ctx,"half-right-clear",x+90,y+.25,x+90,y+199.75,true,false,true);
                pair(ctx,"half-right-blocked",x+110,y+.25,x+110,y+199.75,false);
                blocker.phis=2;
                pair(ctx,"non-one-phis",x+.25,y+100,x+199.75,y+100,true,false,true);
                blocker.phis=1;blocker.phX1=NaN;
                pair(ctx,"solid-bound-nan-default",x+.25,y+100,x+199.75,y+100,false);
                blocker.phX1=x+80;
                pair(ctx,"door-tile-closed",x+.25,y+100,x+199.75,y+100,false);
                blocker.phis=0;
                pair(ctx,"door-tile-open-next-call",x+.25,y+100,x+199.75,y+100,true,false,true);
                blocker.phis=1;
                pair(ctx,"door-tile-closed-next-call",x+.25,y+100,x+199.75,y+100,false);
                loc.space[bx+2][by+2]=null;
                try {pair(ctx,"null-native-tile",x+.25,y+100,x+199.75,y+100,false);}
                finally {loc.space[bx+2][by+2]=blocker;}
                var savedColumn:*=loc.space[bx+2];loc.space[bx+2]=null;
                try {pair(ctx,"native-tile-lookup-exception",x+.25,y+100,x+199.75,y+100,false);}
                finally {loc.space[bx+2]=savedColumn;}
                var mx:Number=loc.spaceX*40,my:Number=loc.spaceY*40;
                pair(ctx,"negative-fraction",-9.25,y+100,8.75,y+100,null,true);
                pair(ctx,"negative-coordinate",-41,y+100,39,y+100,null,true);
                pair(ctx,"left-edge",20,y+100,-20,y+100,null,true);
                pair(ctx,"right-edge",mx-20,y+100,mx+20,y+100,null,true);
                pair(ctx,"top-edge",x+100,20,x+100,-20,null,true);
                pair(ctx,"bottom-edge",x+100,my-20,x+100,my+20,null,true);
                pair(ctx,"nan-start",NaN,y+100,x+100,y+100,true,true);
                pair(ctx,"positive-infinity",x+100,y+100,Infinity,y+100,true,true);
                pair(ctx,"negative-infinity",-Infinity,y+100,x+100,y+100,true,true);
                pair(ctx,"signed-int-wrap",2147483649,y+100,2147483689,y+100,null,true);
            } catch(error:Error) {
                out.error={message:error.message,errorID:error.errorID,stack:error.getStackTrace()};
            } finally {
                var errors:Array=[];
                for each(var column:Object in columns) {
                    try {loc.space[column.x]=column.value;}catch(columnError:Error){errors.push("column:"+columnError.message);}
                }
                for each(var saved:Object in rows) {
                    try {
                        loc.space[saved.x][saved.y]=saved.tile;
                        for each(field in FIELDS)saved.tile[field]=saved.values[field];
                    } catch(tileError:Error) {errors.push("tile:"+tileError.message);}
                }
                if(haveApi)for each(field in API_FIELDS) {
                    try {api[key(field)]=savedApi[field];}catch(apiError:Error){errors.push("api:"+apiError.message);}
                }
                if(havePause)try {w.onPause=oldPause;}catch(pauseError:Error){errors.push("pause:"+pauseError.message);}
                try {
                    for each(column in columns)if(loc.space[column.x]!==column.value)errors.push("column-identity");
                    for each(saved in rows) {
                        if(loc.space[saved.x][saved.y]!==saved.tile)errors.push("tile-identity");
                        for each(field in FIELDS)if(!same(saved.tile[field],saved.values[field]))errors.push("tile-field:"+field);
                    }
                    if(haveApi)for each(field in API_FIELDS)if(!same(api[key(field)],savedApi[field]))errors.push("api-field:"+field);
                    if(havePause && (w.onPause!==oldPause || w.loc!==loc || loc.space!==oldSpace || w.gg!==oldGG || w.grafon!==oldGrafon))
                        errors.push("world-context");
                } catch(verifyError:Error) {errors.push("restore-verify:"+verifyError.message);}
                out.restore={passed:errors.length==0 && haveApi && havePause && rows.length==25,
                    restoredTiles:rows.length,restoredFields:rows.length*FIELDS.length,errors:errors,
                    apiPublicStateRestored:haveApi && errors.length==0,terminalProcessRequired:true,privateClassCacheRestored:false};
            }
            out.passed=!out.error && out.restore.passed && out.cases.length==EXPECTED_CASES
                && out.cacheHits>0 && out.blockedCases>=7 && out.fallbackCases==10 && out.nativeCalls==EXPECTED_CASES*2;
            for each(var test:Object in out.cases)if(!test.passed)out.passed=false;
            if(check!=null)check("tdfc-los-terminal-components",out.passed,{cases:out.cases.length,hits:out.cacheHits,restore:out.restore,error:out.error});
            return out;
        }
    }
}
