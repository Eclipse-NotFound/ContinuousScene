package tests {
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    // Terminal private-game experiment. Only chain-owned Box/Bonus graphics;
    // actors, their weapons, projectiles and unknown owners stay native.
    public final class SceneFarParkingTrial {
        public var report:Object={version:"camera-live-parking-return-1",diagnosticOnly:true,
            selected:0,scanned:0,classes:{},skips:{},parked:0,restored:0,retired:0,
            retireReasons:{},frameChanges:0,updates:0,workMs:0,maximumHeld:0,
            originalWindowVisible:false,pixels:null,lifecycle:null,cleanup:null};
        private var world:*;
        private var location:*;
        private var entries:Array=[];
        private var layers:Array=[];
        private var holders:Array=[];
        private var siblings:Array=[];
        private var masks:Dictionary=new Dictionary(true);
        private var seen:Dictionary=new Dictionary(true);
        private var filterProbe:BitmapData;
        private var enabled:Boolean=false;
        private var ready:Boolean=false;
        private var held:int=0;

        private function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
        private function count(map:Object,key:String):void {map[key]=int(map[key])+1;}
        private function maskWalk(node:DisplayObject):void {
            if(node==null)return;
            if(node.mask)masks[node.mask]=true;
            var c:DisplayObjectContainer=node as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)maskWalk(c.getChildAt(i));
        }
        private function safeTree(node:DisplayObject):Boolean {
            if(!node || node.mask || masks[node] || node.scrollRect || node.blendMode!="normal" || node.transform.matrix3D)return false;
            for each(var f:* in node.filters) {
                var kind:String=getQualifiedClassName(f);
                if(kind!="flash.filters::DropShadowFilter" && kind!="flash.filters::GlowFilter" &&
                    kind!="flash.filters::BlurFilter" && kind!="flash.filters::ColorMatrixFilter")return false;
            }
            var c:DisplayObjectContainer=node as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)if(!safeTree(c.getChildAt(i)))return false;
            return true;
        }
        private function project(r:Rectangle,m:Matrix):Rectangle {
            var x1:Number=r.left*m.a,y1:Number=r.left*m.b,x2:Number=r.right*m.a,y2:Number=r.right*m.b;
            var x3:Number=r.top*m.c,y3:Number=r.top*m.d,x4:Number=r.bottom*m.c,y4:Number=r.bottom*m.d;
            return new Rectangle(Math.min(x1,x2)+Math.min(x3,x4)+m.tx,Math.min(y1,y2)+Math.min(y3,y4)+m.ty,
                Math.abs(x2-x1)+Math.abs(x4-x3),Math.abs(y2-y1)+Math.abs(y4-y3));
        }
        private function localBounds(node:DisplayObject):Rectangle {
            var b:Rectangle=node.getBounds(node),c:DisplayObjectContainer=node as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i) {
                var child:DisplayObject=c.getChildAt(i),cb:Rectangle=project(localBounds(child),child.transform.matrix);
                if(!cb.isEmpty())b=b.isEmpty()?cb:b.union(cb);
            }
            for each(var f:* in node.filters)b=b.union(filterProbe.generateFilterRect(b,f));
            return b;
        }
        public function prepare(w:*):void {
            if(ready){require(w===world && w.loc===location,"Parking world changed");return;}
            var begin:int=getTimer();world=w;location=w.loc;
            require(w.grafon.sceneLarge && w.allStat==1 && !w.onPause,"Parking needs live large scene");
            report.originalWindowVisible=w.main.stage.nativeWindow.visible;
            w.main.stage.nativeWindow.visible=true;
            for(var n:int=0;n<w.main.numChildren;++n)require(getQualifiedClassName(w.main.getChildAt(n))!="visMainMenu","Native menu still attached");
            filterProbe=new BitmapData(1,1,true,0);maskWalk(w.main.stage);
            var ownerMap:Dictionary=new Dictionary(true),obj:*=location.firstObj,chainCount:int=0;
            while(obj!=null) {
                require(++chainCount<50000,"Object chain cycle");
                var type:String=getQualifiedClassName(obj);
                if(type=="fe.loc::Box" || type=="fe.loc::Bonus") {
                    for each(var field:String in ["vis","shad"])if(field in obj && obj[field] is DisplayObject) {
                        var graphic:DisplayObject=obj[field] as DisplayObject;
                        if(ownerMap[graphic])ownerMap[graphic]={duplicate:true};
                        else ownerMap[graphic]={owner:obj,field:field,type:type};
                    }
                }
                obj=obj.nobj;
            }
            report.chainCount=chainCount;
            for(var l:int=0;l<w.grafon.visObjs.length;++l) {
                var parent:DisplayObjectContainer=w.grafon.visObjs[l],all:Array=[],holder:Sprite=new Sprite();
                layers.push(parent);holders.push(holder);siblings.push(all);
                for(n=0;n<parent.numChildren;++n)all.push(parent.getChildAt(n));
                for(n=0;n<all.length;++n) {
                    graphic=all[n];++report.scanned;
                    var owned:Object=ownerMap[graphic];
                    if(!owned || owned.duplicate){count(report.skips,"unknown-owner");continue;}
                    if(!owned.owner.in_chain || owned.owner.loc!==location){count(report.skips,"not-chain-owned");continue;}
                    if(!graphic.visible || !safeTree(graphic)){count(report.skips,"rendering-contract");continue;}
                    var bounds:Rectangle=localBounds(graphic);
                    if(bounds.isEmpty() || !isFinite(bounds.width+bounds.height+bounds.x+bounds.y)){count(report.skips,"bounds");continue;}
                    entries.push({root:graphic,owner:owned.owner,field:owned.field,type:owned.type,layer:l,index:n,
                        bounds:bounds,held:false,retired:false,frame:graphic is MovieClip?MovieClip(graphic).currentFrame:0});
                    ++report.selected;count(report.classes,owned.type);seen[graphic]=true;
                }
            }
            require(report.selected>0,"No chain-owned Box/Bonus graphics qualified");
            ready=true;report.prepareMs=getTimer()-begin;report.initialLayers=layerCounts();
        }
        private function layerCounts():Array {
            var a:Array=[];for each(var p:DisplayObjectContainer in layers)a.push(p.numChildren);return a;
        }
        private function retire(item:Object,reason:String):void {
            if(item.retired)return;
            var root:DisplayObject=item.root,holder:Sprite=holders[item.layer];
            // A game-removed/replaced root is never resurrected. Dispose only
            // our own reference/container ownership, not a new native parent.
            if(root.parent===holder)holder.removeChild(root);
            if(item.held){--held;item.held=false;}
            item.retired=true;++report.retired;count(report.retireReasons,reason);
        }
        private function valid(item:Object):Boolean {
            var root:DisplayObject=item.root,parent:DisplayObjectContainer=layers[item.layer],holder:Sprite=holders[item.layer];
            if(item.retired)return false;
            if(item.owner.loc!==location || !item.owner.in_chain || item.owner[item.field]!==root){retire(item,"owner-removed-or-replaced");return false;}
            if(root.parent!==(item.held?holder:parent)){retire(item,"native-parent-changed");return false;}
            return true;
        }
        private function restore(item:Object):void {
            if(!item.held || !valid(item))return;
            var root:DisplayObject=item.root,parent:DisplayObjectContainer=layers[item.layer],all:Array=siblings[item.layer];
            var at:int=parent.numChildren;
            for(var i:int=item.index+1;i<all.length;++i)if(all[i].parent===parent){at=parent.getChildIndex(all[i]);break;}
            parent.addChildAt(root,at);item.held=false;--held;++report.restored;
        }
        private function restoreAll():void {
            // Reverse order makes the closest following anchor available.
            for(var i:int=entries.length-1;i>=0;--i)if(valid(entries[i]))restore(entries[i]);
            enabled=false;require(held==0,"Parking cleanup left owned roots");
        }
        public function update(w:*,on:Boolean):Object {
            prepare(w);var begin:int=getTimer();
            require(w.loc===location && w.allStat==1 && !w.onPause && w.t_exit==0,"Parking lost active world");
            require(w.main.stage.nativeWindow.visible,"Private native window became hidden");
            var previous:Boolean=enabled;
            if(!on) {if(enabled)restoreAll();}
            else {
                enabled=true;
                var inverse:Matrix=w.visual.transform.concatenatedMatrix.clone();inverse.invert();
                var view:Rectangle=project(new Rectangle(0,0,w.main.stage.stageWidth,w.main.stage.stageHeight),inverse);
                view.inflate(1024,1024);
                for(var l:int=0;l<layers.length;++l) {
                    require(layers[l]===w.grafon.visObjs[l],"Object layer replaced");
                    holders[l].transform.matrix=layers[l].transform.concatenatedMatrix;
                }
                for each(var item:Object in entries) {
                    if(!valid(item))continue;
                    var root:DisplayObject=item.root,frame:int=root is MovieClip?MovieClip(root).currentFrame:0;
                    // A native state transition falls back immediately. There
                    // is no frame-script/animation freezing or replay here.
                    if(frame!=item.frame) {restore(item);retire(item,"frame-transition");++report.frameChanges;continue;}
                    if(item.owner===w.gg.teleObj || ("lurkBox" in w.gg && item.owner===w.gg.lurkBox)) {restore(item);continue;}
                    var transform:Matrix=root.transform.matrix.clone();transform.concat(layers[item.layer].transform.concatenatedMatrix);transform.concat(inverse);
                    var b:Rectangle=project(item.bounds,transform);
                    if(view.intersects(b) || !root.visible || root.mask || root.scrollRect || root.blendMode!="normal")restore(item);
                    else if(!item.held) {holders[item.layer].addChild(root);item.held=true;++held;++report.parked;}
                }
            }
            ++report.updates;report.maximumHeld=Math.max(report.maximumHeld,held);
            var elapsed:int=getTimer()-begin;report.workMs+=elapsed;
            return {enabled:on,previousEnabled:previous,held:held,retired:report.retired,workMs:elapsed,
                vx:w.cam.vx,vy:w.cam.vy,windowVisible:w.main.stage.nativeWindow.visible};
        }
        private function compare(a:BitmapData,b:BitmapData):Object {
            var different:int=0,mr:int=0,ma:int=0;
            for(var y:int=0;y<a.height;++y)for(var x:int=0;x<a.width;++x) {
                var av:uint=a.getPixel32(x,y),bv:uint=b.getPixel32(x,y);if(av==bv)continue;++different;
                ma=Math.max(ma,Math.abs((av>>>24)-(bv>>>24)));
                mr=Math.max(mr,Math.abs(((av>>>16)&255)-((bv>>>16)&255)),Math.abs(((av>>>8)&255)-((bv>>>8)&255)),Math.abs((av&255)-(bv&255)));
            }
            return {differentPixels:different,maxRGB:mr,maxAlpha:ma,passed:mr<=2 && ma==0};
        }
        public function verify(w:*):Object {
            require(ready,"Parking never prepared");restoreAll();
            var stage:*=w.main.stage,a:BitmapData,b:BitmapData,c:BitmapData;
            var verification:Object={afterTiming:true,pixels:null,nativeRemoval:null,restored:false};
            try {
                a=new BitmapData(stage.stageWidth,stage.stageHeight,true,0);b=a.clone();c=a.clone();
                a.draw(stage);update(w,true);require(held>0,"No offscreen roots held for pixel check");
                b.draw(stage);restoreAll();c.draw(stage);
                verification.pixels={changed:compare(a,b),restored:compare(a,c),softwareStageDraw:true};
                report.pixels=verification.pixels;
                update(w,true);
                var victim:Object=null;
                for each(var item:Object in entries)if(item.held && item.field=="vis" && item.type=="fe.loc::Box"){victim=item;break;}
                require(victim!=null,"No parked Box for native lifecycle check");
                var before:int=held;
                location.remObj(victim.owner);
                var nativeRemoved:Boolean=!victim.owner.in_chain && victim.root.parent==null;
                update(w,true);restoreAll();
                verification.nativeRemoval={wasHeld:before>0,nativeRemoved:nativeRemoved,retired:victim.retired,
                    notResurrected:victim.root.parent==null && !victim.owner.in_chain};
                report.lifecycle=verification.nativeRemoval;
                require(nativeRemoved && victim.retired && verification.nativeRemoval.notResurrected,"Native Box removal was resurrected");
                verification.restored=held==0;
            } finally {if(a)a.dispose();if(b)b.dispose();if(c)c.dispose();report.pixelBuffersDisposed=3;}
            return verification;
        }
        public function clear():Object {
            var errors:Array=[];
            try{if(ready)restoreAll();}catch(error:Error){errors.push(error.message);}
            if(world)try {world.main.stage.nativeWindow.visible=report.originalWindowVisible;}catch(windowError:Error){errors.push(windowError.message);}
            if(filterProbe){filterProbe.dispose();filterProbe=null;}
            var pending:int=0;for each(var holder:Sprite in holders)pending+=holder.numChildren;
            report.cleanup={restored:errors.length==0 && held==0 && pending==0,pendingOwnedRoots:pending,errors:errors};
            return report.cleanup;
        }
    }
}
