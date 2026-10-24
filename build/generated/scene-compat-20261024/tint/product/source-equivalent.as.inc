// scene-player-region-tint-2, applied to exact ABE2 Grafon only.
// The executable recipe is audit.py; the original class is never recompiled.
// sceneUpdateEntityColor: change only the levit part of displayOwned:
// (target.levit == 0 || target === World.w.gg)

private function sceneEntitySameColor(a:ColorTransform, b:ColorTransform):Boolean
{
    if(a == null || b == null) return false;
    if(a.redMultiplier == b.redMultiplier && a.greenMultiplier == b.greenMultiplier
        && a.blueMultiplier == b.blueMultiplier && a.alphaMultiplier == b.alphaMultiplier
        && a.redOffset == b.redOffset && a.greenOffset == b.greenOffset
        && a.blueOffset == b.blueOffset && a.alphaOffset == b.alphaOffset) return true;
    if(!isFinite(b.redMultiplier) || !isFinite(b.greenMultiplier)
        || !isFinite(b.blueMultiplier) || !isFinite(b.alphaMultiplier)
        || !isFinite(b.redOffset) || !isFinite(b.greenOffset)
        || !isFinite(b.blueOffset) || !isFinite(b.alphaOffset)) return false;
    var normalizer:Sprite = new Sprite();
    normalizer.transform.colorTransform = b;
    b = normalizer.transform.colorTransform;
    return a.redMultiplier == b.redMultiplier && a.greenMultiplier == b.greenMultiplier
        && a.blueMultiplier == b.blueMultiplier && a.alphaMultiplier == b.alphaMultiplier
        && a.redOffset == b.redOffset && a.greenOffset == b.greenOffset
        && a.blueOffset == b.blueOffset && a.alphaOffset == b.alphaOffset;
}
