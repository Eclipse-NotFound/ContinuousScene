"""Refresh native region base colors at existing entity display update points.

No entity scans, gameplay changes, or extra methods on Unit/Box are required.
Call apply_grafon after region_patch; apply_unit/apply_box accept native sources.
"""
from pathlib import Path


def _replace(source, old, new):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Entity color anchor expected once, got {count}: {old[:120]}")
    return source.replace(old, new)


def apply_unit(source):
    anchor = (
        "      public function setVisPos() : *\n"
        "      {\n"
        "         if(vis)\n"
        "         {\n"
        "            vis.x = X;"
    )
    return _replace(
        source,
        anchor,
        anchor.replace(
            "            vis.x = X;",
            "            World.w.grafon.sceneUpdateEntityColor(this,this.hero == 0 && this.ctrans);\n"
            "            vis.x = X;",
        ),
    )


def apply_box(source):
    source = _replace(
        source,
        "            World.w.grafon.visObjs[sloy].addChild(vis);\n            if(cTransform)",
        "            World.w.grafon.visObjs[sloy].addChild(vis);\n"
        "            World.w.grafon.sceneUpdateEntityColor(this);\n            if(cTransform)",
    )
    source = _replace(
        source,
        "      public function runVis() : *\n      {\n         vis.x = this.shad.x = X;",
        "      public function runVis() : *\n      {\n"
        "         World.w.grafon.sceneUpdateEntityColor(this);\n         vis.x = this.shad.x = X;",
    )
    return source


def apply_grafon(source):
    extension = (
        Path(__file__).resolve().parents[1] / "src/patches/SceneEntityColors.as.inc"
    ).read_text(encoding="utf-8")
    anchor = "      public function Grafon(param1:Sprite)"
    return _replace(source, anchor, extension + anchor)
