        private var routeBounds:Rectangle;
        private var roots:Array=[];
        private var maskTargets:Dictionary=new Dictionary(true);
        private var currentCondition:int=0;
        private var rootsReady:Boolean=false;

        private function collectViewport():void {
            var view:Rectangle=new Rectangle(-cam.vx,-cam.vy,stage.stageWidth,stage.stageHeight);
            routeBounds=routeBounds==null?view:routeBounds.union(view);
        }

        private function collectMasks(node:DisplayObject):void {
            if(node.mask!=null)maskTargets[node.mask]=true;
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i)collectMasks(container.getChildAt(i));
        }

        private function staticReason(node:DisplayObject):String {
            if(node.mask!=null || maskTargets[node]===true)return "mask";
            if(node.filters.length>0)return "filters";
            if(node.transform.matrix3D!=null || node.transform.matrix==null)return "3d";
            if(node.blendMode!="normal")return "blend";
            var clip:MovieClip=node as MovieClip;
            if(clip!=null && clip.totalFrames>1 && clip.isPlaying)return "playing";
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i) {
                var reason:String=staticReason(container.getChildAt(i));if(reason!="")return reason;
            }
            return "";
        }

        private function collectRoots():void {
            require(!rootsReady && routeBounds!=null,"Root collection state");
            var at:int=getTimer();routeBounds.inflate(320,320);
            report.rootSelection={scanned:0,selected:0,byLayer:[0,0,0,0,0,0],classes:{},skips:{},
                area:{x:routeBounds.x,y:routeBounds.y,width:routeBounds.width,height:routeBounds.height},
                perFrameFullScans:0,transitionWrites:0,audits:0};
            collectMasks(stage);
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target as DisplayObjectContainer;
                require(parent!=null && parent===grafon.visObjs[l],"Object layer missing");
                for(var i:int=0;i<parent.numChildren;++i) {
                    var root:DisplayObject=parent.getChildAt(i),reason:String="";
                    ++report.rootSelection.scanned;
                    try {
                        if(!root.visible)reason="already-hidden";
                        if(reason=="")reason=staticReason(root);
                        var bounds:Rectangle=root.getBounds(world.visual);
                        if(reason=="" && (!isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width) || !isFinite(bounds.height) || bounds.isEmpty()))reason="bounds";
                        if(reason=="" && bounds.intersects(routeBounds))reason="route-visible";
                        if(reason=="") {
                            roots.push({target:root,parent:parent,index:i,alpha:root.alpha,matrix:root.transform.matrix.clone(),visible:root.visible,bounds:bounds});
                            ++report.rootSelection.byLayer[l];
                            var name:String=getQualifiedClassName(root);
                            report.rootSelection.classes[name]=int(report.rootSelection.classes[name])+1;
                        }
                    } catch(error:Error){reason="unreadable";}
                    if(reason!="")report.rootSelection.skips[reason]=int(report.rootSelection.skips[reason])+1;
                }
            }
            rootsReady=true;report.rootSelection.selected=roots.length;
            report.rootSelection.prepareMs=getTimer()-at;
            require(roots.length>0,"No qualified offscreen roots");auditRoots();
        }

        private function auditRoots():void {
            if(!rootsReady)return;
            for each(var item:Object in roots) {
                var root:DisplayObject=item.target;
                require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Root ownership/order changed");
                require(root.visible===(currentCondition==0?item.visible:false),"Root visibility changed externally");
                require(root.alpha===item.alpha && sameMatrix(root.transform.matrix,item.matrix),"Root local pose changed");
                require(staticReason(root)=="","Root acquired an effect or animation");
                var bounds:Rectangle=root.getBounds(world.visual);
                require(bounds.equals(item.bounds) && !bounds.intersects(routeBounds),"Root bounds changed");
            }
            ++report.rootSelection.audits;
        }

        private function restoreRoots():void {
            var errors:Array=[];
            for each(var item:Object in roots) {
                var root:DisplayObject=item.target;
                try {
                    if(item.controlled===true && root.visible===false)root.visible=item.visible;
                    require(root.visible===item.visible,"Could not restore controlled visibility");
                    item.controlled=false;
                } catch(error:Error){errors.push(error.message);}
            }
            currentCondition=0;
            require(errors.length==0,"Root restore: "+errors.join(";"));
        }

        private function applyLayers(condition:int):void {
            require(condition==0 || condition==1,"Invalid root condition");
            for(var i:int=0;i<terrain.length;++i)require(terrain[i].target===grafon.visObjs[i] && terrain[i].target.parent===terrain[i].parent,"Layer identity changed");
            if(condition==currentCondition)return;
            require(rootsReady,"Root selection missing");auditRoots();
            for each(var item:Object in roots) {
                item.target.visible=condition==0?item.visible:false;
                item.controlled=condition==1;
                ++report.rootSelection.transitionWrites;
            }
            currentCondition=condition;
        }

        private function layerState():Array {return [currentCondition,roots.length];}
        private function sameLayers(value:Array,condition:int):Boolean {
            return value.length==2 && value[0]==condition && value[1]==roots.length;
        }

