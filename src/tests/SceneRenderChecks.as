package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.MovieClip;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Isolated factory driver only. Synchronous checks; no world step or save.
     * Native light pixels and two water cells are restored before returning.
     * This does not certify the live RV overlay; the main driver checks that.
     */
    public class SceneRenderChecks {
        public static function run(w:*):Array {
            var result:Array=[];
            if(!w || !w.loc || !w.gg || !w.cam || !w.grafon) {
                add(result,"render-context-ready",false); return result;
            }
            try { lighting(w,result); } catch(e2:Error) { add(result,"render-light-exception",false,e2.message); }
            try { regions(w,result); } catch(e3:Error) { add(result,"render-region-exception",false,e3.message); }
            return result;
        }

        /** Experience's terminal phase only, BEFORE SceneDecalChecks. Three
         * full native redraws are deliberately excluded from Perf/Factory/Lab.
         * Electrical doors alter private Interact save state, and effects/pets
         * can run extra logic in inLoc; refuse such fixtures before mutation.
         */
        public static function runPower(w:*):Array {
            var rows:Array=[],g:*=w.grafon,loc:*=w.loc,gg:*=w.gg;
            var safe:Boolean=NativeApplication.nativeApplication.applicationID=="pfe-modsettings-continuous-scene" &&
                g.sceneLarge && loc.prob==null && !gg.pet && gg.effects.length==0;
            var electricalDoors:int=0;
            for each(var obj:* in loc.objs) if(obj.inter && obj.inter.lockTip==4) ++electricalDoors;
            safe=safe && electricalDoors==0;
            add(rows,"render-power-fixture-restorable",safe,
                {electricalDoors:electricalDoors,playerEffects:gg.effects.length,pet:gg.pet!=null,prob:loc.prob!=null});
            if(!safe) return rows;

            var started:int=getTimer(),regions:Array=[],entities:Array=[],interactions:Array=[],backdrops:Array=[];
            var original:Object={color:loc.color,ct:loc.cTransform,darkness:loc.darkness,lightOn:loc.lightOn,
                noGas:gg.t_nogas,stayDam:gg.isStayDam,flying:gg.isFly,lightVisible:gg.vis.svet.visible,
                petSlot:loc.units[1],relight:loc.isRelight,rebuild:loc.isRebuild,
                quakeX:w.cam.quakeX,quakeY:w.cam.quakeY,zoom:w.cam.isZoom};
            var surfaces:Array=g.sceneSurfaces(),resident:int=surfaces.length;
            var first:Object=null;
            // An empty/black-only foreground cannot demonstrate a tint change.
            for each(var candidate:Object in surfaces)
                if(!candidate.nativeBuffers[0].getColorBoundsRect(0x00FFFFFF,0,false).isEmpty()) {first=candidate;break;}
            var offPixels:BitmapData,comparison:BitmapData;
            var mutated:Boolean=false;
            try {
                if(!first) throw new Error("Power check requires resident native surfaces");
                for each(var slice:Object in g.sceneRegionSlices(loc,new Rectangle(0,0,loc.limX,loc.limY))) {
                    var style:Object=slice.style;
                    regions.push({style:style,color:style.color,ct:style.cTransform,darkness:style.darkness,
                        key:style.key,backwall:style.backwall});
                }
                if(!regions.length) throw new Error("Power check requires regional metadata");
                for each(obj in loc.units.concat(loc.objs)) {
                    if(!obj) continue;
                    var weapon:*= "currentWeapon" in obj ? obj.currentWeapon : null;
                    entities.push({target:obj,ct:obj.cTransform,visual:obj.vis?obj.vis.transform.colorTransform:null,
                        weapon:weapon,weaponColor:weapon && weapon.vis?weapon.vis.transform.colorTransform:null});
                }
                for each(obj in loc.objs) if(obj.inter)
                    interactions.push({target:obj.inter,active:obj.inter.active,actionText:obj.inter.actionText,
                        stateText:obj.inter.stateText,sndAct:obj.inter.sndAct});
                for each(var backdrop:* in loc.backobjs)
                    backdrops.push({target:backdrop,frame:backdrop.frame,
                        vis:backdrop.vis?backdrop.vis.currentFrame:0,erase:backdrop.erase?backdrop.erase.currentFrame:0,
                        light:backdrop.light?backdrop.light.currentFrame:0});

                mutated=true;
                loc.alloff();
                powerState(w,rows,"off",regions,backdrops,entities,-1,"black",20);
                var offSurface:Object=findSurface(g,first.cx,first.cy);
                add(rows,"render-power-off-full-repaint",offSurface && offSurface!==first && g.sceneResident==resident,
                    {resident:g.sceneResident,expected:resident});
                if(!offSurface) throw new Error("Native power-off redraw lost sampled surface");
                offPixels=offSurface.nativeBuffers[0].clone();
                for each(var backRecord:Object in backdrops) backRecord.offFrame=backRecord.target.frame;

                loc.allon();
                powerState(w,rows,"on",regions,backdrops,entities,1,"yellow",-20);
                var onSurface:Object=findSurface(g,first.cx,first.cy);
                add(rows,"render-power-on-full-repaint",onSurface && onSurface!==offSurface && g.sceneResident==resident,
                    {resident:g.sceneResident,expected:resident});
                if(!onSurface) throw new Error("Native power-on redraw lost sampled surface");
                var delta:*=offPixels.compare(onSurface.nativeBuffers[0]);
                if(delta is BitmapData) comparison=delta;
                add(rows,"render-power-on-off-pixels-differ",delta is BitmapData,
                    {cx:first.cx,cy:first.cy,bounds:comparison?comparison.getColorBoundsRect(0xFFFFFFFF,0,false).toString():null});
            } catch(error:Error) {add(rows,"render-power-exception",false,error.message);}
            finally {
                try {
                    if(mutated) {
                        loc.color=original.color;loc.cTransform=original.ct;loc.darkness=original.darkness;loc.lightOn=original.lightOn;
                        for each(var regionRecord:Object in regions) {
                            style=regionRecord.style;style.color=regionRecord.color;style.cTransform=regionRecord.ct;
                            style.darkness=regionRecord.darkness;style.key=regionRecord.key;
                        }
                        for each(backRecord in backdrops) {
                            backdrop=backRecord.target;backdrop.frame=backRecord.frame;
                            if(backdrop.vis) backdrop.vis.gotoAndStop(backRecord.vis);
                            if(backdrop.erase) backdrop.erase.gotoAndStop(backRecord.erase);
                            if(backdrop.light) backdrop.light.gotoAndStop(backRecord.light);
                        }
                        for each(var interactionRecord:Object in interactions) {
                            var inter:*=interactionRecord.target;
                            inter.active=interactionRecord.active;inter.actionText=interactionRecord.actionText;
                            inter.stateText=interactionRecord.stateText;inter.sndAct=interactionRecord.sndAct;
                        }
                        w.redrawLoc();
                        // Re-establish the native base ownership in the tint
                        // cache before restoring custom/effect display colors.
                        for each(var entityRecord:Object in entities) {
                            obj=entityRecord.target;obj.cTransform=loc.cTransform;
                            g.sceneUpdateEntityColor(obj);
                            obj.cTransform=entityRecord.ct;
                            if(obj.vis && entityRecord.visual) obj.vis.transform.colorTransform=entityRecord.visual;
                            if(entityRecord.weapon && entityRecord.weapon.vis && entityRecord.weaponColor)
                                entityRecord.weapon.vis.transform.colorTransform=entityRecord.weaponColor;
                        }
                        gg.t_nogas=original.noGas;gg.isStayDam=original.stayDam;gg.isFly=original.flying;
                        gg.vis.svet.visible=original.lightVisible;loc.units[1]=original.petSlot;
                        loc.isRelight=original.relight;loc.isRebuild=original.rebuild;
                        w.cam.setZoom(original.zoom);w.cam.quakeX=original.quakeX;w.cam.quakeY=original.quakeY;
                        var restored:Boolean=loc.color==original.color && loc.cTransform===original.ct &&
                            loc.darkness==original.darkness && loc.lightOn==original.lightOn;
                        for each(regionRecord in regions) restored=restored && regionRecord.style.cTransform===regionRecord.ct &&
                            regionRecord.style.color==regionRecord.color && regionRecord.style.darkness==regionRecord.darkness &&
                            regionRecord.style.key==regionRecord.key && regionRecord.style.backwall==regionRecord.backwall;
                        for each(entityRecord in entities) {
                            restored=restored && entityRecord.target.cTransform===entityRecord.ct;
                            if(entityRecord.visual && entityRecord.target.vis)
                                restored=restored && sameColor(entityRecord.target.vis.transform.colorTransform,entityRecord.visual);
                        }
                        for each(backRecord in backdrops) {
                            backdrop=backRecord.target;restored=restored && backdrop.frame==backRecord.frame;
                            if(backdrop.vis) restored=restored && backdrop.vis.currentFrame==backRecord.vis;
                            if(backdrop.erase) restored=restored && backdrop.erase.currentFrame==backRecord.erase;
                            if(backdrop.light) restored=restored && backdrop.light.currentFrame==backRecord.light;
                        }
                        for each(interactionRecord in interactions) restored=restored &&
                            interactionRecord.target.active==interactionRecord.active &&
                            interactionRecord.target.actionText==interactionRecord.actionText &&
                            interactionRecord.target.stateText==interactionRecord.stateText &&
                            interactionRecord.target.sndAct==interactionRecord.sndAct;
                        add(rows,"render-power-state-restored",restored,{elapsedMs:getTimer()-started});
                        add(rows,"render-power-restored-full-repaint",g.sceneResident==resident &&
                            findSurface(g,first.cx,first.cy)!=null,{resident:g.sceneResident,expected:resident});
                    }
                } catch(restoreError:Error) {add(rows,"render-power-restore-exception",false,restoreError.message);}
                if(offPixels) offPixels.dispose();if(comparison) comparison.dispose();
            }
            return rows;
        }

        private static function findSurface(g:*,cx:int,cy:int):Object {
            for each(var surface:Object in g.sceneSurfaces()) if(surface.cx==cx && surface.cy==cy) return surface;
            return null;
        }

        private static function powerState(w:*,rows:Array,label:String,regions:Array,backdrops:Array,entities:Array,
                                           lightOn:int,color:String,darkness:int):void {
            var loc:*=w.loc,expected:ColorTransform=loc.colorFilter(color);
            add(rows,"render-power-"+label+"-native-state",loc.lightOn==lightOn && loc.color==color &&
                loc.darkness==darkness && sameColor(loc.cTransform,expected));
            var stylesOK:Boolean=true;
            for each(var region:Object in regions) {
                var style:Object=region.style;
                stylesOK=stylesOK && style.color==color && style.darkness==darkness &&
                    sameColor(style.cTransform,expected) && style.backwall==region.backwall && style.key!=region.key &&
                    w.grafon.sceneRegionStyle(loc,style.bounds.x+1,style.bounds.y+1)===style;
            }
            add(rows,"render-power-"+label+"-regions-and-materials",stylesOK,{regions:regions.length});
            var framesOK:Boolean=true,switched:int=0;
            for each(var back:Object in backdrops) {
                var target:*=back.target,frame:int=lightOn<0?target.frameOff:target.frameOn;
                if(frame>0) {
                    ++switched;framesOK=framesOK && target.frame==frame;
                    for each(var art:MovieClip in [target.vis,target.erase,target.light])
                        if(art) framesOK=framesOK && art.currentFrame==Math.min(frame,art.totalFrames);
                } else framesOK=framesOK && target.frame==(lightOn<0?back.frame:back.offFrame);
            }
            add(rows,"render-power-"+label+"-backdrop-frames",framesOK && switched>0,{switched:switched});
            var entitiesOK:Boolean=true;
            for each(var entity:Object in entities) {
                w.grafon.sceneUpdateEntityColor(entity.target);
                entitiesOK=entitiesOK && sameColor(entity.target.cTransform,expected);
            }
            add(rows,"render-power-"+label+"-entity-base-colors",entitiesOK,{entities:entities.length});
        }
        private static function add(rows:Array,name:String,ok:Boolean,detail:*=null):void {
            rows.push({name:name,ok:ok,detail:detail});
        }
        private static function lighting(w:*,rows:Array):void {
            var loc:*=w.loc,g:*=w.grafon;
            var x:int=loc.spaceX-3,y:int=loc.spaceY-3,tile:*=loc.getTile(x,y);
            var oldVisi:Number=tile.visi,oldTarget:Number=tile.t_visi;
            var saved:BitmapData=g.lightBmp.clone();
            try {
                add(rows,"render-light-field-full-scene",g.lightBmp.width==loc.spaceX+1 && g.lightBmp.height==loc.spaceY+3,
                    {width:g.lightBmp.width,height:g.lightBmp.height});
                tile.visi=0.25;tile.t_visi=0.25;g.setLight();
                add(rows,"render-far-native-light-pixel",g.lightBmp.getPixel32(x,y+1)==0xBF000000,
                    {x:x,y:y,pixel:g.lightBmp.getPixel32(x,y+1)});
                add(rows,"render-native-light-transform",g.visLight.scaleX==40 && g.visLight.scaleY==40 &&
                    g.visLight.x==-20 && g.visLight.y==-60);
            } finally {
                tile.visi=oldVisi;tile.t_visi=oldTarget;
                g.lightBmp.copyPixels(saved,saved.rect,new Point());saved.dispose();
            }
        }
        private static function sameColor(a:ColorTransform,b:ColorTransform):Boolean {
            return a && b && a.redMultiplier==b.redMultiplier && a.greenMultiplier==b.greenMultiplier &&
                a.blueMultiplier==b.blueMultiplier && a.alphaMultiplier==b.alphaMultiplier &&
                a.redOffset==b.redOffset && a.greenOffset==b.greenOffset && a.blueOffset==b.blueOffset && a.alphaOffset==b.alphaOffset;
        }
        private static function regions(w:*,rows:Array):void {
            var g:*=w.grafon,loc:*=w.loc;
            var all:Array=g.sceneRegionSlices(loc,new Rectangle(0,0,loc.limX,loc.limY));
            add(rows,"render-factory-twelve-region-styles",all.length==12,all.length);
            if(all.length!=12) return;
            var red:Object=g.sceneRegionStyle(loc,2500,2500),blue:Object=g.sceneRegionStyle(loc,6500,2500);
            add(rows,"render-region-native-red-style",red && red.backwall=="tConcreteDirt" && sameColor(red.cTransform,loc.colorFilter("red")));
            add(rows,"render-region-native-blue-style",blue && sameColor(blue.cTransform,loc.colorFilter("blue")));
            var crossing:Array=g.sceneRegionSlices(loc,new Rectangle(1880,1880,400,400));
            var area:Number=0,overlap:Boolean=false;
            for(var i:int=0;i<crossing.length;++i) {
                area+=crossing[i].bounds.width*crossing[i].bounds.height;
                for(var j:int=0;j<i;++j) overlap=overlap || crossing[i].bounds.intersects(crossing[j].bounds);
            }
            add(rows,"render-region-crossing-clips-cover-once",crossing.length==4 && area==160000 && !overlap,
                {clips:crossing.length,area:area,overlap:overlap});
            waterPixels(w,rows);
        }
        private static function waterPixels(w:*,rows:Array):void {
            var g:*=w.grafon,loc:*=w.loc,top:*=loc.getTile(51,49),bottom:*=loc.getTile(51,50);
            var savedTop:Number=top.water,savedBottom:Number=bottom.water,oldDirty:int=g.sceneLastDirtyCount;
            var color:ColorTransform=loc.cTransform;
            var affected:Rectangle=new Rectangle(2040,1960,40,80),saved:Array=[],target:Object;
            var expected:BitmapData,comparison:BitmapData;
            try {
                for each(var surface:Object in g.sceneSurfaces())
                    if(affected.intersects(new Rectangle(surface.x,surface.y,surface.nativeBuffers[3].width,surface.nativeBuffers[3].height))) {
                        saved.push({surface:surface,data:surface.nativeBuffers[3].clone(),revision:surface.revision});
                        if(surface.cx==6 && surface.cy==6) target=surface;
                    }
                add(rows,"render-cross-region-water-surface",target!=null,saved.length);
                if(target==null) return;
                top.water=bottom.water=1;expected=target.nativeBuffers[3].clone();
                var Water:Class=getDefinitionByName("tileVoda") as Class;
                for each(var tile:* in [top,bottom]) {
                    var art:MovieClip=new Water();art.gotoAndStop(loc.tipWater+1);
                    var above:*=loc.getTile(tile.X,tile.Y-1);
                    art["voda"].gotoAndStop(above.water==0 && above.phis==0?2:1);
                    var style:Object=g.sceneRegionStyle(loc,tile.X*40+20,tile.Y*40+20);
                    expected.draw(art,new Matrix(1,0,0,1,tile.X*40-target.x,tile.Y*40-target.y),
                        style?style.cTransform:color,"normal",null,false);
                }
                g.drawWater(top,true);
                var diff:*=target.nativeBuffers[3].compare(expected);
                if(diff is BitmapData) comparison=diff;
                add(rows,"render-cross-region-water-exact-native-pixels",diff===0,
                    {changedChunks:g.sceneLastDirtyCount,expectedChunks:saved.length});
                add(rows,"render-incremental-style-restored",loc.cTransform===color);
                add(rows,"render-water-only-touches-overlapping-chunks",g.sceneLastDirtyCount==saved.length);
            } finally {
                top.water=savedTop;bottom.water=savedBottom;loc.cTransform=color;g.sceneLastDirtyCount=oldDirty;
                for each(var record:Object in saved) {
                    record.surface.nativeBuffers[3].copyPixels(record.data,record.data.rect,new Point());
                    record.surface.revision=record.revision;record.data.dispose();
                }
                if(expected) expected.dispose();if(comparison) comparison.dispose();
            }
        }
    }
}
