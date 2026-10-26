        private function applyLayers(condition:int):void {
            require(condition>=0 && condition<=3,"Invalid world condition");
            require(terrain.length==1,"World target missing");
            var item:Object=terrain[0];
            require(item.target===world.visual && item.target.parent===item.parent,"World parent changed");
            item.target.alpha=(condition&1)?0:item.alpha;
            item.target.visible=(condition&2)?false:item.visible;
            require(sameLayers(layerState(),condition),"World condition did not apply");
        }
        private function layerState():Array {
            return [world.visual.alpha,world.visual.visible?1:0];
        }
        private function sameLayers(value:Array,condition:int):Boolean {
            return value.length==2 && value[0]===Number((condition&1)?0:terrain[0].alpha) &&
                value[1]===Number((condition&2)?0:(terrain[0].visible?1:0));
        }
