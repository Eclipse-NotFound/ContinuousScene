package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Shape;
    import flash.display.Stage;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Read-only native motion, followed by one terminal cache pixel comparison. */
    public class SceneLeafCacheTrial {
        private static const TARGET:String="pfe_fla::sleg20_53";
        private static const STABLE:int=120;
        private var ids:Dictionary=new Dictionary(true),nextId:int=1;
        private var matches:Array=[];
        private var world:*,location:*,player:*,root:DisplayObjectContainer;
        private var targetClass:Class;
        private var prior:Object,currentRun:int=0,maxRun:int=0;
        private var samples:int=0,present:int=0,eligible:int=0,changes:int=0,topologyChanges:int=0;
        private var scanMs:int=0,scanNodes:int=0,created:int=0,disposed:int=0;
        private var held:MovieClip,heldOriginal:Boolean=false;
        private var closed:Boolean=false;
        public var report:Object={version:"player-leaf-cache-1",target:TARGET,diagnosticOnly:true,
            performanceEligible:false,complete:false,passed:false,outcome:"not-started",errors:[],
            policy:{minimumStableRunFrames:120,maximumTopologyChangesPer120Frames:1,
                pixelMaxRGB:2,pixelMaxAlpha:0,restoreExact:true},
            limits:["Observation is not a performance acceptance run; scan work remains in all continuous intervals.",
                "Only the exact native sleg20_53 is considered; no alternative symbol, equipment, AI or input is substituted.",
                "120-frame stability is a conservative experiment threshold, not an engine guarantee or measured cache lifetime.",
                "One terminal current-pose Stage draw comparison does not validate other poses, zoom, ancestor transforms, OS presentation or global animation-queue timing.",
                "Terminal effective visibility and bounds reject obvious hidden/offstage leaves; foreground or mask occlusion and actual unoccluded contribution are not proved.",
                "Window state is observed only. Hidden/inactive windows do not by themselves mean cache failure; actual screen presentation remains unverified.",
                "Shape count does not prove vector complexity. No cacheAsBitmapMatrix, timeline stop/goto, or window/focus change is used."]};

        private function id(value:*):int {if(value==null)return 0;if(!ids[value])ids[value]=nextId++;return ids[value];}
        private static function matrix(d:DisplayObject):Array {
            var m:Matrix=d.transform.matrix;return [m.a,m.b,m.c,m.d,m.tx,m.ty];
        }
        private static function color(d:DisplayObject):Array {
            var c:ColorTransform=d.transform.colorTransform;
            return [c.redMultiplier,c.greenMultiplier,c.blueMultiplier,c.alphaMultiplier,c.redOffset,c.greenOffset,c.blueOffset,c.alphaOffset];
        }
        private static function equalArray(a:Array,b:Array):Boolean {
            if(a.length!=b.length)return false;for(var i:int=0;i<a.length;++i)if(a[i]!==b[i])return false;return true;
        }
        private function walk(node:DisplayObject,inventory:Object=null):void {
            ++scanNodes;
            var name:String=getQualifiedClassName(node),clip:MovieClip=node as MovieClip;
            if(name==TARGET)matches.push(node);
            if(inventory && clip && clip.totalFrames==1 && clip.numChildren==1 && clip.getChildAt(0) is Shape)
                inventory[name]=inventory[name]===undefined?1:int(inventory[name])+1;
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container)for(var i:int=0;i<container.numChildren;++i)walk(container.getChildAt(i),inventory);
        }
        private function state(leaf:MovieClip):Object {
            var child:DisplayObject=leaf.numChildren==1?leaf.getChildAt(0):null;
            return {id:id(leaf),parent:id(leaf.parent),shape:id(child),className:getQualifiedClassName(leaf),
                frame:leaf.currentFrame,totalFrames:leaf.totalFrames,isPlaying:leaf.isPlaying,
                children:leaf.numChildren,shapeClass:child?getQualifiedClassName(child):null,
                matrix:matrix(leaf),parentMatrix:leaf.parent?matrix(leaf.parent):null,color:color(leaf),
                shapeMatrix:child?matrix(child):null,shapeColor:child?color(child):null,
                cache:leaf.cacheAsBitmap,filters:leaf.filters.length,mask:id(leaf.mask),blendMode:leaf.blendMode,
                visible:leaf.visible,alpha:leaf.alpha,shapeVisible:child?child.visible:false,
                shapeAlpha:child?child.alpha:0,shapeCache:child?child.cacheAsBitmap:false,
                shapeFilters:child?child.filters.length:-1,shapeMask:child?id(child.mask):0,
                shapeBlendMode:child?child.blendMode:null,
                eligible:Object(leaf)[new QName("","constructor")]===targetClass && leaf.totalFrames==1 &&
                    leaf.currentFrame==1 && !leaf.isPlaying && leaf.numChildren==1 && child is Shape &&
                    !leaf.cacheAsBitmap && leaf.filters.length==0 && leaf.mask==null && leaf.blendMode=="normal" &&
                    !child.cacheAsBitmap && child.filters.length==0 && child.mask==null && child.blendMode=="normal"};
        }
        private static function sameContent(a:Object,b:Object):Boolean {
            if(!a || !b)return false;
            for each(var key:String in ["id","parent","shape","frame","totalFrames","isPlaying","children","cache",
                "filters","mask","blendMode","visible","alpha","shapeVisible","shapeAlpha","shapeCache","shapeFilters","shapeMask","shapeBlendMode"])
                if(a[key]!==b[key])return false;
            return equalArray(a.matrix,b.matrix) && equalArray(a.color,b.color) &&
                equalArray(a.shapeMatrix,b.shapeMatrix) && equalArray(a.shapeColor,b.shapeColor);
        }
        private static function windowState(stage:Stage):Object {
            var out:Object={errors:[],stage:{},nativeWindow:{}};
            if(!stage){out.errors.push("No actual Stage");return out;}
            for each(var key:String in ["displayState","frameRate","quality","stageWidth","stageHeight"])
                try {out.stage[key]=stage[key];}catch(e:*){out.errors.push("stage."+key+": "+String(e));}
            var window:*;
            try {window=stage.nativeWindow;}catch(error:*){out.errors.push("nativeWindow: "+String(error));}
            if(window){
                try {out.nativeWindow.applicationActiveWindowMatches=NativeApplication.nativeApplication.activeWindow===window;}
                catch(aerror:*){out.errors.push("activeWindow identity: "+String(aerror));}
                for each(key in ["visible","active","closed","displayState","renderMode"])
                    try {out.nativeWindow[key]=window[key];}catch(werror:*){out.errors.push("nativeWindow."+key+": "+String(werror));}
                try {var b:*=window.bounds;out.nativeWindow.bounds={x:b.x,y:b.y,width:b.width,height:b.height};}
                catch(berror:*){out.errors.push("nativeWindow.bounds: "+String(berror));}
            } else out.errors.push("No readable nativeWindow");
            return out;
        }
        public function begin(w:*):Boolean {
            if(world)throw new Error("Leaf diagnostic started twice");
            world=w;location=w.loc;player=w.gg;root=player.vis as DisplayObjectContainer;
            report.initialWindow=windowState(w.main.stage as Stage);
            report.equipment={currentArmor:player.currentArmor?String(player.currentArmor.id):null,
                inventoryArmor:String(w.invent.cArmorId),playerVisualClass:getQualifiedClassName(root)};
            var classes:Object={},before:int=getTimer();matches.length=0;
            if(!root)throw new Error("Player has no native display container");
            walk(root,classes);report.inventory={singleFrameSingleShapeClasses:classes,matches:[],scanMs:getTimer()-before};
            try {targetClass=w.main.loaderInfo.applicationDomain.getDefinition(TARGET.replace("::",".")) as Class;}
            catch(definitionError:*){report.inventory.definitionError=String(definitionError);}
            for each(var node:DisplayObject in matches)report.inventory.matches.push(state(node as MovieClip));
            report.preflightPassed=targetClass!=null && matches.length==1 && report.inventory.matches[0].eligible && report.equipment.currentArmor=="pip";
            report.outcome=report.preflightPassed?"observing":"inconclusive-initial-target";
            return report.preflightPassed;
        }
        public function observe(w:*,windowIndex:int,frame:int):Object {
            var started:int=getTimer(),before:int=scanNodes;
            if(w!==world || w.loc!==location || w.gg!==player || player.vis!==root)throw new Error("Leaf diagnostic world/player/root changed");
            matches.length=0;walk(root);
            var leaf:Object=matches.length==1?state(matches[0] as MovieClip):null;
            ++samples;if(leaf)++present;
            if(leaf && leaf.eligible)++eligible;
            if(prior && (!leaf || leaf.id!=prior.id || leaf.parent!=prior.parent || leaf.shape!=prior.shape))++topologyChanges;
            if(leaf && leaf.eligible && sameContent(prior,leaf))++currentRun;
            else {if(prior)++changes;currentRun=leaf && leaf.eligible?1:0;}
            maxRun=Math.max(maxRun,currentRun);prior=leaf;
            var elapsed:int=getTimer()-started;scanMs+=elapsed;
            return {window:windowIndex,frame:frame,matches:matches.length,leaf:leaf,stableRun:currentRun,
                scanMs:elapsed,scanNodes:scanNodes-before};
        }
        public function snapshot():Object {
            return {samples:samples,present:present,eligible:eligible,contentChanges:changes,topologyChanges:topologyChanges,
                currentStableRun:currentRun,maxStableRun:maxRun,scanMs:scanMs,scanNodes:scanNodes,
                pendingRestore:held?1:0,created:created,disposed:disposed};
        }
        private function capture(stage:Stage):BitmapData {
            var out:BitmapData=new BitmapData(stage.stageWidth,stage.stageHeight,true,0);++created;
            try {out.draw(stage);}catch(error:*){out.dispose();++disposed;throw error;}
            return out;
        }
        private static function compare(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
            var changed:int=0,maxRGB:int=0,maxAlpha:int=0;
            for(var i:int=0;i<av.length;++i){
                var p:uint=av[i],q:uint=bv[i];if(p==q)continue;++changed;
                maxAlpha=Math.max(maxAlpha,Math.abs(int(p>>>24)-int(q>>>24)));
                for(var shift:int=0;shift<24;shift+=8)maxRGB=Math.max(maxRGB,Math.abs(int((p>>>shift)&255)-int((q>>>shift)&255)));
            }
            av=null;bv=null;
            return {exactEqual:changed==0,withinTolerance:maxRGB<=2 && maxAlpha==0,changedPixels:changed,maxRGB:maxRGB,maxAlpha:maxAlpha};
        }
        private function restore():void {
            if(!held)return;
            var clip:MovieClip=held;
            if(clip.cacheAsBitmap!==true)report.errors.push("External leaf cache change while owned");
            clip.cacheAsBitmap=heldOriginal;
            if(clip.cacheAsBitmap!==heldOriginal)throw new Error("Leaf cache restoration failed");
            held=null;
        }
        private function pixels(w:*):Object {
            var start:int=getTimer(),a:BitmapData,b:BitmapData,c:BitmapData;
            var result:Object={attempted:true,passed:false,afterFinalTimingSample:true,errors:[]};
            try {
                matches.length=0;walk(root);
                if(matches.length!=1)throw new Error("Terminal exact leaf is absent or ambiguous");
                var clip:MovieClip=matches[0] as MovieClip,before:Object=state(clip);
                if(!before.eligible || !sameContent(prior,before))throw new Error("Terminal leaf/content changed after observation");
                var stage:Stage=w.main.stage as Stage;
                if(!stage || stage.stageWidth<1 || stage.stageHeight<1 || stage.stageWidth>4096 || stage.stageHeight>2160)
                    throw new Error("Unsupported actual Stage size");
                result.leaf=before;result.worldMatrix=matrix(w.visual);result.playerMatrix=matrix(root);
                var cursor:DisplayObject=clip,effectiveVisible:Boolean=true,reachesStage:Boolean=false,effectiveAlpha:Number=1;
                while(cursor){
                    if(!cursor.visible || !(cursor.alpha>0))effectiveVisible=false;
                    effectiveAlpha*=cursor.alpha;
                    if(cursor===stage){reachesStage=true;break;}cursor=cursor.parent;
                }
                var bounds:Rectangle=clip.getBounds(stage),viewport:Rectangle=new Rectangle(0,0,stage.stageWidth,stage.stageHeight);
                var finiteBounds:Boolean=isFinite(bounds.x) && isFinite(bounds.y) && isFinite(bounds.width) && isFinite(bounds.height);
                result.visibility={onStage:clip.stage===stage,ancestryReachesStage:reachesStage,
                    effectiveVisible:effectiveVisible && effectiveAlpha>0,effectiveAlpha:effectiveAlpha,
                    finiteBounds:finiteBounds,bounds:{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height},
                    intersectsStage:finiteBounds && !bounds.isEmpty() && viewport.intersects(bounds)};
                if(!result.visibility.onStage || !reachesStage || !result.visibility.effectiveVisible || !result.visibility.intersectsStage)
                    throw new Error("Terminal leaf is hidden or outside the actual Stage; cache untouched");
                a=capture(stage);
                if(!sameContent(before,state(clip)))throw new Error("Native capture changed leaf state");
                held=clip;heldOriginal=clip.cacheAsBitmap;clip.cacheAsBitmap=true;
                if(!clip.cacheAsBitmap)throw new Error("Leaf cache setter did not apply");
                b=capture(stage);restore();c=capture(stage);
                if(w!==world || w.loc!==location || w.gg!==player || player.vis!==root)
                    throw new Error("Terminal captures changed world/player/root identity");
                result.cached=compare(a,b);result.restored=compare(a,c);result.finalLeaf=state(clip);
                result.stateRestored=sameContent(before,result.finalLeaf);
                result.passed=result.cached.withinTolerance && result.restored.exactEqual && result.stateRestored;
            } catch(error:*) {result.errors.push(String(error));}
            finally {
                try {restore();}catch(cleanup:*){result.errors.push("restore: "+String(cleanup));}
                if(a){a.dispose();++disposed;}if(b){b.dispose();++disposed;}if(c){c.dispose();++disposed;}
            }
            result.elapsedMs=getTimer()-start;result.passed=result.passed && result.errors.length==0 && !held;
            return result;
        }
        public function finish(w:*,complete:Boolean):Object {
            report.finalWindow=windowState(w && w.main?w.main.stage as Stage:null);
            report.observation=snapshot();report.complete=complete && samples==1200;
            report.frequentReplacement=topologyChanges>Math.floor(samples/STABLE);
            report.stabilityAccepted=report.complete && present==samples && eligible==samples &&
                currentRun>=STABLE && !report.frequentReplacement;
            report.pixels={attempted:false,reason:"Incomplete or unstable exact target; no cache write"};
            try {
                if(report.stabilityAccepted)report.pixels=pixels(w);
                report.passed=report.stabilityAccepted && report.pixels.passed===true && report.errors.length==0;
                report.outcome=report.passed?"component-passed":report.preflightPassed?"not-qualified":"inconclusive-initial-target";
            } finally {report.cleanup=clear();}
            report.passed=report.passed && report.cleanup.restored;
            return report;
        }
        public function clear():Object {
            if(closed)return report.cleanup;
            var failures:Array=[];
            try {restore();}catch(error:*){failures.push(String(error));}
            var clean:Object={restored:!held && created==disposed && report.errors.length==0 && failures.length==0,
                pendingRestore:held?1:0,created:created,disposed:disposed,errors:report.errors.concat(failures)};
            if(!held){world=null;location=null;player=null;root=null;matches.length=0;prior=null;targetClass=null;ids=new Dictionary(true);closed=true;}
            report.cleanup=clean;return clean;
        }
    }
}
