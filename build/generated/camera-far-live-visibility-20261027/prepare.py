"""Narrow native attribution for far animation/filter roots omitted by the old trial."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-maskguard-20261027'
VERSION='camera-far-live-visibility-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-maskguard-1',VERSION)
    s=one(s,'import flash.geom.Matrix;', 'import flash.geom.Matrix;\n    import flash.geom.Point;\n    import flash.filters.BitmapFilter;')
    s=one(s,'private var order:Array=[0,1,1,0];','private var order:Array=[0,1,2,3,3,2,1,0];')
    s=s.replace('measurementFrames:480','measurementFrames:960')
    s=s.replace('Only qualified static direct roots outside the whole route plus 320px are hidden.',
        'Only far animation/filter direct roots omitted by the old static-only trial are hidden; timelines stay live.')
    s=s.replace('before alpha tests','before offscreen visibility checks')
    s=one(s,'sameLayers(layerState(),row.condition)','sameLayers(layerState(),int(row.condition/2))')
    s=one(s,'report.complete=true;report.passed=true;clear(w);',
        'phase=4;cursor=0;applyLayers(0);')
    s=one(s,'} else applyFrame();\n                }\n            } catch(error:Error)',
        '''} else applyFrame();
                } else if(phase==4) {
                    pixelCase(views[cursor],views.length+cursor);++cursor;
                    if(cursor==views.length){report.complete=true;report.passed=true;clear(w);}
                }
            } catch(error:Error)''')
    s=one(s,'try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady)auditRoots();}',
        'try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady)auditRoots();}')
    s=one(s,'disposeOwned();\n            if(saved!=null', '''disposeOwned();
            if(filterProbe!=null) {try {filterProbe.dispose();report.filterProbeDisposed=true;filterProbe=null;}catch(filterError:Error){cleanup.errors.push("filter probe: "+filterError.message);}}
            if(saved!=null''')
    s=one(s,'mode:["native-moving","far-static-hidden-moving"][condition]',
        'mode:["native-static","native-moving","far-live-hidden-static","far-live-hidden-moving"][condition]')
    s=one(s,'hidden:false,moving:true,startAtMs:previous,','hidden:false,moving:condition%2==1,startAtMs:previous,')
    s=one(s,'var point:Object=route[age];','var point:Object=row.moving?route[age]:views[0];')
    s=one(s,'applyCamera(point.x,point.y);applyLayers(row.condition);','applyCamera(point.x,point.y);applyLayers(int(row.condition/2));')
    start=s.index('        private function staticReason(')
    end=s.index('        private function collectRoots(',start)
    s=s[:start]+BOUND_FUNCTIONS+s[end:]
    s=one(s,'var at:int=getTimer();routeBounds.inflate(320,320);',
        'var at:int=getTimer();routeBounds.inflate(320,320);filterProbe=new BitmapData(1,1,true,0);report.filterProbeCreated=true;')
    s=one(s,'perFrameFullScans:0,transitionWrites:0,audits:0};',
        'perFrameFullScans:0,transitionWrites:0,audits:0,withFilters:0,withAnimation:0,boundsChangedAtAudit:0,frameChangesAtAudit:0};')
    s=one(s,'if(reason=="")reason=staticReason(root);\n                        var bounds:Rectangle=root.getBounds(world.visual);',
        '''var features:Object={filters:0,animation:0};
                        if(reason=="")reason=supportedReason(root,features);
                        if(reason=="" && features.filters==0 && features.animation==0)reason="old-static-only";
                        var bounds:Rectangle=reason==""?worldBounds(root):null;''')
    s=one(s,'roots.push({target:root,parent:parent,index:i,alpha:root.alpha,matrix:root.transform.matrix.clone(),visible:root.visible,bounds:bounds});',
        '''roots.push({target:root,parent:parent,index:i,alpha:root.alpha,matrix:root.transform.matrix.clone(),visible:root.visible,bounds:bounds,
                                frame:root is MovieClip?MovieClip(root).currentFrame:-1});
                            if(features.filters>0)++report.rootSelection.withFilters;
                            if(features.animation>0)++report.rootSelection.withAnimation;''')
    s=one(s,'} catch(error:Error){reason="unreadable";}',
        '} catch(error:Error){throw new Error("Root selection layer="+l+" index="+i+": "+error.message);}')
    start=s.index('                require(staticReason(root)=="","Root acquired an effect or animation");')
    end=s.index('\n            }\n            ++report.rootSelection.audits;',start)
    s=s[:start]+'''                var features:Object={filters:0,animation:0};
                require(supportedReason(root,features)=="","Root acquired unsupported rendering");
                var bounds:Rectangle=worldBounds(root);
                require(!bounds.intersects(routeBounds),"Animated/filter root reached protected route: "+getQualifiedClassName(root));
                if(!bounds.equals(item.bounds))++report.rootSelection.boundsChangedAtAudit;
                if(root is MovieClip && MovieClip(root).currentFrame!=item.frame)++report.rootSelection.frameChangesAtAudit;'''+s[end:]
    return s

BOUND_FUNCTIONS='''        private var filterProbe:BitmapData;
        private function supportedReason(node:DisplayObject,features:Object):String {
            if(node==null)return "null-node";
            if(node.mask!=null || maskTargets[node]===true)return "mask";
            if(node.transform.matrix3D!=null || node.transform.matrix==null)return "3d";
            if(node.blendMode!="normal")return "blend";
            for each(var filter:BitmapFilter in node.filters) {
                var kind:String=getQualifiedClassName(filter);
                if(kind!="flash.filters::DropShadowFilter" && kind!="flash.filters::GlowFilter" &&
                   kind!="flash.filters::BlurFilter" && kind!="flash.filters::ColorMatrixFilter")return "unsupported-filter";
                ++features.filters;
            }
            var clip:MovieClip=node as MovieClip;
            if(clip!=null && clip.totalFrames>1)++features.animation;
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i) {
                var reason:String=supportedReason(container.getChildAt(i),features);if(reason!="")return reason;
            }
            return "";
        }
        private function transformedBounds(bounds:Rectangle,m:Matrix):Rectangle {
            var points:Array=[m.transformPoint(new Point(bounds.left,bounds.top)),m.transformPoint(new Point(bounds.right,bounds.top)),
                m.transformPoint(new Point(bounds.left,bounds.bottom)),m.transformPoint(new Point(bounds.right,bounds.bottom))];
            var left:Number=Infinity,top:Number=Infinity,right:Number=-Infinity,bottom:Number=-Infinity;
            for each(var p:Point in points) {left=Math.min(left,p.x);right=Math.max(right,p.x);top=Math.min(top,p.y);bottom=Math.max(bottom,p.y);}
            return new Rectangle(left,top,right-left,bottom-top);
        }
        private function localVisualBounds(node:DisplayObject):Rectangle {
            var bounds:Rectangle=node.getBounds(node);
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container!=null)for(var i:int=0;i<container.numChildren;++i) {
                var child:DisplayObject=container.getChildAt(i);
                require(child!=null,"Incomplete visual bounds traversal");
                var childBounds:Rectangle=transformedBounds(localVisualBounds(child),child.transform.matrix);
                if(!childBounds.isEmpty())bounds=bounds.isEmpty()?childBounds:bounds.union(childBounds);
            }
            for each(var filter:BitmapFilter in node.filters) {
                // Retain unfiltered geometry as a conservative union (including knockout effects).
                var expanded:Rectangle=filterProbe.generateFilterRect(bounds,filter);
                bounds=bounds.union(expanded);
            }
            return bounds;
        }
        private function worldBounds(node:DisplayObject):Rectangle {
            var m:Matrix=node.transform.concatenatedMatrix.clone(),inverse:Matrix=world.visual.transform.concatenatedMatrix.clone();
            inverse.invert();m.concat(inverse);
            var bounds:Rectangle=transformedBounds(localVisualBounds(node),m);
            require(isFinite(bounds.x) && isFinite(bounds.y) && isFinite(bounds.width) && isFinite(bounds.height),"Non-finite rendered bounds");
            return bounds;
        }

'''

def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-far-maskguard-1',VERSION)
    s=s.replace("==55 and cleanup['terrainRestored']","==110 and cleanup['terrainRestored']")
    s=s.replace("==len(trial['nativeWarmups'])==5","==len(trial['nativeWarmups'])==10")
    s=s.replace("roots['selected']*12", "roots['selected']*22")
    s=s.replace("roots['audits']>=15", "roots['audits']>=25 and trial['filterProbeCreated'] and trial['filterProbeDisposed']")
    s=s.replace("len(trial['windows'])==4", "len(trial['windows'])==8").replace("==480", "==960")
    s=s.replace("modes=('native-moving','far-static-hidden-moving')", "modes=('native-static','native-moving','far-live-hidden-static','far-live-hidden-moving')")
    s=s.replace("(0,1,1,0)","(0,1,2,3,3,2,1,0)")
    s=s.replace("row['moving'] is True", "row['moving'] is (condition%2==1)")
    s=s.replace("assert len(xs)>1 and len(ys)>1", "assert (len(xs)>1)==row['moving'] and (len(ys)>1)==row['moving']")
    s=s.replace("[condition,roots['selected']]", "[condition//2,roots['selected']]")
    s=s.replace("if i:assert row['vx']==trial['windows'][0]['vx'] and row['vy']==trial['windows'][0]['vy']", "if row['moving']:assert row['vx']==trial['windows'][1]['vx'] and row['vy']==trial['windows'][1]['vy']")
    s=s.replace("((0,1),(3,2))", "((1,3),(6,4),(0,2),(7,5))")
    s=s.replace('Mask/effect/animation-bearing roots excluded, no wrapper or reparenting.', 'Only animation/filter roots, conservative bounds at switches; no timeline controls, wrappers or reparenting.')
    s=s.replace('ContinuousScene / far static root visibility / 01a13816','ContinuousScene / far live root visibility / 01a13816')
    s=s.replace('480 direct-root visibility controls','960 static/moving live-root visibility controls')
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared offscreen live/filter root diagnostic; formal files untouched')
