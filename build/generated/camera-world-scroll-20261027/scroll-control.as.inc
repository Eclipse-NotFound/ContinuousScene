        private var scrollCondition:int=0;
        private function applyLayers(condition:int):void {
            require(condition>=0 && condition<=2,"Invalid world scroll condition");
            require(terrain.length==1,"World target missing");
            var item:Object=terrain[0];
            require(item.target===world.visual && item.target.parent===item.parent,"World parent changed");
            require(world.visual.alpha===item.alpha && world.visual.visible===item.visible,"World style changed");
            if(condition==0) {
                if(world.visual.cacheAsBitmap!==saved.worldCache)world.visual.cacheAsBitmap=saved.worldCache;
                if(world.visual.scrollRect!=null)world.visual.scrollRect=null;
                if(world.visual.x!==Number(cam.vx))world.visual.x=cam.vx;
                if(world.visual.y!==Number(cam.vy))world.visual.y=cam.vy;
            } else {
                world.visual.scrollRect=new Rectangle(-cam.vx,-cam.vy,stage.stageWidth,stage.stageHeight);
                if(world.visual.x!=0)world.visual.x=0;
                if(world.visual.y!=0)world.visual.y=0;
                if(world.visual.cacheAsBitmap!==(condition==2))world.visual.cacheAsBitmap=condition==2;
            }
            scrollCondition=condition;
            require(sameLayers(layerState(),condition),"World scrolling did not apply");
        }
        private function layerState():Array {
            var r:Rectangle=world.visual.scrollRect;
            return [scrollCondition,world.visual.cacheAsBitmap,world.visual.x,world.visual.y,r!=null,
                r!=null?r.x:0,r!=null?r.y:0,r!=null?r.width:0,r!=null?r.height:0];
        }
        private function sameLayers(value:Array,condition:int):Boolean {
            var expected:Array=condition==0?[0,saved.worldCache,Number(cam.vx),Number(cam.vy),false,0,0,0,0]:
                [condition,condition==2,0,0,true,-Number(cam.vx),-Number(cam.vy),stage.stageWidth,stage.stageHeight];
            if(value.length!=expected.length)return false;
            for(var i:int=0;i<value.length;++i)if(value[i]!==expected[i])return false;
            return true;
        }

