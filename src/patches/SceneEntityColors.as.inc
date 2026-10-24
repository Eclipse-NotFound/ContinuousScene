      // Update the native base tint, preserving effects which temporarily own
      // the displayed tint. Weak keys never keep removed enemies/boxes alive.
      private var sceneEntityColors:Dictionary = new Dictionary(true);
      // Values must not point back to Location: it owns units/objs, which would
      // keep the entity dictionary's weak keys alive. Empty identity tokens
      // preserve ownership across redraws without retaining the old scene.
      private var sceneEntityLocationTokens:Dictionary = new Dictionary(true);
      public var sceneEntityTintChanges:int = 0;

      public function sceneUpdateEntityColor(target:Obj, eligible:Boolean = true) : void
      {
         if(!this.sceneLarge || target == null || target.loc == null || target.loc !== this.loc
            || this.sceneRegionData[target.loc] == null) return;
         if(!eligible) { delete this.sceneEntityColors[target]; return; }
         var locationToken:Object = this.sceneEntityLocationTokens[target.loc];
         if(locationToken == null)
            this.sceneEntityLocationTokens[target.loc] = locationToken = {};
         var previous:Object = this.sceneEntityColors[target];
         var original:ColorTransform = target.cTransform;
         // A hero or another mod can own cTransform itself. Only the native
         // Location reference and our last assigned reference are ours to edit.
         if(original !== target.loc.cTransform &&
            (previous == null || previous.locationToken !== locationToken || original !== previous.base)) return;
         var worldX:Number = target.X;
         var worldY:Number = target.Y - target.scY / 2;
         var region:Object = previous != null && previous.locationToken === locationToken ? previous.region : null;
         if(region == null || !region.bounds.contains(worldX,worldY))
            region = this.sceneRegionStyle(target.loc,worldX,worldY);
         var desired:ColorTransform = region == null ? target.loc.cTransform : region.cTransform;
         if(previous == null || previous.locationToken !== locationToken)
            this.sceneEntityColors[target] = previous = {locationToken:locationToken,base:original,region:region};
         previous.region = region;
         if(original === desired) { previous.base = desired; return; }
         var highlighted:Boolean = World.w.shineObjs && World.w.gui != null && World.w.gui.celObj === target;
         // Player hover owns inner filters, not the root tint. Telekinetically
         // held non-player objects still keep their temporary root color.
         var displayOwned:Boolean = target.vis != null && (target.levit == 0 || target === World.w.gg) && !highlighted
            && this.sceneEntitySameColor(target.vis.transform.colorTransform,original);
         target.cTransform = desired;
         previous.base = desired;
         ++this.sceneEntityTintChanges;
         if(displayOwned) target.vis.transform.colorTransform = desired;
         // Native Weapon.addVisual reads owner.cTransform, so changing weapons
         // already inherits the new base. Here only an existing plain weapon
         // needs an immediate update; magical/tinted effects retain ownership.
         var object:* = target;
         if("currentWeapon" in object)
         {
            var weapon:* = object.currentWeapon;
            if(weapon != null && weapon.tip != 5 && weapon.vis != null
               && this.sceneEntitySameColor(weapon.vis.transform.colorTransform,original))
               weapon.vis.transform.colorTransform = desired;
         }
      }

      private function sceneEntitySameColor(a:ColorTransform, b:ColorTransform) : Boolean
      {
         if(a == null || b == null) return false;
         // Keep the exact fast path; a display transform is a value copy and
         // AIR also quantizes its components when storing the logical tint.
         if(a.redMultiplier == b.redMultiplier && a.greenMultiplier == b.greenMultiplier
            && a.blueMultiplier == b.blueMultiplier && a.alphaMultiplier == b.alphaMultiplier
            && a.redOffset == b.redOffset && a.greenOffset == b.greenOffset
            && a.blueOffset == b.blueOffset && a.alphaOffset == b.alphaOffset) return true;
         if(!isFinite(b.redMultiplier) || !isFinite(b.greenMultiplier)
            || !isFinite(b.blueMultiplier) || !isFinite(b.alphaMultiplier)
            || !isFinite(b.redOffset) || !isFinite(b.greenOffset)
            || !isFinite(b.blueOffset) || !isFinite(b.alphaOffset)) return false;
         // Normalize through the runtime itself, without an epsilon that could
         // claim another effect's color. This Sprite never enters the display tree.
         var normalizer:Sprite = new Sprite();
         normalizer.transform.colorTransform = b;
         b = normalizer.transform.colorTransform;
         return a.redMultiplier == b.redMultiplier && a.greenMultiplier == b.greenMultiplier
            && a.blueMultiplier == b.blueMultiplier && a.alphaMultiplier == b.alphaMultiplier
            && a.redOffset == b.redOffset && a.greenOffset == b.greenOffset
            && a.blueOffset == b.blueOffset && a.alphaOffset == b.alphaOffset;
      }
