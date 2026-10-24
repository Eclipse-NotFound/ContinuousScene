package tests {
    import flash.desktop.NativeApplication;
    import flash.filters.GlowFilter;
    import flash.geom.ColorTransform;
    import flash.system.ApplicationDomain;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal component test of the real host method. Never a movement/FPS test. */
    public class SceneEntityTintChecks {
        private static const CT:Array=["redMultiplier","greenMultiplier","blueMultiplier","alphaMultiplier",
            "redOffset","greenOffset","blueOffset","alphaOffset"];

        public static function run(w:*,check:Function=null,expectFixed:Boolean=false):Object {
            var started:int=getTimer();
            var out:Object={version:"scene-entity-tint-components-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,expectFixed:expectFixed,passed:false,cases:[],observations:[],restore:{passed:false},
                limitations:[
                    "Two real native region objects receive explicit green/neutral component color inputs. No terrain draw, physics, input, travel or pixel equivalence is claimed.",
                    "The actual player and an existing native Box are used. Pickup state is replayed from native actTele color rules; the real public dropTeleObj performs release.",
                    "All touched public values/references and region color references are restored. Grafon's private weak entity-color/location-token caches cannot be restored through its public API.",
                    "The real dropTeleObj refreshes GUI mana text. Terminate this isolated process without saving, advancing gameplay, or performance measurement.",
                    "Actual factory-to-neutral-room walking/levitation and departure through Game.gotoLand remain separate travel acceptance tests."
                ]};
            var saves:Array=[],actors:Array=[],regions:Array=[],regionSaved:Array=[];
            var player:*=null,box:*=null,g:*=null,loc:*=null,ctx:Object=null;
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    throw new Error("An isolated continuous-motion application is required");
                if(!w || !w.main || !w.gg || !w.loc || !w.grafon || !w.gui)
                    throw new Error("A fully initialized native continuous scene is required");
                var ad:ApplicationDomain=w.main.loaderInfo.applicationDomain;
                var wc:Class=ad.getDefinition("fe.World") as Class;
                var pc:Class=ad.getDefinition("fe.unit.UnitPlayer") as Class;
                var bc:Class=ad.getDefinition("fe.loc.Box") as Class;
                if(wc[new QName("","w")]!==w || Object(w.gg).constructor!==pc)
                    throw new Error("World/player must be the actual host-domain instances");
                player=w.gg;loc=w.loc;g=w.grafon;
                if(!g.sceneLarge || g.loc!==loc || player.loc!==loc || !player.vis || !player.vis.osn)
                    throw new Error("The player and Grafon must own this active large Location");
                if(player.teleObj!=null)throw new Error("Run the terminal component before native telekinesis begins");
                for each(var obj:* in loc.objs) {
                    if(obj is bc && obj.loc===loc && obj.vis!=null) { box=obj;break; }
                }
                if(box==null)throw new Error("An existing native Box with a live visual is required");
                // The merged native map uses 1920x1000 room cells; inspect only their centers.
                for(var x:int=960;x<loc.limX;x+=1920) for(var y:int=500;y<loc.limY;y+=1000) {
                    var style:Object=g.sceneRegionStyle(loc,x,y);
                    if(style!=null && regions.indexOf(style)<0)regions.push(style);
                }
                if(regions.length<2)throw new Error("Two real native region identities are required");
                regions=regions.slice(0,2);
                out.applicationID=app;
                out.nativeIdentity={world:true,playerClass:getQualifiedClassName(player),boxClass:getQualifiedClassName(box),
                    locationClass:getQualifiedClassName(loc),playerIsGG:player===w.gg,boxIndex:loc.objs.indexOf(box)};
                out.regionInputs=[];
                for(var n:int=0;n<2;++n) {
                    regionSaved.push(regions[n].cTransform);
                    out.regionInputs.push({bounds:String(regions[n].bounds),originalColor:String(regions[n].color),
                        originalTransform:values(regions[n].cTransform),componentColor:n==0?"green":""});
                }
                save(saves,w,"onPause,shineObjs");save(saves,g,"sceneLarge,sceneEntityTintChanges");
                save(saves,player,"teleObj");
                actors.push(captureActor(player,true));actors.push(captureActor(box,false));
                w.onPause=true;w.shineObjs=false;
                regions[0].cTransform=loc.colorFilter("green");
                regions[1].cTransform=loc.colorFilter("");
                ctx={w:w,g:g,loc:loc,player:player,out:out,regions:regions,calls:0};
                out.ownedComponentTransforms=[values(regions[0].cTransform),values(regions[1].cTransform)];

                seed(ctx,player,0);observe(ctx,"player-grounded-green",player,true);
                position(player,regions[1]);call(ctx,player);
                record(out,"grounded-player-enters-neutral",same(player.vis.transform.colorTransform,regions[1].cTransform)
                    && player.cTransform===regions[1].cTransform,shot(player));

                seed(ctx,player,0);
                player.levit=1;position(player,regions[1]);call(ctx,player);
                out.observations.push({name:"player-levitating-cross",state:shot(player)});
                var logicalChanged:Boolean=player.cTransform===regions[1].cTransform;
                var crossStale:Boolean=same(player.vis.transform.colorTransform,regions[0].cTransform);
                record(out,"levitating-player-logical-base-updates",logicalChanged,shot(player));
                record(out,"levitating-player-display-expectation",expectFixed
                    ? same(player.vis.transform.colorTransform,regions[1].cTransform) : crossStale,shot(player));
                call(ctx,player);
                player.levit=0;call(ctx,player);call(ctx,player);
                out.residualReproduced=logicalChanged && crossStale
                    && same(player.vis.transform.colorTransform,regions[0].cTransform);
                record(out,"player-after-levitation-display-expectation",expectFixed
                    ? same(player.vis.transform.colorTransform,regions[1].cTransform) : out.residualReproduced,shot(player));
                if(player.currentWeapon && player.currentWeapon.tip!=5 && player.currentWeapon.vis)
                    record(out,"plain-held-weapon-follows-neutral",same(player.currentWeapon.vis.transform.colorTransform,
                        regions[1].cTransform),{weapon:values(player.currentWeapon.vis.transform.colorTransform)});

                seed(ctx,box,0);
                var ac:Class=ad.getDefinition("fe.inter.Appear") as Class;
                var magic:ColorTransform=ac[new QName("","trMagic")] as ColorTransform;
                if(!magic)throw new Error("Native appearance magic ColorTransform is absent");
                var tele:ColorTransform=new ColorTransform(magic.redMultiplier*.5+1,
                    magic.greenMultiplier*.5+1,magic.blueMultiplier*.5+1);
                box.vis.transform.colorTransform=tele;
                box.vis.filters=[new GlowFilter(uint(w.app.cMagic),1,6,6,1,3)];
                box.levit=1;position(box,regions[1]);call(ctx,box);
                record(out,"telekinetic-box-keeps-magic-color",box.cTransform===regions[1].cTransform
                    && same(box.vis.transform.colorTransform,tele),shot(box));
                player.teleObj=box;
                player.dropTeleObj();
                record(out,"native-drop-restores-new-region-base",player.teleObj==null && box.levit==0
                    && box.vis.filters.length==0 && same(box.vis.transform.colorTransform,regions[1].cTransform),shot(box));
                call(ctx,box);observe(ctx,"released-box-stays-neutral",box,true);

                // A different root transform represents another effect/mod's ownership; never overwrite it.
                seed(ctx,player,0);
                var external:ColorTransform=new ColorTransform(.31,.47,.63,1,7,11,13,0);
                player.vis.transform.colorTransform=external;
                position(player,regions[1]);call(ctx,player);call(ctx,player);
                record(out,"external-player-root-color-preserved",same(player.vis.transform.colorTransform,external)
                    && player.cTransform===regions[1].cTransform,shot(player));
                record(out,"player-inner-effects-untouched",same(player.vis.osn.transform.colorTransform,actors[0].innerCT)
                    && filterValues(player.vis.osn.filters)==actors[0].innerFiltersJSON,{inner:values(player.vis.osn.transform.colorTransform)});

                var gateCT:ColorTransform=player.cTransform;
                var gateDisplay:ColorTransform=player.vis.transform.colorTransform;
                g.sceneLarge=false;position(player,regions[0]);call(ctx,player);g.sceneLarge=true;
                record(out,"non-large-updater-gate-does-not-write",player.cTransform===gateCT
                    && same(player.vis.transform.colorTransform,gateDisplay),{scope:"updater gate only; not native travel"});
                out.nativeCalls=ctx.calls;
            } catch(error:*) {
                out.error=String(error);out.stack=error is Error?Error(error).getStackTrace():null;
            } finally {
                try {
                    for(var r:int=0;r<regionSaved.length;++r)regions[r].cTransform=regionSaved[r];
                    for each(var actor:Object in actors)restoreActor(actor);
                    restore(saves);
                    var ok:Boolean=true;
                    for(r=0;r<regionSaved.length;++r)ok=ok && regions[r].cTransform===regionSaved[r];
                    for each(actor in actors)ok=ok && actorRestored(actor);
                    for each(var saved:Object in saves)for(var key:String in saved.fields)
                        ok=ok && saved.target[new QName("",key)]===saved.fields[key];
                    out.restore={passed:ok,publicStateRestored:ok,regionReferencesRestored:ok,
                        privateColorCacheRestored:false,terminalProcessRequired:true};
                } catch(cleanup:*) {out.restore={passed:false,error:String(cleanup)};}
                out.elapsedMs=getTimer()-started;
            }
            out.passed=!out.error && out.restore.passed && out.cases.length>0;
            for each(var c:Object in out.cases)if(!c.passed)out.passed=false;
            if(check!=null)check("scene-entity-tint-components",out.passed,out);
            return out;
        }
        private static function position(target:*,style:Object):void {
            target.X=style.bounds.x+style.bounds.width/2;
            target.Y=style.bounds.y+style.bounds.height/2+target.scY/2;
        }
        private static function seed(ctx:Object,target:*,index:int):void {
            target.cTransform=ctx.loc.cTransform;target.vis.transform.colorTransform=ctx.loc.cTransform;target.levit=0;
            if(target===ctx.player && target.currentWeapon && target.currentWeapon.tip!=5 && target.currentWeapon.vis)
                target.currentWeapon.vis.transform.colorTransform=ctx.loc.cTransform;
            position(target,ctx.regions[index]);call(ctx,target);
        }
        private static function call(ctx:Object,target:*):void {ctx.g.sceneUpdateEntityColor(target,true);++ctx.calls;}
        private static function observe(ctx:Object,name:String,target:*,equal:Boolean):void {
            record(ctx.out,name,same(target.vis.transform.colorTransform,target.cTransform)==equal,shot(target));
        }
        private static function shot(target:*):Object {
            return {X:target.X,Y:target.Y,levit:target.levit,logical:values(target.cTransform),
                displayed:values(target.vis.transform.colorTransform),logicalDisplayEqual:same(target.cTransform,target.vis.transform.colorTransform)};
        }
        private static function values(c:ColorTransform):Array {
            if(!c)return null;
            var result:Array=[];for each(var key:String in CT)result.push(c[key]);return result;
        }
        private static function same(a:ColorTransform,b:ColorTransform):Boolean {
            if(!a || !b)return a===b;
            for each(var key:String in CT)if(a[key]!==b[key])return false;return true;
        }
        private static function captureActor(target:*,inner:Boolean):Object {
            var s:Object={target:target,X:target.X,Y:target.Y,levit:target.levit,base:target.cTransform,
                visual:target.vis,rootCT:target.vis.transform.colorTransform,filters:target.vis.filters,
                filtersJSON:filterValues(target.vis.filters)};
            if(inner) {
                s.inner=target.vis.osn;s.innerCT=s.inner.transform.colorTransform;s.innerFilters=s.inner.filters;
                s.innerFiltersJSON=filterValues(s.innerFilters);
                if(target.currentWeapon && target.currentWeapon.vis) {
                    s.weapon=target.currentWeapon;s.weaponVisual=s.weapon.vis;s.weaponCT=s.weaponVisual.transform.colorTransform;
                }
            }
            return s;
        }
        private static function restoreActor(s:Object):void {
            s.target.X=s.X;s.target.Y=s.Y;s.target.levit=s.levit;s.target.cTransform=s.base;
            s.visual.transform.colorTransform=s.rootCT;s.visual.filters=s.filters;
            if(s.inner) {s.inner.transform.colorTransform=s.innerCT;s.inner.filters=s.innerFilters;}
            if(s.weaponVisual)s.weaponVisual.transform.colorTransform=s.weaponCT;
        }
        private static function actorRestored(s:Object):Boolean {
            var ok:Boolean=s.target.X===s.X && s.target.Y===s.Y && s.target.levit===s.levit
                && s.target.cTransform===s.base && s.target.vis===s.visual
                && same(s.visual.transform.colorTransform,s.rootCT) && filterValues(s.visual.filters)==s.filtersJSON;
            if(s.inner)ok=ok && s.target.vis.osn===s.inner && same(s.inner.transform.colorTransform,s.innerCT)
                && filterValues(s.inner.filters)==s.innerFiltersJSON;
            if(s.weaponVisual)ok=ok && s.target.currentWeapon===s.weapon && s.weapon.vis===s.weaponVisual
                && same(s.weaponVisual.transform.colorTransform,s.weaponCT);
            return ok;
        }
        private static function filterValues(filters:Array):String {
            var result:Array=[];
            for each(var f:* in filters) {
                var item:Object={type:getQualifiedClassName(f)};
                for each(var key:String in ["color","alpha","blurX","blurY","strength","quality","inner","knockout",
                    "distance","angle","hideObject","matrix"])
                    if(key in f)item[key]=f[key];
                result.push(item);
            }
            return JSON.stringify(result);
        }
        private static function save(list:Array,target:*,fields:String):void {
            var s:Object={target:target,fields:{}};
            for each(var key:String in fields.split(","))s.fields[key]=target[new QName("",key)];list.push(s);
        }
        private static function restore(list:Array):void {
            for(var i:int=list.length-1;i>=0;--i)for(var key:String in list[i].fields)
                list[i].target[new QName("",key)]=list[i].fields[key];
        }
        private static function record(out:Object,name:String,passed:Boolean,detail:Object):void {
            out.cases.push({name:name,passed:passed,detail:detail});
        }
    }
}
