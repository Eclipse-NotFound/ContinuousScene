      // Per-native-Game state; loading an older slot never reuses a newer cache.
      private var sceneGame:Object;
      private var sceneLocations:Array = [];
      private var sceneSaved:Object = {};
      private var sceneFields:Array = ["front","phis","opac","vid","vid2","hp","water","t_ghost"];

      public function sceneTrack(value:Location, revision:String) : void
      {
         if(value.spaceX <= World.cellsX && value.spaceY <= World.cellsY) return;
         if(this.sceneGame !== World.w.game)
         {
            this.sceneGame = World.w.game; this.sceneLocations = []; this.sceneSaved = {};
            this.sceneHistory = new Dictionary(true);
            var encoded:* = this.sceneGame.triggers["continuous_scene.terrain.v1"];
            if(encoded is String && encoded.length)
            {
               var decoded:Object = JSON.parse(encoded);
               if(decoded.version == 1) this.sceneSaved = decoded.locations;
            }
         }
         var base:Array = [];
         var tile:Tile;
         var row:Array;
         var x:int;
         var y:int;
         for(y = 0; y < value.spaceY; ++y)
            for(x = 0; x < value.spaceX; ++x)
            {
               tile = value.space[x][y]; row = [];
               for each(var field:String in this.sceneFields) row.push(tile[field]);
               base.push(row);
            }
         var key:String = value.land.act.id + ":" + revision;
         var saved:Object = this.sceneSaved[key];
         if(saved && saved.width == value.spaceX && saved.height == value.spaceY)
         {
            for each(var change:Array in saved.tiles)
            {
               var index:int = int(change[0]);
               if(index < 0 || index >= base.length || change.length != this.sceneFields.length + 1) continue;
               tile = value.space[index % value.spaceX][int(index / value.spaceX)];
               for(var i:int = 0; i < this.sceneFields.length; ++i) tile[this.sceneFields[i]] = change[i + 1];
            }
            var marks:Array = [];
            for each(var mark:Array in saved.marks)
            {
               if(mark[0] == "decal")
               {
                  mark[1][0] = mark[1][0] ? getDefinitionByName(mark[1][0]) as Class : null;
                  mark[1][1] = mark[1][1] ? getDefinitionByName(mark[1][1]) as Class : null;
               }
               marks.push(mark);
            }
            this.sceneHistory[value] = marks;
         }
         this.sceneLocations.push({loc:value,base:base,key:key});
      }

      public function sceneSave(game:Object) : void
      {
         if(game !== this.sceneGame) return;
         for each(var entry:Object in this.sceneLocations)
         {
            var value:Location = entry.loc;
            var changes:Array = [];
            for(var y:int = 0; y < value.spaceY; ++y)
               for(var x:int = 0; x < value.spaceX; ++x)
               {
                  var index:int = y * value.spaceX + x;
                  var tile:Tile = value.space[x][y];
                  var row:Array = [index];
                  var changed:Boolean = false;
                  for(var i:int = 0; i < this.sceneFields.length; ++i)
                  {
                     var current:* = tile[this.sceneFields[i]];
                     row.push(current);
                     if(current !== entry.base[index][i]) changed = true;
                  }
                  if(changed) changes.push(row);
               }
            var marks:Array = [];
            for each(var mark:Array in this.sceneHistory[value])
            {
               var args:Array = mark[1].concat();
               if(mark[0] == "decal")
               {
                  args[0] = args[0] ? getQualifiedClassName(args[0]) : null;
                  args[1] = args[1] ? getQualifiedClassName(args[1]) : null;
               }
               marks.push([mark[0],args,mark[2]]);
            }
            this.sceneSaved[entry.key] = {width:value.spaceX,height:value.spaceY,tiles:changes,marks:marks};
         }
         game.triggers["continuous_scene.terrain.v1"] = JSON.stringify({version:1,locations:this.sceneSaved});
      }

