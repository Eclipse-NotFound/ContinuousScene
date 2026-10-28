      private var sceneNativeEnvironments:Dictionary = new Dictionary(true);
      private var sceneNativeLast:Object;
      private var sceneRasterRegion:Object;
      private function sceneNativeBackwall(id:String, form:int) : Boolean
      {
         if(this.sceneRasterRegion == null || form == 0) return false;
         if(id == "sky") return true;
         var bounds:Rectangle = this.sceneRasterRegion.bounds;
         var texture:BitmapData = this.getObj(id);
         if(texture == null) texture = this.getObj("tBackWall");
         var sprite:Sprite = new Sprite();
         sprite.graphics.beginBitmapFill(texture);
         if(form == 1)
         {
            sprite.graphics.drawRect(bounds.x,bounds.y,11 * Tile.tileX - 10,bounds.height);
            sprite.graphics.drawRect(bounds.x + 37 * Tile.tileX + 10,bounds.y,bounds.width - 37 * Tile.tileX - 10,bounds.height);
         }
         else
         {
            var top:int = form == 2 ? 16 * Tile.tileY + 10 : 24 * Tile.tileY + 10;
            sprite.graphics.drawRect(bounds.x,bounds.y + top,bounds.width,Math.max(0,bounds.height - top));
         }
         this.backBmp.draw(sprite,this.sceneMatrix(),null,null,null,false);
         return true;
      }
      public function sceneNativeCall(kind:String, args:Array) : *
      {
         var carrier:Object = World.w.main.getChildByName("ContinuousSceneCarrier");
         if(carrier == null || carrier["nativeAPI"] == null) return null;
         var action:Function = carrier["nativeAPI"][kind];
         return action == null ? null : action.apply(null,args);
      }
      public function sceneSetNativeEnvironment(value:Location, state:Object) : void
      {
         for(var prior:Object in this.sceneNativeEnvironments)
            if(prior.land.act.id == value.land.act.id && prior !== value) delete this.sceneNativeEnvironments[prior];
         this.sceneNativeEnvironments[value] = state;
         this.sceneNativeLast = null;
      }
      public function sceneNativeEnvironment(value:Location, x:Number, y:Number) : void
      {
         var state:Object = this.sceneNativeEnvironments[value];
         if(state == null) return;
         var region:Object = state.byCell[(value.land.minLocX + int(Math.max(0,x) / 1920)) + ":" + (value.land.minLocY + int(Math.max(0,y) / 1000))];
         if(region == null || region === this.sceneNativeLast) return;
         for(var field:String in region.environment) value[field] = region.environment[field];
         this.sceneNativeLast = region;
      }
      public function sceneForgetLand(land:Object) : void
      {
         for(var i:int = this.sceneLocations.length - 1; i >= 0; --i)
         {
            var entry:Object = this.sceneLocations[i];
            if(entry.loc.land.act.id == land.act.id && entry.loc.land !== land)
            {
               delete this.sceneHistory[entry.loc]; delete this.sceneSaved[entry.key];
               this.sceneLocations.splice(i,1);
            }
         }
      }
      public function sceneResetGeneration(id:String) : void
      {
         World.w.main.dispatchEvent(new DataEvent("continuousSceneResetGeneration",false,false,id));
         for(var i:int = this.sceneLocations.length - 1; i >= 0; --i)
            if(this.sceneLocations[i].loc.land.act.id == id)
            {
               delete this.sceneHistory[this.sceneLocations[i].loc];
               this.sceneLocations.splice(i,1);
            }
         for(var key:String in this.sceneSaved)
            if(key.indexOf(id + ":") == 0) delete this.sceneSaved[key];
      }
