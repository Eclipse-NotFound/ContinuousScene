"""Native generation remains authoritative; bridge only after its constructor."""
from pathlib import Path
from render_camera_patch import _replace


def game(source):
    return _replace(source, 'this.curLand.land = new Land(World.w.gg,this.curLand,_loc2_);',
                    'if(this.crea) World.w.grafon.sceneResetGeneration(this.curLand.id);\n'
                    '            this.curLand.land = new Land(World.w.gg,this.curLand,_loc2_);\n'
                    '            World.w.grafon.sceneNativeCall("prepare",[this.curLand.land]);')


def land(source):
    source = _replace(source, '      public function setGGToSpawnPoint() : *\n      {',
                      '      public function setGGToSpawnPoint() : *\n      {\n'
                      '         if(World.w.grafon.sceneNativeCall("spawn",[this])) return;')
    source = _replace(source, '         var _loc4_:Number = this.gg.X;',
                      '         var sceneDoor:Object = World.w.grafon.sceneNativeCall("door",[this,param1,param2,param3]);\n'
                      '         if(sceneDoor != null) return sceneDoor.result;\n'
                      '         var _loc4_:Number = this.gg.X;')
    source = _replace(source, '      public function gotoProb(param1:String = "", param2:Number = -1, param3:Number = -1) : *\n      {',
                      '      public function gotoProb(param1:String = "", param2:Number = -1, param3:Number = -1) : *\n      {\n'
                      '         World.w.grafon.sceneNativeCall("coordinates",[this]);')
    return source


def location(source, method):
    def step(body):
        body = _replace(body, '         this.gg.step();',
                        '         World.w.grafon.sceneNativeEnvironment(this,this.gg.X,this.gg.Y);\n         this.gg.step();')
        body = _replace(body, '               obj.step();',
                        '               World.w.grafon.sceneNativeEnvironment(this,obj.X,obj.Y);\n               obj.step();')
        body = _replace(body, '         if(Boolean(this.unitCoord)',
                        '         World.w.grafon.sceneNativeEnvironment(this,this.gg.X,this.gg.Y);\n         if(Boolean(this.unitCoord)')
        return body
    return method(source, 'step', step)


def area(source):
    # bx/by are constructor tile coordinates. Public X/Y have been translated
    # when merging; tile effects must follow those same translated bounds.
    return source.replace('var _loc1_:* = this.bx;', 'var _loc1_:* = int(X / World.tileX);').replace(
        'var _loc3_:* = this.bx;', 'var _loc3_:* = int(X / World.tileX);').replace(
        '_loc1_ < this.bx + this.rx', '_loc1_ < int(X / World.tileX) + this.rx').replace(
        '_loc3_ < this.bx + this.rx', '_loc3_ < int(X / World.tileX) + this.rx').replace(
        '_loc2_ = this.by - this.ry + 1', '_loc2_ = int(Y / World.tileY) - this.ry').replace(
        '_loc4_ = this.by - this.ry + 1', '_loc4_ = int(Y / World.tileY) - this.ry').replace(
        '_loc2_ <= this.by', '_loc2_ < int(Y / World.tileY)').replace('_loc4_ <= this.by', '_loc4_ < int(Y / World.tileY)')


def grafon(source):
    source = _replace(source, '      public function drawBackWall(param1:String, param2:int = 0) : *\n      {',
                      '      public function drawBackWall(param1:String, param2:int = 0) : *\n      {\n'
                      '         if(this.sceneNativeBackwall(param1,param2)) return;')
    source = _replace(source, '               this.m.ty = 520;',
                      '               this.m.ty = 520;\n'
                      '               if(this.sceneRasterRegion != null) { this.m.tx += this.sceneRasterRegion.bounds.x; this.m.ty += this.sceneRasterRegion.bounds.y; }')
    extension = (Path(__file__).resolve().parents[1] / 'src/patches/SceneNativeBridge.as.inc').read_text(encoding='utf-8')
    return _replace(source, '      public function Grafon(param1:Sprite)', extension + '      public function Grafon(param1:Sprite)')
