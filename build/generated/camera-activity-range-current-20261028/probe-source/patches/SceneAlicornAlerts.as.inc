// SOURCE-ONLY CANDIDATE, 2026-10-21. Not compiled, tested or installed.
// Replace only UnitAlicorn.budilo and UnitAlicorn.telepat method bodies.
// No production include or build recipe references this file yet.
// Approved shape: one native room centred on the sender's X/Y anchor.
// Width 48*40 = 1920; height 25*40 = 1000. Edges are inclusive.
// Applies to the active ContinuousScene renderer, including authored maps.
// It intentionally preserves native relaying, pursuit and teleport rules.

      override public function budilo(param1:Number = 500) : *
      {
         var _loc2_:Unit = null;
         // Object access avoids requiring the vanilla Grafon type to declare
         // the extension. The location checks exclude stale scene flags.
         var sceneGraph:Object = World.w != null ? World.w.grafon : null;
         var sceneBounded:Boolean = loc != null && World.w != null && World.w.loc === loc
            && sceneGraph != null && sceneGraph.loc === loc
            && ("sceneLarge" in sceneGraph) && Boolean(sceneGraph["sceneLarge"]);
         var sceneHalfWidth:Number = World.cellsX * World.tileX / 2;
         var sceneHalfHeight:Number = World.cellsY * World.tileY / 2;
         if(celUnit == null)
         {
            celX = X;
            celY = Y;
         }
         for each(_loc2_ in loc.units)
         {
            if(_loc2_ != this && _loc2_.fraction == fraction && _loc2_.sost == 1 && !_loc2_.unres)
            {
               // Measure from the caller, never the target/player, room grid,
               // camera, display scale, or the current large loc dimensions.
               if(!sceneBounded || (Math.abs(_loc2_.X - X) <= sceneHalfWidth
                  && Math.abs(_loc2_.Y - Y) <= sceneHalfHeight))
               {
                  _loc2_.alarma(celX,celY);
               }
            }
         }
      }

      public function telepat() : *
      {
         var _loc1_:Unit = null;
         var sceneGraph:Object = World.w != null ? World.w.grafon : null;
         var sceneBounded:Boolean = loc != null && World.w != null && World.w.loc === loc
            && sceneGraph != null && sceneGraph.loc === loc
            && ("sceneLarge" in sceneGraph) && Boolean(sceneGraph["sceneLarge"]);
         var sceneHalfWidth:Number = World.cellsX * World.tileX / 2;
         var sceneHalfHeight:Number = World.cellsY * World.tileY / 2;
         for each(_loc1_ in loc.units)
         {
            if(_loc1_ != this && _loc1_.fraction == fraction && _loc1_.sost == 1 && !_loc1_.unres && _loc1_.celUnit == null)
            {
               // The second broadcast path must obey the same range; leaving
               // it global would still assign the player to distant units.
               if(!sceneBounded || (Math.abs(_loc1_.X - X) <= sceneHalfWidth
                  && Math.abs(_loc1_.Y - Y) <= sceneHalfHeight))
               {
                  _loc1_.setCel(celUnit);
               }
            }
         }
      }
