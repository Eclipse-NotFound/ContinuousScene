package tests {
    import flash.display.DisplayObject;
    import flash.display.Sprite;
    import flash.geom.Rectangle;

    /** Differential gate for the analytic bounds cache in SceneObjectCulling
     * (event-tracked-2). The oracle recomputes getBounds for every root on
     * every frame and applies the identical hide formula, so a wrong cached
     * box, a wrong mirror, a stale cache reused after a rotation, or a skipped
     * re-decide after a translation shows up as a visibility mismatch instead
     * of a silent visual pop. No stage, no game, no save files. */
    public class SceneCullingScaleChecks {
        public static function run(type:Class):Array {
            var rows:Array=[];
            function check(name:String,ok:Boolean,detail:Object=null):void {
                rows.push({name:name,ok:ok,detail:detail});
                if(!ok)throw new Error("CullingScale: "+name+" "+JSON.stringify(detail));
            }

            // ------------------------------------------------------------ A
            // Randomised mixed scene: roots flip, pulse and translate every
            // frame while the camera also moves. Production must agree with the
            // oracle on every root of every frame.
            var world:Object=makeWorld(type);
            var cut:*=world.cut,visual:Sprite=world.visual,roots:Array=world.roots;
            var rng:Object=seedRng(0x5EED1234);
            var mismatches:Array=[],frames:int=0,hiddenFrames:int=0;
            var transformed:int=0,totalBounds:int=0,totalSkips:int=0,maxBounds:int=0;
            var f:int,i:int;
            for(f=0;f<90;++f) {
                transformed+=mutate(roots,rng);
                if(f%7==0)moveCamera(world,rng);
                cut.update(world.w,true);
                var stats:Object=cut.stats();
                totalBounds+=stats.boundsReads;totalSkips+=stats.scaleSkips;
                maxBounds=Math.max(maxBounds,stats.boundsReads);
                for(i=0;i<roots.length;++i) {
                    var root:DisplayObject=roots[i];
                    if(root.parent==null)continue;
                    var expected:Boolean=!oracleHidden(root,visual,world.w.cam);
                    if(root.parent.visible!=expected) {
                        mismatches.push({frame:f,index:i,x:root.x,y:root.y,
                            sx:root.scaleX,sy:root.scaleY,rot:root.rotation,
                            got:root.parent.visible,expected:expected});
                        if(mismatches.length>6)break;
                    }
                }
                ++frames;
                if(stats.hidden>0)++hiddenFrames;
                if(mismatches.length)break;
            }
            check("mixed-scene-frame-count",frames==90,{frames:frames});
            check("mixed-scene-oracle-agrees",mismatches.length==0,{mismatches:mismatches});
            check("mixed-scene-culls-something",hiddenFrames>0,{hiddenFrames:hiddenFrames});
            check("mixed-scene-fast-path-dominant",totalSkips>transformed*0.25,
                {skips:totalSkips,transformed:transformed});
            check("mixed-scene-bounds-reads-bounded",totalBounds<=frames*8,
                {totalBounds:totalBounds,perFrame:totalBounds/frames,maxPerFrame:maxBounds});
            var surface:Object=cut.stats();
            check("mixed-scene-stats-surface",surface.version=="event-tracked-2" &&
                int(surface.baseRefreshes)>=1 && int(surface.visits)>0,
                {version:surface.version,baseRefreshes:surface.baseRefreshes,visits:surface.visits});
            cut.clear();

            // ------------------------------------------------------------ M
            // Asymmetric art: a mirror is not a rescaled symmetric box, so a
            // wrong edge swap changes the cull decision. Sign flips only.
            var mirror:Object=makeWorld(type,1);
            var mcut:*=mirror.cut,mroot:DisplayObject=mirror.roots[0];
            mroot.x=0;mroot.y=0;mroot.scaleX=1;mroot.scaleY=1;mroot.rotation=0;
            mcut.update(mirror.w,true);
            var mirrorBad:Array=[],mirrorSkips:int=0;
            for(f=0;f<8;++f) {
                mroot.scaleX=(f%2==0)?-1:1;
                mcut.update(mirror.w,true);
                mirrorSkips+=mcut.stats().scaleSkips;
                var mExpected:Boolean=!oracleHidden(mroot,mirror.visual,mirror.w.cam);
                if(mroot.parent.visible!=mExpected)mirrorBad.push({frame:f,expected:mExpected});
            }
            check("mirror-matches-oracle",mirrorBad.length==0,{bad:mirrorBad});
            check("mirror-uses-arithmetic",mirrorSkips>=7,{skips:mirrorSkips});
            mcut.clear();

            // ------------------------------------------------------------ R
            // A rotation change must leave the arithmetic path and measure.
            var rotWorld:Object=makeWorld(type,1);
            var rcut:*=rotWorld.cut,rroot:DisplayObject=rotWorld.roots[0];
            rcut.update(rotWorld.w,true);
            rroot.rotation=45;
            rcut.update(rotWorld.w,true);
            var rotBounds:int=rcut.stats().boundsReads;
            var rotOk:Boolean=rroot.parent.visible==(!oracleHidden(rroot,rotWorld.visual,rotWorld.w.cam));
            rroot.scaleX=-1.5;
            rcut.update(rotWorld.w,true);
            var rotScaleBounds:int=rcut.stats().boundsReads;
            var rotScaleOk:Boolean=rroot.parent.visible==(!oracleHidden(rroot,rotWorld.visual,rotWorld.w.cam));
            check("rotation-measures",rotBounds>=1,{boundsReads:rotBounds});
            check("rotation-oracle-agrees",rotOk);
            check("rotation-then-scale-measures",rotScaleBounds>=1,{boundsReads:rotScaleBounds});
            check("rotation-then-scale-oracle-agrees",rotScaleOk);
            rroot.rotation=0;rcut.update(rotWorld.w,true);
            rroot.scaleX=-1;rroot.scaleY=1;rcut.update(rotWorld.w,true);
            check("rotation-cleared-reuses-cache",rcut.stats().scaleSkips>=1,{skips:rcut.stats().scaleSkips});
            rcut.clear();

            // ------------------------------------------------------------ Z
            // A zero axis collapses the box; the cache must drop out instead of
            // dividing by zero, and recover once the axis returns.
            var zeroWorld:Object=makeWorld(type,1);
            var zcut:*=zeroWorld.cut,zroot:Sprite=zeroWorld.roots[0] as Sprite;
            zcut.update(zeroWorld.w,true);
            var zeroBad:Array=[],scales:Array=[0,0.001,1,-1,0,2];
            for(f=0;f<scales.length;++f) {
                zroot.scaleX=scales[f];
                zcut.update(zeroWorld.w,true);
                var zExpected:Boolean=!oracleHidden(zroot,zeroWorld.visual,zeroWorld.w.cam);
                if(zroot.parent.visible!=zExpected)zeroBad.push({frame:f,scaleX:scales[f],expected:zExpected});
            }
            check("zero-axis-oracle-agrees",zeroBad.length==0,{bad:zeroBad});
            zcut.clear();

            // ------------------------------------------------------------ T
            // A translated root must be re-decided in the same frame, including
            // the frame where the amortised refresh touches it (that refresh
            // must never adopt the new position as already-seen).
            var teleWorld:Object=makeWorld(type,1);
            var tcut:*=teleWorld.cut,troot:DisplayObject=teleWorld.roots[0];
            tcut.update(teleWorld.w,true);
            var teleBad:Array=[];
            for(f=0;f<60;++f) {
                troot.x=(f%2==0)?0:9000;
                tcut.update(teleWorld.w,true);
                var tExpected:Boolean=!oracleHidden(troot,teleWorld.visual,teleWorld.w.cam);
                if(troot.parent.visible!=tExpected)teleBad.push({frame:f,expected:tExpected});
            }
            check("translation-redecided-same-frame",teleBad.length==0,{bad:teleBad});
            tcut.clear();

            // ------------------------------------------------------------ S
            // Art changed under a static root transform: the amortised sweep must
            // refresh the cached box, so a later scale change decides with the
            // new extent (here it flips the object from culled to visible).
            var artWorld:Object=makeWorld(type,1);
            var acut:*=artWorld.cut,aroot:Sprite=artWorld.roots[0] as Sprite;
            aroot.x=1650;aroot.y=0;aroot.scaleX=1;aroot.scaleY=1;aroot.rotation=0;
            drawArt(aroot,200,6,40,40);      // wholly right of the padded viewport
            acut.update(artWorld.w,true);
            var hiddenBefore:Boolean=!aroot.parent.visible;
            drawArt(aroot,-200,6,80,40);     // art now reaches back into the viewport
            for(f=0;f<8;++f)acut.update(artWorld.w,true);   // one full sweep of 3 entries
            aroot.scaleX=1.3;                // force the arithmetic path with the refreshed base
            acut.update(artWorld.w,true);
            var artExpected:Boolean=!oracleHidden(aroot,artWorld.visual,artWorld.w.cam);
            check("art-change-was-culled-before",hiddenBefore,{hiddenBefore:hiddenBefore});
            check("sweep-refreshes-stale-art",aroot.parent.visible==artExpected,
                {got:aroot.parent.visible,expected:artExpected});
            check("sweep-flipped-to-visible",artExpected && aroot.parent.visible);
            acut.clear();

            // ------------------------------------------------------------ E
            // Empty roots stay visible no matter how far away they are.
            var emptyWorld:Object=makeWorld(type);
            var ecut:*=emptyWorld.cut,emptyRoot:Sprite=emptyWorld.empty[0] as Sprite;
            ecut.update(emptyWorld.w,true);
            emptyRoot.x=50000;emptyRoot.y=50000;emptyRoot.scaleX=3;
            ecut.update(emptyWorld.w,true);
            check("empty-root-never-hidden",emptyRoot.parent.visible);
            ecut.clear();

            // ------------------------------------------------------------ U
            // Units-only mode restores every other layer, and switching the
            // tracked layer set back keeps the cache consistent.
            var unitWorld:Object=makeWorld(type);
            var ucut:*=unitWorld.cut;
            var unitsLayer:Sprite=unitWorld.layers[2];
            ucut.update(unitWorld.w,true);
            ucut.update(unitWorld.w,true,true);
            check("units-only-tracks-unit-layer",ucut.stats().tracked>0,{tracked:ucut.stats().tracked});
            check("units-layer-populated",unitsLayer.numChildren>0);
            ucut.update(unitWorld.w,true,false);
            var restoreBad:Array=[];
            for(i=0;i<unitWorld.roots.length;++i) {
                var rr:DisplayObject=unitWorld.roots[i];
                if(rr.parent==null)continue;
                var rExp:Boolean=!oracleHidden(rr,unitWorld.visual,unitWorld.w.cam);
                if(rr.parent.visible!=rExp)restoreBad.push({index:i});
            }
            check("layer-set-switch-oracle-agrees",restoreBad.length==0,{bad:restoreBad});
            ucut.clear();
            return rows;
        }

        /** Independent oracle: fresh bounds every frame, identical hide formula. */
        private static function oracleHidden(child:DisplayObject,visual:DisplayObject,cam:Object):Boolean {
            var scale:Number=cam.scaleV;
            var left:Number=-cam.vx/scale-320,top:Number=-cam.vy/scale-320;
            var right:Number=left+cam.screenX/scale+640,bottom:Number=top+cam.screenY/scale+640;
            var b:Rectangle=child.getBounds(visual);
            if(b.width<=0 && b.height<=0)return false;
            return !(b.right+240>=left && b.left-240<=right && b.bottom+240>=top && b.top-240<=bottom);
        }

        private static function makeWorld(type:Class,small:int=0):Object {
            var visual:Sprite=new Sprite();
            var layers:Array=[new Sprite(),new Sprite(),new Sprite()];
            for(var l:int=0;l<layers.length;++l)visual.addChild(layers[l]);
            var roots:Array=[],empty:Array=[],rng:Object=seedRng(0xC0FFEE);
            var count:int=small>0?1:24;
            for(var i:int=0;i<count;++i) {
                var layer:Sprite=layers[i%layers.length];
                var root:Sprite=new Sprite();
                root.name="root"+i;
                root.x=randomIn(rng,-900,900);root.y=randomIn(rng,-600,600);
                if(i%6==0)root.scaleX=-1;          // pre-existing mirror
                if(i%5==0)root.scaleY=0.8;
                drawArt(root,10,6,randomIn(rng,8,60),randomIn(rng,8,60));
                layer.addChild(root);roots.push(root);
            }
            // Geometry-free roots are never culled, however far they travel.
            var emptyRoot:Sprite=new Sprite();emptyRoot.x=-2000;emptyRoot.y=-2000;
            layers[0].addChild(emptyRoot);roots.push(emptyRoot);empty.push(emptyRoot);
            // A lurk exclusion exercises the documented exception with the cache active.
            var lurk:Sprite=new Sprite();drawArt(lurk,4,4,20,20);layers[1].addChild(lurk);
            var w:Object={visual:visual,loc:{objs:[{lurk:1,vis:lurk}]},
                grafon:{sceneLarge:true,visObjs:layers},
                gg:{teleObj:null},cam:{vx:0,vy:0,scaleV:1,screenX:1000,screenY:600}};
            return {visual:visual,layers:layers,roots:roots,empty:empty,w:w,cut:new type()};
        }

        /** Off-centre art: a mirror must swap the edges, not the box. */
        private static function drawArt(root:Sprite,artX:Number,artY:Number,width:Number,height:Number):void {
            while(root.numChildren)root.removeChildAt(0);
            var art:Sprite=new Sprite();
            art.graphics.beginFill(0x88ccff);art.graphics.drawRect(artX,artY,width,height);art.graphics.endFill();
            root.addChild(art);
        }

        /** Returns how many roots changed transform this frame. */
        private static function mutate(roots:Array,rng:Object):int {
            var changed:int=0;
            for(var i:int=0;i<roots.length;++i) {
                var root:Sprite=roots[i] as Sprite;
                if(!root || root.numChildren==0)continue;   // empty roots keep their place
                var roll:Number=nextRandom(rng);
                if(roll<0.34){root.scaleX=root.scaleX>0?-1:1;++changed;}                 // turn: pure mirror
                else if(roll<0.46){root.scaleX=(nextRandom(rng)<0.5?-1:1)*randomIn(rng,0.4,2.2);++changed;}
                else if(roll<0.54){root.scaleY=(nextRandom(rng)<0.5?-1:1)*randomIn(rng,0.4,2.2);++changed;}
                else if(roll<0.60){root.rotation=(nextRandom(rng)<0.3)?45:0;++changed;}
                else if(roll<0.88){root.x=randomIn(rng,-1400,1400);root.y=randomIn(rng,-900,900);++changed;}
                // else: untouched this frame
            }
            return changed;
        }
        private static function moveCamera(world:Object,rng:Object):void {
            world.w.cam.vx=randomIn(rng,-1200,1200);
            world.w.cam.vy=randomIn(rng,-700,700);
        }

        // Deterministic xorshift32 so a failure is reproducible from the seed.
        private static function seedRng(seed:uint):Object {
            return {state:seed==0?0x9E3779B9:seed};
        }
        private static function nextRandom(rng:Object):Number {
            var s:uint=uint(rng.state);
            s^=s<<13;s^=s>>>17;s^=s<<5;
            rng.state=s;
            return (s>>>0)/4294967296;
        }
        private static function randomIn(rng:Object,min:Number,max:Number):Number {
            return min+(max-min)*nextRandom(rng);
        }
    }
}
