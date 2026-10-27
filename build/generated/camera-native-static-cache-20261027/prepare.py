from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-live-warm-20261027'
VERSION='camera-native-static-cache-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-live-warm-1',VERSION)
    s=one(s,'import flash.display.Bitmap;', 'import flash.display.Bitmap;\n    import flash.display.Shape;')
    s=s.replace('Only far animation/filter direct roots omitted by the old static-only trial are hidden; timelines stay live.',
        'Only near-route, wholly single-frame unfiltered vector roots request native bitmap caching; no visibility or animation write.')
    s=one(s,'report.pixelsValid=true;', 'report.pixelsValid=report.visualAccepted===true;')
    s=one(s,'report.complete=true;report.passed=true;clear(w);', 'report.pixelsValid=report.visualAccepted===true;report.complete=true;report.passed=true;clear(w);')
    s=one(s,'if(filterProbe!=null) {try {filterProbe.dispose();report.filterProbeDisposed=true;filterProbe=null;}catch(filterError:Error){cleanup.errors.push("filter probe: "+filterError.message);}}', '')
    s=s.replace('far-live-hidden-static','native-cache-static').replace('far-live-hidden-moving','native-cache-moving')
    start=s.index('        private var filterProbe:BitmapData;');end=s.index('        private function savePixel(',start)
    s=s[:start]+CONTROL+s[end:]
    s=one(s,'require(item.changed.equal && item.restored.equal,"Offscreen root culling changed pixels");',
        '''item.visualAccepted=item.changed.maxRGB<=2 && item.changed.maxAlpha==0;
                    if(report.visualAccepted==null)report.visualAccepted=true;
                    if(!item.visualAccepted)report.visualAccepted=false;
                    require(item.restored.equal,"Native cache restoration changed pixels");''')
    s=one(s,'if(index==0 || !item.restored.equal)', 'if(index==0 || !item.restored.equal || item.changed.maxRGB>2 || item.changed.maxAlpha>0)')
    return s

CONTROL='''        private function staticReason(node:DisplayObject,features:Object):String {
            if(node==null)return "null-node";
            if(node.mask!=null || maskTargets[node]===true)return "mask";
            if(node.filters.length>0)return "filters";
            if(node.transform.matrix3D!=null || node.transform.matrix==null)return "3d";
            if(node.blendMode!="normal")return "blend";
            var clip:MovieClip=node as MovieClip;
            if(clip!=null && clip.totalFrames>1)return "multiframe";
            if(node is Shape)++features.shapes;
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i) {
                var child:DisplayObject=container.getChildAt(i);
                if(child!=null && child.cacheAsBitmap)return "cached-child";
                var reason:String=staticReason(child,features);if(reason!="")return reason;
            }
            return "";
        }
        private function collectRoots():void {
            require(!rootsReady && routeBounds!=null,"Cache root collection state");
            var at:int=getTimer();routeBounds.inflate(320,320);
            report.rootSelection={scanned:0,selected:0,byLayer:[0,0,0,0,0,0],classes:{},skips:{},
                area:{x:routeBounds.x,y:routeBounds.y,width:routeBounds.width,height:routeBounds.height},
                estimatedBytes:0,perFrameFullScans:0,transitionWrites:0,audits:0};
            collectMasks(stage);
            for(var l:int=0;l<terrain.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target as DisplayObjectContainer;
                require(parent===grafon.visObjs[l],"Cache object layer missing");
                for(var i:int=0;i<parent.numChildren;++i) {
                    var root:DisplayObject=parent.getChildAt(i),reason:String="",features:Object={shapes:0};
                    ++report.rootSelection.scanned;
                    if(root==null)reason="null-root";
                    else if(!root.visible)reason="already-hidden";
                    else if(root.cacheAsBitmap)reason="already-cached";
                    if(reason=="")reason=staticReason(root,features);
                    if(reason=="" && features.shapes==0)reason="no-vector-shape";
                    var bounds:Rectangle=reason==""?root.getBounds(world.visual):null;
                    if(reason=="" && (!isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width) || !isFinite(bounds.height) || bounds.isEmpty()))reason="bounds";
                    if(reason=="" && !bounds.intersects(routeBounds))reason="off-route";
                    var bytes:Number=reason==""?(Math.ceil(bounds.width)+4)*(Math.ceil(bounds.height)+4)*4:0;
                    if(reason=="" && (bounds.width>2048 || bounds.height>2048 || report.rootSelection.estimatedBytes+bytes>32*1024*1024))reason="cache-budget";
                    if(reason=="") {
                        roots.push({target:root,parent:parent,index:i,alpha:root.alpha,matrix:root.transform.matrix.clone(),visible:root.visible,
                            bounds:bounds,cache:root.cacheAsBitmap,shapes:features.shapes});
                        ++report.rootSelection.byLayer[l];report.rootSelection.estimatedBytes+=bytes;
                        var name:String=getQualifiedClassName(root);report.rootSelection.classes[name]=int(report.rootSelection.classes[name])+1;
                    } else report.rootSelection.skips[reason]=int(report.rootSelection.skips[reason])+1;
                }
            }
            rootsReady=true;report.rootSelection.selected=roots.length;report.rootSelection.prepareMs=getTimer()-at;
            require(roots.length>0,"No eligible near-route static vector roots");auditRoots();
        }
        private function auditRoots():void {
            if(!rootsReady)return;
            for each(var item:Object in roots) {
                var root:DisplayObject=item.target,features:Object={shapes:0};
                require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Cache root ownership/order changed");
                require(root.visible===item.visible && root.alpha===item.alpha && sameMatrix(root.transform.matrix,item.matrix),"Cache root local state changed");
                require(root.cacheAsBitmap===(currentCondition==1?true:item.cache),"Cache flag changed externally");
                require(staticReason(root,features)=="" && features.shapes==item.shapes,"Static vector root changed structure");
                require(root.getBounds(world.visual).equals(item.bounds),"Static vector root bounds changed");
            }
            ++report.rootSelection.audits;
        }
        private function restoreRoots():void {
            var errors:Array=[];
            for each(var item:Object in roots)try {
                if(item.controlled===true)item.target.cacheAsBitmap=item.cache;
                item.controlled=false;
                require(item.target.cacheAsBitmap===item.cache,"Native cache flag did not restore");
            } catch(error:Error){errors.push(error.message);}
            currentCondition=0;require(errors.length==0,"Cache restore: "+errors.join(";"));
        }
        private function applyLayers(condition:int):void {
            require(condition==0 || condition==1,"Invalid cache condition");
            for(var i:int=0;i<terrain.length;++i)require(terrain[i].target===grafon.visObjs[i] && terrain[i].target.parent===terrain[i].parent,"Cache layer identity changed");
            if(condition==currentCondition)return;
            require(rootsReady,"Cache root selection missing");auditRoots();
            for each(var item:Object in roots) {
                item.target.cacheAsBitmap=condition==1?true:item.cache;item.controlled=condition==1;
                require(item.target.cacheAsBitmap===(condition==1?true:item.cache),"Native cache setter ignored");
                ++report.rootSelection.transitionWrites;
            }
            currentCondition=condition;
        }
        private function layerState():Array {return [currentCondition,roots.length];}
        private function sameLayers(value:Array,condition:int):Boolean {return value.length==2 && value[0]==condition && value[1]==roots.length;}

'''
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-far-live-warm-1',VERSION)
    s=s.replace('far-live-hidden-static','native-cache-static').replace('far-live-hidden-moving','native-cache-moving')
    s=s.replace("assert trial['pixelsValid'] and len(trial['pixels'])==len(trial['nativeWarmups'])==10", "assert trial['pixelsValid']==trial['visualAccepted'] and len(trial['pixels'])==len(trial['nativeWarmups'])==10")
    s=s.replace("for key in ('changed','restored'):", "for key in ('restored',):")
    s=s.replace("and trial['filterProbeCreated'] and trial['filterProbeDisposed']", "and 0<roots['estimatedBytes']<=32*1024**2")
    s=s.replace("originalFrameRate=trial['originalFrameRate'],", "visualAccepted=trial['visualAccepted'],originalFrameRate=trial['originalFrameRate'],")
    s=s.replace('Only animation/filter roots, conservative bounds at switches; no timeline controls, wrappers or reparenting.', 'Only near-route static vector roots request native cache; rejected candidate pixels remain rejected.')
    s=s.replace('ContinuousScene / far live root visibility / 01a13816','ContinuousScene / native static vector cache / 01a13816')
    s=s.replace('960 static/moving live-root visibility controls', '960 static/moving native static cache controls')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared native cache on eligible near-route static vector roots')
