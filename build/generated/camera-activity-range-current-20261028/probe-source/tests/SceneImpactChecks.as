package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.MovieClip;
    import flash.geom.ColorTransform;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;
    import flash.utils.getDefinitionByName;

    /** TERMINAL, isolated probe only. Private decal/warm history is deliberately
     * not edited. The caller must prevent deactivation saves and exit afterwards.
     * Both paths see identical native surface pixels, origins and fixed artwork.
     */
    public class SceneImpactChecks {
        public static function run(w:*,check:Function):Object {
            var id:String=NativeApplication.nativeApplication.applicationID;
            var isolated:Boolean=id.indexOf("pfe-modsettings-continuous-motion-")==0 &&
                id.length>"pfe-modsettings-continuous-motion-".length+7;
            check("impact-isolated-unique-id",isolated,id);
            if(!isolated) throw new Error("Impact checks require unique isolated AIR storage");
            var g:*=w ? w.grafon : null;
            var switchName:String=g && ("sceneImpactArtEnabled" in g) ? "sceneImpactArtEnabled" :
                g && ("sceneImpactTightEnabled" in g) ? "sceneImpactTightEnabled" :
                g && ("sceneImpactBufferEnabled" in g) ? "sceneImpactBufferEnabled" : "sceneDecalClipEnabled";
            var ready:Boolean=w && w.loc && g && g.sceneLarge && (switchName in g);
            check("impact-host-contract",ready);
            if(!ready) throw new Error("Large scene with sceneDecalClipEnabled is required");
            var oldSwitch:Boolean=g[switchName];
            var oldDirty:int=g.sceneLastDirtyCount;
            var oldColor:ColorTransform=w.loc.cTransform;
            var records:Array=[],surfaces:Array=g.sceneSurfaces();
            var result:Object={terminalOnly:true,applicationID:id,cases:[],benchmark:[],
                comparison:"exact BitmapData.compare == 0 on every resident front surface",control:switchName,
                version:("sceneImpactVersion" in g)?g.sceneImpactVersion:null,
                history:"Private sceneMarks and cancelled warm jobs remain. Exit without saving, travel or redraw.",
                timing:"Only 100 g.decal calls; excludes prepare, clones, comparisons and restoration."};
            var expected:Object=null;
            try {
                if(!surfaces.length) throw new Error("No resident surfaces");
                for each(var surface:Object in surfaces) {
                    var front:BitmapData=surface.nativeBuffers[0];
                    records.push({surface:surface,target:front,data:front.clone(),revision:surface.revision});
                }
                var anchor:Object=corner(surfaces,w.gg.X,w.gg.Y);
                check("impact-resident-four-way-corner",anchor!=null,anchor);
                if(!anchor) throw new Error("Need four resident neighbouring chunks");
                result.anchor=anchor;result.surfaces=records.length;
                var x:Number=anchor.x,y:Number=anchor.y;
                var nativeCut:Class=getDefinitionByName("bullet_dyr") as Class;
                var nativePaint:Class=getDefinitionByName("bullet_metal") as Class;
                check("impact-native-single-frame-fixture",new nativeCut().totalFrames==1 && new nativePaint().totalFrames==1);
                var cases:Array=[
                    {name:"native-reuse-corner",cut:nativeCut,paint:nativePaint,x:x+.25,y:y+.5,scale:2.35,angle:.71,blend:"normal",pattern:true,cross:true},
                    {name:"native-reuse-mirrored",cut:nativeCut,paint:nativePaint,x:x-.5,y:y+.75,scale:-3.25,angle:-.47,blend:"hardlight",pattern:true,cross:true},
                    {name:"native-reuse-region",cut:nativeCut,paint:nativePaint,x:1920.5,y:1000.25,scale:2.35,angle:.71,blend:"normal",pattern:true},
                    {name:"native-front-small",cut:null,paint:SceneDecalMetalPaint,x:x,y:y,scale:1,angle:0,blend:"normal",pattern:false},
                    {name:"small-corner",cut:null,paint:SceneDecalMetalPaint,x:x,y:y,scale:1,angle:0,blend:"normal",pattern:true,cross:true},
                    {name:"cut-paint-quarter",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:x+.25,y:y+.5,scale:2.35,angle:.71,blend:"hardlight",pattern:true,cross:true},
                    {name:"mirrored-half",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:x-.5,y:y+.75,scale:-3.25,angle:-.47,blend:"hardlight",pattern:true,cross:true},
                    {name:"cut-only-three-quarters",cut:SceneDecalBulletCut,paint:null,x:x+.75,y:y-.25,scale:1.7,angle:.37,blend:"normal",pattern:true},
                    {name:"filtered-paint",cut:null,paint:SceneImpactFilteredPaint,x:x+.5,y:y+.25,scale:1.5,angle:.29,blend:"normal",pattern:true},
                    {name:"region-boundary-normal",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:1920.5,y:1000.25,scale:2.35,angle:.71,blend:"normal",pattern:true},
                    {name:"region-boundary-hardlight",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:1919.5,y:999.75,scale:-2.35,angle:-.47,blend:"hardlight",pattern:true},
                    {name:"world-origin",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:.25,y:.5,scale:2.35,angle:.71,blend:"hardlight",pattern:true}
                ];
                for each(var nativeName:String in ["fire_soft","laser_tre","plasma_dyr","plasma_tre","bluplasma_tre",
                    "pinkplasma_tre","cryo_soft","block_plav","block_pla","block_bur"]) {
                    var nativeFactory:Class=getDefinitionByName(nativeName) as Class;
                    check("impact-native-single-frame-"+nativeName,new nativeFactory().totalFrames==1);
                    cases.push({name:"native-reuse-"+nativeName,cut:nativeCut,paint:nativeFactory,x:x+.25,y:y+.5,
                        scale:1.35,angle:.71,blend:"hardlight",pattern:true});
                }
                var explosion:MovieClip=new SceneDecalExplosionPaint();
                var bounds:Rectangle=explosion.getBounds(explosion);
                var span:Number=Math.max(bounds.width,bounds.height);
                if(span<=0) throw new Error("Empty explosion artwork");
                cases.push({name:"large-explosion-fallback",cut:null,paint:SceneDecalExplosionPaint,
                    x:x+.5,y:y+.75,scale:Math.max(8,1400/span),angle:.36,blend:"hardlight",pattern:true,
                    expectedLargeFallback:true});
                var changedCases:int=0;
                for each(var test:Object in cases) {
                    prepare(records,test.pattern);w.loc.cTransform=oldColor;g[switchName]=false;
                    draw(g,test);expected=capture(records,g.sceneLastDirtyCount);
                    prepare(records,test.pattern);w.loc.cTransform=oldColor;g[switchName]=true;
                    draw(g,test);
                    var compared:Object=compare(records,expected,g.sceneLastDirtyCount);
                    compared.name=test.name;compared.pattern=test.pattern;
                    compared.oldChangedSurfaces=expected.changed;compared.oldDirty=expected.dirty;
                    compared.expectedLargeFallback=Boolean(test.expectedLargeFallback);
                    result.cases.push(compared);
                    check("impact-"+test.name+"-pixels",compared.pixelMismatches==0,compared);
                    check("impact-"+test.name+"-revisions",compared.revisionMismatches==0 && compared.dirtyMatches,compared);
                    check("impact-"+test.name+"-resident-dispatch",expected.dirty>0,expected.dirty);
                    if(test.cross) check("impact-"+test.name+"-gutter-neighbours",expected.dirty>=4,expected.dirty);
                    if(expected.changed>0) ++changedCases;
                    dispose(expected);expected=null;
                }
                check("impact-nonempty-pixel-coverage",changedCases>0,{changedCases:changedCases,total:cases.length});
                // Fixed frames prevent random selection of different artwork.
                // Warm both paths, then ABBA/BAAB counterbalances timer/GC drift.
                // Reset pixels and revisions outside every timed window.
                var sequence:Array=[];
                for(var i:int=0;i<100;++i) sequence.push({cut:nativeCut,paint:nativePaint,
                    x:x+(i%10)*18.25-82.125,y:y+int(i/10)*17.75-79.875,
                    scale:1,angle:(i%4)*.11,blend:"hardlight"});
                for(var warm:int=0;warm<2;++warm) {
                    prepare(records,true);g[switchName]=warm==1;
                    for(i=0;i<25;++i)draw(g,sequence[i]);
                }
                var modes:Array=[false,true,true,false,true,false,false,true];
                for(var pass:int=0;pass<modes.length;++pass) {
                    prepare(records,true);w.loc.cTransform=oldColor;g[switchName]=modes[pass];
                    var started:int=getTimer();
                    for(i=0;i<sequence.length;++i) {
                        var mark:Object=sequence[i];
                        g.decal(mark.cut,mark.paint,mark.x,mark.y,mark.scale,mark.angle,mark.blend);
                    }
                    var elapsed:int=getTimer()-started;
                    var row:Object={pass:pass,mode:modes[pass]?"candidate":"original",calls:100,ms:elapsed,
                        front:"same controlled alpha pattern",art:"native bullet_dyr + bullet_metal (both single-frame), hardlight"};
                    if(!expected) expected=capture(records,g.sceneLastDirtyCount);
                    else {
                        row.comparison=compare(records,expected,g.sceneLastDirtyCount);
                        check("impact-abba-"+pass+"-pixels",row.comparison.pixelMismatches==0,row.comparison);
                        check("impact-abba-"+pass+"-revisions",row.comparison.revisionMismatches==0 && row.comparison.dirtyMatches,row.comparison);
                    }
                    result.benchmark.push(row);
                }
                check("impact-resident-identity",g.sceneSurfaces().length==records.length);
            } finally {
                if(expected) dispose(expected);
                try {
                    prepare(records,false,false);
                    for each(var record:Object in records) record.data.dispose();
                } finally {
                    g[switchName]=oldSwitch;g.sceneLastDirtyCount=oldDirty;w.loc.cTransform=oldColor;
                }
            }
            check("impact-terminal-only",true,result.history);
            return result;
        }

        private static function draw(g:*,test:Object):void {
            g.decal(test.cut,test.paint,test.x,test.y,test.scale,test.angle,test.blend);
        }

        private static function corner(surfaces:Array,px:Number,py:Number):Object {
            var byKey:Object={},best:Object=null,distance:Number=Number.MAX_VALUE;
            for each(var s:Object in surfaces) byKey[s.cx+":"+s.cy]=s;
            for each(s in surfaces) {
                if(s.side!=320 || !byKey[(s.cx+1)+":"+s.cy] || !byKey[s.cx+":"+(s.cy+1)] ||
                    !byKey[(s.cx+1)+":"+(s.cy+1)]) continue;
                var x:Number=(s.cx+1)*s.side,y:Number=(s.cy+1)*s.side;
                var d:Number=(x-px)*(x-px)+(y-py)*(y-py);
                if(d<distance) {distance=d;best={x:x,y:y,side:s.side,gutter:s.gutter};}
            }
            return best;
        }

        private static function prepare(records:Array,pattern:Boolean,keepBaseline:Boolean=true):void {
            var zero:Point=new Point();
            for each(var record:Object in records) {
                var s:Object=record.surface,b:BitmapData=record.target;
                if(record.before) {record.before.dispose();record.before=null;}
                b.copyPixels(record.data,record.data.rect,zero);
                s.revision=record.revision;
                if(!pattern) {
                    if(keepBaseline) record.before=b.clone();
                    continue;
                }
                // World-periodic alpha edges: overlapping gutters receive the
                // same input. Restored from actual game pixels on every exit.
                b.fillRect(b.rect,0xFFA6B4C2);
                var stripe:int=int(Math.floor((s.x-50)/80))*80+50;
                for(;stripe<s.x+b.width;stripe+=80) b.fillRect(new Rectangle(stripe-s.x,0,4,b.height),0);
                stripe=int(Math.floor((s.y-60)/80))*80+60;
                for(;stripe<s.y+b.height;stripe+=80) b.fillRect(new Rectangle(0,stripe-s.y,b.width,3),0x70A6B4C2);
                // Place partial-alpha samples directly on every chunk boundary.
                stripe=int(Math.floor(s.x/80))*80;
                for(;stripe<s.x+b.width;stripe+=80) b.fillRect(new Rectangle(stripe-s.x,0,2,b.height),0x40C284A6);
                if(keepBaseline) record.before=b.clone();
            }
        }

        private static function capture(records:Array,dirty:int):Object {
            var result:Object={items:[],dirty:dirty,changed:0};
            for each(var record:Object in records) {
                var b:BitmapData=record.target;
                // Revision changes are always checked separately from pixels.
                var delta:*=b.compare(record.before);
                if(delta!==0) ++result.changed;
                if(delta is BitmapData) delta.dispose();
                result.items.push({data:b.clone(),revision:record.surface.revision-record.revision});
            }
            return result;
        }

        private static function compare(records:Array,expected:Object,dirty:int):Object {
            var result:Object={surfaces:records.length,pixelMismatches:0,revisionMismatches:0,
                dirtyMatches:dirty==expected.dirty,dirty:dirty,mismatches:[]};
            for(var i:int=0;i<records.length;++i) {
                var record:Object=records[i],prior:Object=expected.items[i];
                var diff:*=record.target.compare(prior.data);
                if(diff!==0) {
                    ++result.pixelMismatches;
                    if(result.mismatches.length<12) result.mismatches.push({cx:record.surface.cx,cy:record.surface.cy,
                        bounds:diff is BitmapData?diff.getColorBoundsRect(0xFFFFFFFF,0,false).toString():String(diff)});
                }
                if(diff is BitmapData) diff.dispose();
                if(record.surface.nativeBuffers[0]!==record.target ||
                    record.surface.revision-record.revision!=prior.revision) ++result.revisionMismatches;
            }
            return result;
        }

        private static function dispose(snapshot:Object):void {
            for each(var item:Object in snapshot.items) item.data.dispose();
        }
    }

}
