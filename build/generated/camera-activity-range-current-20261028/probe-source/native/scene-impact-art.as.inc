      // Reuse only audited native timeline artwork, within one synchronous
      // impact. Unknown factories keep their constructor/frame-script behavior.
      public const sceneImpactVersion:String = "impact-art-1";
      public var sceneImpactArtEnabled:Boolean = true;
      private var sceneImpactArt:Array = null;

      private function sceneImpactCanReuse(factory:Class) : Boolean
      {
         return factory === bullet_dyr || factory === bullet_tre
            || factory === bullet_metal || factory === bullet_wood
            || factory === expl_tre || factory === metal_tre || factory === punch_tre
            || factory === fire_soft || factory === laser_tre || factory === plasma_dyr
            || factory === plasma_tre || factory === bluplasma_tre
            || factory === pinkplasma_tre || factory === cryo_soft || factory === plaexpl_tre
            || factory === block_plav || factory === block_pla || factory === block_bur;
      }

      private function sceneImpactGetArt(factory:Class, index:int) : MovieClip
      {
         if(!this.sceneImpactArtEnabled || this.sceneImpactArt == null || !this.sceneImpactCanReuse(factory))
            return new factory();
         var slot:Object = this.sceneImpactArt[index];
         if(slot == null)
         {
            slot = {factory:factory,art:new factory()};
            this.sceneImpactArt[index] = slot;
         }
         // Do not let an unknown/reentrant factory replace the active pair.
         if(slot.factory !== factory) return new factory();
         return slot.art as MovieClip;
      }

      private function sceneImpactSelectFrame(art:MovieClip, index:int, choice:Number) : void
      {
         var frame:int = Math.floor(choice * art.totalFrames + 1);
         var slot:Object = this.sceneImpactArt != null ? this.sceneImpactArt[index] : null;
         if(slot == null || slot.art !== art)
            art.gotoAndStop(frame);
         else if(slot.selectedFrame !== frame || art.currentFrame != frame)
         {
            art.gotoAndStop(frame);
            slot.selectedFrame = frame;
         }
      }
