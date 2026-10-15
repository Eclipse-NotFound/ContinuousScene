"""Narrow fixes for native camera controls and scene viewport coordinates.

Call these helpers after prepare.py's existing ContinuousScene transformations.
Only the named anchors may change; a missing/duplicated anchor aborts the build.
The ordinary-room branches retain their existing scale and background rules.
"""


def _replace(source, old, new, *, count=1):
    actual = source.count(old)
    if actual != count:
        raise RuntimeError(
            f"Render/camera anchor mismatch: expected {count}, got {actual}: {old[:120]}"
        )
    return source.replace(old, new)


def apply_camera(camera):
    """Restore 0/1/2 cycling, using native room zoom levels in a large scene.

    maxsx/maxsy and all camera limits remain the actual scene dimensions. Only
    the two fit-to-room scale denominators use the original 1920 x 1000 room.
    """
    camera = _replace(
        camera,
        "if(World.w.loc && (World.w.loc.spaceX > World.cellsX || World.w.loc.spaceY > World.cellsY)) this.isZoom = 0;\n         ",
        "",
    )
    camera = _replace(
        camera,
        "public function setZoom(param1:int = -1000) : *\n      {",
        "public function setZoom(param1:int = -1000) : *\n      {\n"
        "         var sceneLarge:Boolean = World.w.loc != null && "
        "(World.w.loc.spaceX > World.cellsX || World.w.loc.spaceY > World.cellsY);",
    )
    camera = _replace(
        camera,
        "Math.max(this.screenX / this.maxsx,this.screenY / this.maxsy)",
        "Math.max(this.screenX / (sceneLarge ? 1920 : this.maxsx),"
        "this.screenY / (sceneLarge ? 1000 : this.maxsy))",
    )
    camera = _replace(
        camera,
        "Math.min(this.screenX / this.maxsx,this.screenY / this.maxsy)",
        "Math.min(this.screenX / (sceneLarge ? 1920 : this.maxsx),"
        "this.screenY / (sceneLarge ? 1000 : this.maxsy))",
    )
    return camera


def apply_grafon(grafon):
    """Keep background and visible world bounds independent of chunk buffers."""
    grafon = _replace(
        grafon,
        "         this.sceneEnsure(-World.w.cam.vx,-World.w.cam.vy,World.w.cam.screenX,World.w.cam.screenY);\n"
        "         World.w.cam.setZoom(0);",
        "         var camera:* = World.w.cam;\n"
        "         var scale:Number = camera.scaleV > 0 ? camera.scaleV : 1;\n"
        "         this.sceneEnsure(-camera.vx / scale,-camera.vy / scale,"
        "camera.screenX / scale,camera.screenY / scale);",
    )
    # Large scenes use the existing viewport-covering branch. rectX/rectY are
    # 400px scratch buffers there, not the dimensions of the sky/background.
    grafon = _replace(
        grafon,
        "if(param1 > this.rectX && param2 > this.rectY)",
        "if(!this.sceneLarge && param1 > this.rectX && param2 > this.rectY)",
    )
    return grafon


def apply_vision(source):
    """Fix fog bounds and repaint newly exposed pixels without recomputing FOV.

    applyVision receives the already computed logical visibility field. Camera
    motion only refreshes its pixel cache and unit-mask cache version; it does
    not call computeFov or alter the logical exploration/interaction rules.
    """
    source = _replace(
        source,
        "         var camera:* = world.cam;\n"
        "         var left:int = Math.max(0,Math.floor(-camera.vx / Tile.tileX) - 4);\n"
        "         var top:int = Math.max(0,Math.floor(-camera.vy / Tile.tileY) - 4);\n"
        "         var right:int = Math.min(this.spaceX,Math.ceil((-camera.vx + camera.screenX) / Tile.tileX) + 4);\n"
        "         var bottom:int = Math.min(this.spaceY,Math.ceil((-camera.vy + camera.screenY) / Tile.tileY) + 4);",
        "         var camera:* = world.cam;\n"
        "         var scale:Number = camera.scaleV > 0 ? camera.scaleV : 1;\n"
        "         var left:int = Math.max(0,Math.floor(-camera.vx / scale / Tile.tileX) - 4);\n"
        "         var top:int = Math.max(0,Math.floor(-camera.vy / scale / Tile.tileY) - 4);\n"
        "         var right:int = Math.min(this.spaceX,Math.ceil((-camera.vx + camera.screenX) / scale / Tile.tileX) + 4);\n"
        "         var bottom:int = Math.min(this.spaceY,Math.ceil((-camera.vy + camera.screenY) / scale / Tile.tileY) + 4);",
    )
    source = _replace(
        source,
        "      private var fogDirty:Boolean = false;",
        "      private var fogDirty:Boolean = false;\n"
        "      private var scenePaintLoc:Location = null;\n"
        "      private var sceneLastPaintBounds:Rectangle = null;",
    )
    source = _replace(
        source,
        "         var sceneLarge:Boolean = this.spaceX > 48 || this.spaceY > 25;\n"
        "         var scenePixelBounds:Rectangle",
        "         var sceneLarge:Boolean = this.spaceX > 48 || this.spaceY > 25;\n"
        "         var sceneViewChanged:Boolean = sceneLarge && "
        "(this.scenePaintLoc !== loc || this.sceneLastPaintBounds == null || "
        "!this.sceneLastPaintBounds.equals(sceneBounds));\n"
        "         if(sceneLarge)\n"
        "         {\n"
        "            this.scenePaintLoc = loc; this.sceneLastPaintBounds = sceneBounds;\n"
        "            if(sceneViewChanged)\n"
        "            {\n"
        "               this.fogDirty = true; this.fogBlurPending = true;\n"
        "               if(!needFov) ++this.fovVersion;\n"
        "            }\n"
        "         }\n"
        "         var scenePixelBounds:Rectangle",
    )
    source = _replace(
        source,
        "if(wallChanged && !needFov)",
        "if(wallChanged && !needFov && !sceneViewChanged)",
    )
    source = _replace(
        source,
        "         if(needFov)\n         {\n            this.fillFogCache(loc);",
        "         if(needFov || sceneViewChanged)\n         {\n            this.fillFogCache(loc);",
    )
    return source
