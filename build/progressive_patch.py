"""Generate the whole logical world; prepare only upcoming raster surfaces."""
from pathlib import Path
from render_camera_patch import _replace


def apply_grafon(source):
    # Native drawLoc initializes the room borders; camera.setZoom then points
    # the left/top rectangles outwards. Rasterizing a later chunk must not
    # overwrite that camera state or it paints a 200px strip over the world.
    begin = source.index('            this.ramT.x = this.ramB.x = -50;')
    end = source.index('            World.w.gr_stage = 3;', begin)
    borders = source[begin:end]
    assert len(borders.strip().splitlines()) == 10
    source = source[:begin] + '            if(!this.sceneRepaint) this.sceneConfigureBorders();\n' + source[end:]
    helper = '      private function sceneConfigureBorders():void\n      {\n' + borders + '      }\n\n'
    source = _replace(source, '      public function Grafon(param1:Sprite)', helper + '      public function Grafon(param1:Sprite)')
    source = _replace(source,
        '         this.sceneEnsure(left,top,World.w.swfStage.stageWidth,World.w.swfStage.stageHeight,true);',
        '         if(this.scenePreload) this.sceneEnsure(left,top,World.w.swfStage.stageWidth,World.w.swfStage.stageHeight,true);')
    source = _replace(source,
        '         var minX:int = Math.max(0,int(Math.floor(left / this.sceneSide)));',
        '         this.sceneEnsureUpcoming(left,top,width,height); return;\n'
        '         var minX:int = Math.max(0,int(Math.floor(left / this.sceneSide)));')
    # Retire the old streaming implementation, including its destructive eviction
    # sweep. Previously generated surfaces now remain until the native redraw.
    start = source.index('         this.sceneEnsureUpcoming(left,top,width,height); return;')
    end = source.index('      public function sceneTick()', start)
    source = source[:start] + '         this.sceneEnsureUpcoming(left,top,width,height);\n      }\n\n' + source[end:]
    source = _replace(source, '         this.sceneCullKey = "";',
                      '         this.sceneCullKey = ""; this.sceneUpcomingReady = false; this.sceneNextWarm = 0;')
    source = _replace(source,
        '         this.sceneEnsure(-camera.vx / scale,-camera.vy / scale,camera.screenX / scale,camera.screenY / scale);',
        '         this.sceneEnsure((-camera.vx-camera.quakeX) / scale,(-camera.vy-camera.quakeY) / scale,camera.screenX / scale,camera.screenY / scale);')
    source = _replace(source,
        '         return new Rectangle(-World.w.cam.vx / scale - 80,-World.w.cam.vy / scale - 80,\n'
        '            World.w.cam.screenX / scale + 160,World.w.cam.screenY / scale + 160);',
        '         var guard:int = this.scenePreload ? 80 : 0;\n'
        '         return new Rectangle((-World.w.cam.vx-World.w.cam.quakeX) / scale - guard,(-World.w.cam.vy-World.w.cam.quakeY) / scale - guard,\n'
        '            World.w.cam.screenX / scale + 2*guard,World.w.cam.screenY / scale + 2*guard);')
    extension = (Path(__file__).resolve().parents[1] / 'src/patches/SceneUpcoming.as.inc').read_text(encoding='utf-8')
    return _replace(source, '      public function Grafon(param1:Sprite)', extension + '      public function Grafon(param1:Sprite)')
