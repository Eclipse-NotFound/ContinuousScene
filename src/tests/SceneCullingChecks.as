package tests {
    import flash.display.Sprite;
    public class SceneCullingChecks {
        public static function run(type:Class):Array {
            var rows:Array=[];
            function check(name:String,ok:Boolean):void {rows.push({name:name,ok:ok});if(!ok)throw new Error("Culling: "+name);}
            function art(x:Number):Sprite {var s:Sprite=new Sprite();s.graphics.beginFill(0xffffff);s.graphics.drawRect(0,0,20,20);s.graphics.endFill();s.x=x;return s;}
            var world:Sprite=new Sprite(),a:Sprite=new Sprite(),b:Sprite=new Sprite(),c:Sprite=new Sprite();
            world.addChild(a);world.addChild(b);world.addChild(c);
            var near:Sprite=art(0),far:Sprite=art(2000),lurk:Sprite=art(2100),empty:Sprite=new Sprite();
            a.addChild(near);a.addChild(far);b.addChild(lurk);c.addChild(empty);
            near.visible=false;near.alpha=.4;var expectedAlpha:Number=near.alpha;
            var w:Object={visual:world,loc:{objs:[{lurk:1,vis:lurk}]},grafon:{sceneLarge:true,visObjs:[a,b,c]},
                gg:{teleObj:null},cam:{vx:0,vy:0,scaleV:1,screenX:100,screenY:100}};
            var cut:*=new type();
            try {
                cut.update(w,true);
                check("native-visibility-owned",!near.visible && near.alpha==expectedAlpha);
                check("near-wrapper-visible",near.parent.visible);
                check("far-wrapper-hidden",!far.parent.visible && far.visible);
                check("lurk-direct",lurk.parent===b);
                check("empty-conservative",empty.parent.visible);
                var stable:Object=cut.stats();cut.update(w,true);
                check("no-discovery-rescan",cut.stats().layerScans==stable.layerScans);
                check("no-redundant-visibility-write",cut.stats().visibilityChanges==0);
                check("capture-reveals",cut.suspendForCapture() && far.parent.visible && !near.visible);
                cut.resumeFromCapture();check("capture-restores",!far.parent.visible);
                far.x=0;cut.update(w,true);check("teleport-visible",far.parent.visible);
                far.x=2000;cut.update(w,true);check("move-away-hidden",!far.parent.visible);
                w.gg.teleObj={vis:far};cut.update(w,true);check("telekinesis-direct",far.parent===a && far.visible);
                w.gg.teleObj=null;cut.update(w,true);check("telekinesis-retracked",far.parent!==a && !far.parent.visible);
                var born:Sprite=art(2300);c.addChild(born);cut.update(w,true);
                check("new-root-tracked",born.parent!==c && !born.parent.visible);
                var count:int=cut.stats().tracked;born.parent.removeChild(born);cut.update(w,true);
                check("removed-root-released",cut.stats().tracked==count-1 && born.parent==null);
                c.addChild(far);cut.update(w,true);check("reparent-preserved",far.parent.parent===c);
                far.scaleX=-200;cut.update(w,true);check("transform-remeasured",far.parent.visible);
                var inner:Sprite=art(5000);near.addChild(inner);cut.update(w,true);
                check("nested-animation-not-root",inner.parent===near);
                cut.update(w,true,true);check("units-only-restores-other-layers",near.parent===a && !near.visible);
                var replacement:Sprite=new Sprite();world.addChild(replacement);w.grafon.visObjs[2]=replacement;
                cut.update(w,true);check("same-array-layer-replaced",far.parent===c);
                cut.update(w,false);check("disable-restores",near.parent===a && empty.parent===c);
                cut.update(w,true);w.loc={objs:[]};cut.update(w,true);
                check("location-rebind",cut.stats().tracked>0 && !near.visible);
            } finally {cut.clear();}
            check("clear-native-state",near.parent===a && !near.visible && near.alpha==expectedAlpha);
            return rows;
        }
    }
}
