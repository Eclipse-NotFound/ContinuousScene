package tests {
    import flash.display.Bitmap;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.geom.Rectangle;
    import flash.text.TextField;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Read-only terminal census. Invoke outside frame timing samples.
     * Public unit.vis / childObjs associations are resolved to direct layer roots,
     * including an intervening test wrapper. Internal visBmp / arm are never read.
     * Presence in the display tree does not prove that AIR rasterizes an offscreen
     * object. Bounds do not include filter expansion or prove pixel visibility.
     */
    public class SceneUnitLayerCensus {
        private static const ROOT_DETAILS:int=600;
        private static const TREE_NODES:int=10000;
        private static const TREE_DEPTH:int=80;

        public static function read(w:*):Object {
            var started:int=getTimer();
            var out:Object={version:"unit-layer-census-1",readOnly:true,complete:false,
                layerIndex:2,roots:[],categories:{},classes:{},errors:[],
                rootsCount:0,rootDetailsOmitted:0,owners:0,missingBodyVisuals:0,
                associationsOutsideLayer:0,duplicateAssociations:0,ambiguousRoots:0,
                limitations:[
                    "Geometry uses getBounds(w.visual) against the actual camera view, without a safety margin.",
                    "Bounds exclude filter expansion; masks, alpha and clipping may further change drawn pixels.",
                    "Shape and TextField counts identify vector/text nodes. Sprite graphics are not inspected; vectorLeafCandidates may be empty containers.",
                    "Bitmap pixel totals count references, not unique GPU/CPU allocations or rendered pixels.",
                    "Unknown roots and ambiguous ownership remain explicit; no internal visBmp or arm access.",
                    "isPlaying is recorded only as a flag; it does not prove animation is advancing."
                ]};
            try {
                if(!w || !w.loc || !w.grafon || !w.visual || !w.cam)
                    throw new Error("Missing current world/location/display/camera");
                var layer:DisplayObjectContainer=w.grafon.visObjs[2] as DisplayObjectContainer;
                var reference:DisplayObject=w.visual as DisplayObject;
                if(!layer || !reference)throw new Error("Missing unit layer or world display");
                var scale:Number=Number(w.cam.scaleV);
                if(!isFinite(scale) || scale<=0)throw new Error("Invalid camera scale");
                var view:Rectangle=new Rectangle(-Number(w.cam.vx)/scale,-Number(w.cam.vy)/scale,
                    Number(w.cam.screenX)/scale,Number(w.cam.screenY)/scale);
                if(!finiteRect(view) || view.width<=0 || view.height<=0)throw new Error("Invalid camera view");
                out.view=rect(view);out.camera={scale:scale,vx:w.cam.vx,vy:w.cam.vy,
                    screenX:w.cam.screenX,screenY:w.cam.screenY};
                out.layer=displayState(layer);out.layerClass=className(layer);
                out.layerParentClass=className(layer.parent);
                var claims:Dictionary=new Dictionary(true),seenOwners:Dictionary=new Dictionary(true);
                var units:Array=[];
                if(w.loc.units)for each(var candidate:* in w.loc.units)if(candidate && !seenOwners[candidate]) {
                    seenOwners[candidate]=true;units.push(candidate);
                }
                if(w.gg && !seenOwners[w.gg]){seenOwners[w.gg]=true;units.push(w.gg);}
                for each(var unit:* in units)associateOwner(unit,w.gg,layer,claims,out);
                var count:int=layer.numChildren;
                out.rootsCount=count;
                for(var index:int=0;index<count;++index) {
                    var root:DisplayObject=layer.getChildAt(index);
                    var associations:Array=claims[root] as Array;
                    var category:String="unknown",ownerClass:String=null;
                    if(associations && associations.length==1) {
                        category=associations[0].category;ownerClass=associations[0].ownerClass;
                    } else if(associations && associations.length>1) {
                        category="ambiguous";++out.ambiguousRoots;
                    }
                    var row:Object={index:index,category:category,rootClass:className(root),
                        ownerClass:ownerClass,associations:associations?associations:[],
                        name:root.name,state:displayState(root),bounds:null,geometry:"unknown"};
                    try {
                        var bounds:Rectangle=root.getBounds(reference);
                        row.bounds=rect(bounds);
                        if(finiteRect(bounds))row.geometry=bounds.isEmpty()?"empty":bounds.intersects(view)?"onscreen":"offscreen";
                    } catch(boundsError:Error) {row.boundsError=boundsError.message;}
                    var tree:Object=newTree();
                    walk(root,tree,0);
                    row.tree=tree;
                    if(tree.truncated)out.errors.push("Display tree census truncated at root "+index);
                    if(tree.errors.length)out.errors.push("Display tree census errors at root "+index);
                    var group:Object=out.categories[category];
                    if(!group)out.categories[category]=group={roots:0,onscreen:0,offscreen:0,empty:0,unknown:0,
                        ownVisible:0,effectiveVisible:0,bitmapNodes:0,bitmapPixels:0,
                        shapeNodes:0,textNodes:0,vectorLeafCandidates:0,filteredNodes:0,cachedNodes:0,maskedNodes:0};
                    ++group.roots;++group[row.geometry];
                    if(row.state.visible)++group.ownVisible;
                    if(row.state.effectiveVisible)++group.effectiveVisible;
                    for each(var field:String in ["bitmapNodes","bitmapPixels","shapeNodes","textNodes",
                        "vectorLeafCandidates","filteredNodes","cachedNodes","maskedNodes"])group[field]+=tree[field];
                    out.classes[row.rootClass]=int(out.classes[row.rootClass])+1;
                    if(out.roots.length<ROOT_DETAILS)out.roots.push(row);else ++out.rootDetailsOmitted;
                }
                out.layerIdentityStable=w.grafon.visObjs[2]===layer && layer.numChildren==count;
                out.complete=out.layerIdentityStable && out.errors.length==0;
            } catch(error:Error) {out.errors.push(error.message);}
            out.elapsedMs=getTimer()-started;
            return out;
        }

        private static function associateOwner(unit:*,player:*,layer:DisplayObjectContainer,
                                               claims:Dictionary,out:Object):void {
            ++out.owners;
            try {
                var owner:Object={ownerIndex:out.owners-1,ownerClass:className(unit),ownerId:unit.id==null?null:String(unit.id),
                    ownerX:Number(unit.X),ownerY:Number(unit.Y),player:unit===player || Boolean(unit.player)};
                var visual:DisplayObject=unit.vis as DisplayObject;
                if(visual)associate(visual,owner,owner.player?"player-body":"unit-body","vis",layer,claims,out);
                else ++out.missingBodyVisuals;
                var children:*=unit.childObjs;
                if(children)for(var key:String in children) {
                    var child:*=children[key];
                    if(!child)continue;
                    try {
                        visual=child.vis as DisplayObject;
                        if(visual)associate(visual,owner,"unit-attachment","childObjs["+key+"]",
                            layer,claims,out,className(child));
                    } catch(childError:Error) {out.errors.push(owner.ownerClass+" child "+key+": "+childError.message);}
                }
            } catch(error:Error) {out.errors.push("Owner association: "+error.message);}
        }

        private static function associate(visual:DisplayObject,owner:Object,category:String,source:String,
                                          layer:DisplayObjectContainer,claims:Dictionary,out:Object,
                                          attachmentClass:String=null):void {
            var root:DisplayObject=visual,depth:int=0;
            while(root && root.parent!==layer) {root=root.parent;++depth;}
            if(!root) {++out.associationsOutsideLayer;return;}
            var list:Array=claims[root] as Array;
            if(!list)claims[root]=list=[];
            for each(var existing:Object in list)
                if(existing.category==category && existing.ownerIndex==owner.ownerIndex && existing.source==source) {
                    ++out.duplicateAssociations;return;
                }
            list.push({category:category,source:source,ownerIndex:owner.ownerIndex,ownerClass:owner.ownerClass,ownerId:owner.ownerId,
                ownerX:owner.ownerX,ownerY:owner.ownerY,player:owner.player,
                visualClass:className(visual),attachmentClass:attachmentClass,wrapperDepth:depth});
        }

        private static function newTree():Object {
            return {nodes:0,bitmapNodes:0,bitmapPixels:0,bitmapDimensions:{},maxBitmapWidth:0,maxBitmapHeight:0,
                shapeNodes:0,textNodes:0,vectorLeafCandidates:0,vectorLeafDimensions:{},
                containers:0,sprites:0,movieClips:0,playingFlags:0,multiFrameClips:0,
                filteredNodes:0,filterClasses:{},cachedNodes:0,maskedNodes:0,
                ownHiddenNodes:0,zeroAlphaNodes:0,otherNodes:0,truncated:false,errors:[]};
        }

        private static function walk(node:DisplayObject,out:Object,depth:int):void {
            if(!node)return;
            if(out.nodes>=TREE_NODES || depth>TREE_DEPTH) {out.truncated=true;return;}
            ++out.nodes;
            try {
                if(!node.visible)++out.ownHiddenNodes;
                if(node.alpha<=0)++out.zeroAlphaNodes;
                if(node.cacheAsBitmap)++out.cachedNodes;
                if(node.mask)++out.maskedNodes;
                var filters:Array=node.filters;
                if(filters.length)++out.filteredNodes;
                for each(var filter:* in filters) {
                    var filterClass:String=className(filter);
                    out.filterClasses[filterClass]=int(out.filterClasses[filterClass])+1;
                }
                var bitmap:Bitmap=node as Bitmap;
                var container:DisplayObjectContainer=node as DisplayObjectContainer;
                if(bitmap) {
                    ++out.bitmapNodes;
                    if(bitmap.bitmapData) {
                        var width:int=bitmap.bitmapData.width,height:int=bitmap.bitmapData.height;
                        var dimensions:String=width+"x"+height;
                        out.bitmapDimensions[dimensions]=int(out.bitmapDimensions[dimensions])+1;
                        out.bitmapPixels+=Number(width)*height;
                        out.maxBitmapWidth=Math.max(out.maxBitmapWidth,width);
                        out.maxBitmapHeight=Math.max(out.maxBitmapHeight,height);
                    }
                } else if(node is Shape)++out.shapeNodes;
                else if(node is TextField)++out.textNodes;
                else if(!container)++out.otherNodes;
                if(!bitmap && (!container || container.numChildren==0)) {
                    ++out.vectorLeafCandidates;
                    dimensions=Math.ceil(node.width)+"x"+Math.ceil(node.height);
                    out.vectorLeafDimensions[dimensions]=int(out.vectorLeafDimensions[dimensions])+1;
                }
                if(node is Sprite)++out.sprites;
                var clip:MovieClip=node as MovieClip;
                if(clip) {
                    ++out.movieClips;
                    if(clip.isPlaying)++out.playingFlags;
                    if(clip.totalFrames>1)++out.multiFrameClips;
                }
                if(container) {
                    ++out.containers;
                    for(var i:int=0;i<container.numChildren;++i)walk(container.getChildAt(i),out,depth+1);
                }
            } catch(error:Error) {out.errors.push(className(node)+": "+error.message);}
        }

        private static function displayState(node:DisplayObject):Object {
            var filters:Array=[],effective:Boolean=true,alpha:Number=1;
            for each(var filter:* in node.filters)filters.push(className(filter));
            var parent:DisplayObject=node;
            while(parent) {effective=effective && parent.visible;alpha*=parent.alpha;parent=parent.parent;}
            return {visible:node.visible,alpha:node.alpha,effectiveVisible:effective,effectiveAlpha:alpha,
                cacheAsBitmap:node.cacheAsBitmap,filters:filters,maskClass:className(node.mask),
                scrollRect:node.scrollRect?rect(node.scrollRect):null,
                x:node.x,y:node.y,width:node.width,height:node.height,
                scaleX:node.scaleX,scaleY:node.scaleY,rotation:node.rotation,blendMode:node.blendMode};
        }
        private static function className(value:*):String {return value==null?null:getQualifiedClassName(value);}
        private static function rect(value:Rectangle):Object {
            return {x:value.x,y:value.y,width:value.width,height:value.height};
        }
        private static function finiteRect(value:Rectangle):Boolean {
            return isFinite(value.x) && isFinite(value.y) && isFinite(value.width) && isFinite(value.height);
        }
    }
}
