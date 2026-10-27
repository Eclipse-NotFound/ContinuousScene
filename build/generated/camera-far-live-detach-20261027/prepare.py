from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-live-counts-20261027'
VERSION='camera-far-live-detach-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-live-counts-1',VERSION)
    s=s.replace('far-live-hidden-static','far-live-detached-static').replace('far-live-hidden-moving','far-live-detached-moving')
    s=s.replace('Only far animation/filter direct roots omitted by the old static-only trial are hidden; timelines stay live.',
        'Far animation/filter roots are detached in a terminal paused diagnostic; no explicit timeline control, but native event/timeline scheduling may change.')
    s=one(s,'private var rootsReady:Boolean=false;', 'private var rootsReady:Boolean=false;\n        private var virtualParents:Dictionary=new Dictionary(true);\n        private var layerChildren:Array=[];')
    s=one(s,'var m:Matrix=node.transform.concatenatedMatrix.clone(),inverse:Matrix=world.visual.transform.concatenatedMatrix.clone();',
        '''var m:Matrix=node.transform.concatenatedMatrix.clone(),inverse:Matrix=world.visual.transform.concatenatedMatrix.clone();
            if(node.parent==null && virtualParents[node]!=null) {m=node.transform.matrix.clone();m.concat(virtualParents[node].transform.concatenatedMatrix);}''')
    s=one(s,'excludedDuringQualification:[],initialSelected:0};','excludedDuringQualification:[],initialSelected:0,removed:0,reattached:0};')
    s=one(s,'require(parent!=null && parent===grafon.visObjs[l],"Object layer missing");',
        '''require(parent!=null && parent===grafon.visObjs[l],"Object layer missing");
                var siblings:Array=[];for(var si:int=0;si<parent.numChildren;++si)siblings.push(parent.getChildAt(si));layerChildren.push(siblings);''')
    s=one(s,'++report.rootSelection.byLayer[l];', 'virtualParents[root]=parent;++report.rootSelection.byLayer[l];')
    s=one(s,'require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Root ownership/order changed: "+label);',
        '''if(currentCondition==0)require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Root ownership/order changed: "+label);
                else require(root.parent==null && item.controlled===true,"Detached root changed ownership: "+label);''')
    s=one(s,'require(root.visible===(currentCondition==0?item.visible:false),"Root visibility changed externally: "+label);',
        'require(root.visible===item.visible,"Detached root visibility changed externally: "+label);')
    s=one(s,'if(item.controlled===true) {root.visible=item.visible;item.controlled=false;}',
        'require(currentCondition==0 && item.controlled!==true,"Qualification exclusion requires native ownership");')
    start=s.index('        private function restoreRoots():void {');end=s.index('        private function layerState():Array',start)
    s=s[:start]+OWNERSHIP+s[end:]
    s=one(s,'try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady)auditRoots();}',
        'try {restoreRoots();cleanup.terrainRestored=sameLayers(layerState(),0);if(rootsReady){auditRoots();verifySiblings();}cleanup.siblingsRestored=true;}')
    return s
OWNERSHIP='''        private function verifySiblings():void {
            for(var l:int=0;l<layerChildren.length;++l) {
                var parent:DisplayObjectContainer=terrain[l].target as DisplayObjectContainer,siblings:Array=layerChildren[l];
                require(parent.numChildren==siblings.length,"Layer child count changed");
                for(var i:int=0;i<siblings.length;++i)require(parent.getChildAt(i)===siblings[i],"Layer sibling order changed at "+l+"/"+i);
            }
        }
        private function restoreRoots():void {
            var errors:Array=[];
            // Selection is in ascending layer/index order, so insertion restores original slots.
            for each(var item:Object in roots)try {
                var root:DisplayObject=item.target;
                if(item.controlled===true) {
                    require(root.parent==null,"Do not steal a reparented detached root");
                    require(item.index<=item.parent.numChildren,"Original restore slot unavailable");
                    item.parent.addChildAt(root,item.index);item.controlled=false;
                    ++report.rootSelection.reattached;++report.rootSelection.transitionWrites;
                }
                require(root.parent===item.parent && root.visible===item.visible,"Detached root restoration mismatch");
            }catch(error:Error){errors.push(error.message);}
            currentCondition=0;require(errors.length==0,"Detached restore: "+errors.join(";"));
            if(rootsReady)verifySiblings();
        }
        private function applyLayers(condition:int):void {
            require(condition==0 || condition==1,"Invalid detach condition");
            for(var i:int=0;i<terrain.length;++i)require(terrain[i].target===grafon.visObjs[i] && terrain[i].target.parent===terrain[i].parent,"Detach layer identity changed");
            if(condition==currentCondition)return;
            require(rootsReady,"Detach selection missing");auditRoots();
            if(condition==0){restoreRoots();return;}
            verifySiblings();
            for(i=roots.length-1;i>=0;--i) {
                var item:Object=roots[i],root:DisplayObject=item.target;
                require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Detach ownership changed before removal");
                item.parent.removeChild(root);item.controlled=true;
                require(root.parent==null,"Detach did not remove child");
                ++report.rootSelection.removed;++report.rootSelection.transitionWrites;
            }
            currentCondition=1;
        }

'''
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-far-live-counts-1',VERSION)
    s=s.replace('far-live-hidden-static','far-live-detached-static').replace('far-live-hidden-moving','far-live-detached-moving')
    s=s.replace("roots['audits']>=25", "roots['audits']>=25 and roots['removed']==roots['reattached'] and cleanup['siblingsRestored']")
    s=s.replace('Only animation/filter roots, conservative bounds at switches; no timeline controls, wrappers or reparenting.',
        'Temporary offscreen detach can affect native scheduling/events; not a pure transform or gameplay claim.')
    s=s.replace('ContinuousScene / far live root visibility / 01a13816','ContinuousScene / far live root detach / 01a13816')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared temporary offscreen detach with exact sibling restoration')
