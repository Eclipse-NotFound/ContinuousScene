        private function applyLayers(condition:int):void {
            require(condition>=0 && condition<=3,"Invalid object condition");
            require(terrain.length==6,"Object layers missing");
            for(var i:int=0;i<6;++i) {
                var item:Object=terrain[i];
                require(item.target===grafon.visObjs[i] && item.target.parent===item.parent,"Object layer parent changed");
                item.target.alpha=(condition&1)?0:item.alpha;
                item.target.visible=(condition&2)?false:item.visible;
            }
            require(sameLayers(layerState(),condition),"Object condition did not apply");
        }
        private function layerState():Array {
            var out:Array=[];
            for each(var item:Object in terrain){out.push(item.target.alpha);out.push(item.target.visible?1:0);}
            return out;
        }
        private function sameLayers(value:Array,condition:int):Boolean {
            if(value.length!=12)return false;
            for(var i:int=0;i<6;++i) {
                if(value[2*i]!==Number((condition&1)?0:terrain[i].alpha))return false;
                if(value[2*i+1]!==Number((condition&2)?0:(terrain[i].visible?1:0)))return false;
            }
            return true;
        }

