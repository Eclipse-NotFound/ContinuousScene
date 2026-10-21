package tests {
    import flash.display.MovieClip;
    import flash.filters.BlurFilter;
    import flash.filters.GlowFilter;
    /** One-frame wrapper retaining the native child's fixed artwork. */
    public final class SceneImpactFilteredPaint extends MovieClip {
        public function SceneImpactFilteredPaint() {
            var art:MovieClip=new SceneDecalCrackPaint();
            art.filters=[new GlowFilter(0xD08040,.7,10,8,1,2),new BlurFilter(4,6,2)];
            addChild(art);
        }
    }
}
