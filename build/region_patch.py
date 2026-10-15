"""Attach regional native raster styles after ContinuousScene's base patches.

SceneRegions uses the native Location.colorFilter parser and clips each style
in world coordinates. It does not recolor gameplay objects or change lighting
visibility, collision, interaction, or other room options.
"""
from pathlib import Path


def _replace(source, old, new, count=1):
    actual = source.count(old)
    if actual != count:
        raise RuntimeError(
            f"Scene region anchor mismatch: expected {count}, got {actual}: {old[:120]}"
        )
    return source.replace(old, new)


def apply_location(location):
    anchor = "World.w.grafon.sceneTrack(this,String(param2.@sceneRevision));"
    return _replace(
        location,
        anchor,
        anchor + "\n         World.w.grafon.sceneSetRegions(this,param2);",
    )


def apply_grafon(grafon):
    extension = (
        Path(__file__).resolve().parents[1] / "src/patches/SceneRegions.as.inc"
    ).read_text(encoding="utf-8")
    # scenePrepare is also called inside every regional raster pass, where
    # Location temporarily has that region's color. Synchronize only at the
    # outer sceneOpen entry, before clearing/recreating resident surfaces.
    grafon = _replace(
        grafon,
        "      private function sceneOpen(value:Location) : void\n      {\n",
        "      private function sceneOpen(value:Location) : void\n      {\n"
        "         this.sceneSyncRegionLighting(value);\n",
    )
    grafon = _replace(
        grafon,
        "try { this.drawLoc(this.loc); }",
        "try { this.sceneDrawRegionChunk(); }",
    )
    grafon = _replace(
        grafon,
        "         this.sceneChunks = {}; this.sceneResident = 0;",
        "         this.sceneChunks = {}; this.sceneResident = 0;\n"
        "         this.sceneRegionClearScratch();",
    )
    grafon = _replace(
        grafon,
        "               var action:Function = this[kind]; action.apply(this,args);",
        "               this.sceneApplyRegionAction(kind,args,affected);",
    )
    # decal_patch has already added the cached world bounds at item[3]. During
    # a region raster pass the helper preserves that pass's native color; the
    # enclosing compositor performs the exact region clip once.
    grafon = _replace(
        grafon,
        "               var action:Function = this[item[0]]; action.apply(this,item[1]);",
        "               this.sceneApplyRegionAction(String(item[0]),item[1],"
        "item.length > 3 ? item[3] as Rectangle : null);",
    )
    # Insert helpers after editing original call sites: the helpers deliberately
    # invoke the same native drawLoc method and may contain identical phrases.
    anchor = "      public function Grafon(param1:Sprite)"
    return _replace(grafon, anchor, extension + anchor)
