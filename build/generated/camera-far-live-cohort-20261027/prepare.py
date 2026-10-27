from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-far-live-warm-20261027'
VERSION='camera-far-live-cohort-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-far-live-warm-1',VERSION)
    s=one(s,'boundsChangedAtAudit:0,frameChangesAtAudit:0};','boundsChangedAtAudit:0,frameChangesAtAudit:0,excludedDuringQualification:[],initialSelected:0};')
    s=one(s,'frame:root is MovieClip?MovieClip(root).currentFrame:-1});', 'layer:l,hasFilters:features.filters>0,hasAnimation:features.animation>0,frame:root is MovieClip?MovieClip(root).currentFrame:-1});')
    s=one(s,'rootsReady=true;report.rootSelection.selected=roots.length;', 'rootsReady=true;report.rootSelection.selected=roots.length;report.rootSelection.initialSelected=roots.length;')
    start=s.index('        private function auditRoots():void {');end=s.index('        private function restoreRoots():void {',start)
    s=s[:start]+AUDIT+s[end:]
    s=one(s,'report.stabilizationFrames=settle;report.timingStart=snapshot();',
        'auditRoots();require(roots.length>0,"No stable far roots after fixed qualification");report.rootSelection.timingSelected=roots.length;report.rootSelection.writesBeforeTiming=report.rootSelection.transitionWrites;report.stabilizationFrames=settle;report.timingStart=snapshot();')
    return s
AUDIT='''        private function auditRoots():void {
            if(!rootsReady)return;
            for(var i:int=roots.length-1;i>=0;--i) {
                var item:Object=roots[i],root:DisplayObject=item.target;
                var label:String=getQualifiedClassName(root)+" layer="+item.layer+" index="+item.index;
                require(root.parent===item.parent && item.parent.getChildIndex(root)==item.index,"Root ownership/order changed: "+label);
                require(root.visible===(currentCondition==0?item.visible:false),"Root visibility changed externally: "+label);
                var reason:String="",bounds:Rectangle=null,features:Object={filters:0,animation:0};
                if(root.alpha!==item.alpha || !sameMatrix(root.transform.matrix,item.matrix))reason="local-pose";
                if(reason=="")reason=supportedReason(root,features);
                if(reason=="") {
                    try {bounds=worldBounds(root);}
                    catch(e:Error) {reason="bounds-read: "+e.message;}
                }
                if(reason=="" && bounds.intersects(routeBounds))reason="protected-route";
                if(reason!="") {
                    require(phase<3,"Qualified root changed during/after timing: "+label+" reason="+reason);
                    if(item.controlled===true) {root.visible=item.visible;item.controlled=false;}
                    require(root.visible===item.visible,"Qualification visibility restoration failed: "+label);
                    report.rootSelection.excludedDuringQualification.push({className:getQualifiedClassName(root),layer:item.layer,index:item.index,reason:reason,phase:phase});
                    --report.rootSelection.byLayer[item.layer];
                    --report.rootSelection.classes[getQualifiedClassName(root)];
                    if(item.hasFilters)--report.rootSelection.withFilters;
                    if(item.hasAnimation)--report.rootSelection.withAnimation;
                    roots.splice(i,1);report.rootSelection.selected=roots.length;
                    continue;
                }
                if(!bounds.equals(item.bounds))++report.rootSelection.boundsChangedAtAudit;
                if(root is MovieClip && MovieClip(root).currentFrame!=item.frame)++report.rootSelection.frameChangesAtAudit;
            }
            ++report.rootSelection.audits;
        }

'''
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-far-live-warm-1',VERSION)
    s=s.replace("roots['selected']+sum(roots['skips'].values())", "roots['selected']+len(roots['excludedDuringQualification'])+sum(roots['skips'].values())")
    s=s.replace("roots['transitionWrites']==roots['selected']*22", "roots['timingSelected']==roots['selected'] and roots['transitionWrites']-roots['writesBeforeTiming']==roots['selected']*12")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared fixed pre-timing qualification and explicit instability reasons')
