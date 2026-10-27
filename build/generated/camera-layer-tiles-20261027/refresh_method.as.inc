        private function refreshChangedLayers():void {
            var at:int=getTimer(),dirty:Array=[];
            require(DisplayObjectContainer(root).numChildren==worldChildren.length,"World layer lifecycle changed");
            for(var i:int=0;i<worldChildren.length;++i)require(DisplayObjectContainer(root).getChildAt(i)===worldChildren[i],"World layer identity changed");
            for each(var group:Object in groups) {
                var changed:Boolean=false,owners:Dictionary=new Dictionary();
                for each(var watch:Object in group.watch) {
                    ++watchReads;
                    if(watch.node.currentFrame!=watch.frame || watch.node.totalFrames!=watch.total) {
                        changed=true;++animationChanges;++group.changes;owners[watch.owner]=true;
                    }
                }
                if(changed)dirty.push({group:group,owners:owners});
            }
            watchMs+=getTimer()-at;
            for each(var item:Object in dirty) {
                if(item.group.actor)redrawActorTiles(item.group,item.owners);else drawGroup(item.group);
                collectWatch(item.group);
            }
        }
