package {
    import flash.display.Sprite;
    import flash.display.BitmapData;
    import flash.desktop.NativeApplication;
    import flash.geom.Rectangle;
    import fe.loc.Location;
    import fe.loc.Tile;
    import fe.unit.Unit;
    public class SceneSightHarness extends Sprite {
        private var failures:int;
        public function SceneSightHarness() {
            try { run(); } catch(e:Error) { ++failures; trace(e.getStackTrace()); }
            trace("SCENE SIGHT COMPLETE failures="+failures);
            NativeApplication.nativeApplication.exit(failures?1:0);
        }
        private function check(ok:Boolean,name:String):void { if(!ok) ++failures; trace((ok?"PASS ":"FAIL ")+name); }
        private function run():void {
            Tile.tileX=Tile.tileY=40;
            var loc:Location=new Location(); loc.spaceX=192; loc.spaceY=60;
            var m:RealisticVisionMod=new RealisticVisionMod();
            m.spaceX=192; m.spaceY=60; m.cfgMode="current";
            m.fov=[]; for(var i:int=0;i<192*60;++i) m.fov[i]=0;
            m.currentSight=new BitmapData(192*8+8,60*8+8,true,0);
            var u:Unit=new Unit(); u.X=420; u.Y=420; u.scX=u.scY=40;
            check(m.enemyState(loc,u)==0 && m.currentSightData==null,"hidden enemy does not copy whole sight map");
            var bb:Array=m.unitBBox(loc,u);
            for(var y:int=bb[1];y<=bb[3];++y) for(var x:int=bb[0];x<=bb[2];++x) m.fov[x+y*192]=2;
            var area:Rectangle=new Rectangle(4+bb[0]*8,4+bb[1]*8,(bb[2]-bb[0]+1)*8,(bb[3]-bb[1]+1)*8);
            m.currentSight.fillRect(area,0xFFFFFFFF);
            check(m.enemyState(loc,u)==1 && m.currentSightData!=null,"visible enemy gets exact current subcell snapshot");
            var snapshot:Vector.<uint>=m.currentSightData;
            check(m.enemyState(loc,u)==1 && m.currentSightData===snapshot,"same-frame units reuse snapshot");
            m.currentSight.setPixel32(area.x+1,area.y+1,0); m.currentSightData=null;
            check(m.enemyState(loc,u)==2,"changed subcell invalidates whole-visible classification");
            m.currentSight.fillRect(area,0); m.currentSightData=null;
            check(m.enemyState(loc,u)==0,"dark subcells hide enemy even with lit coarse centers");
            m.currentSight.dispose();
        }
    }
}
