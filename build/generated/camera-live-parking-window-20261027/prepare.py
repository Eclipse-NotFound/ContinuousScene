from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-live-parking-return-20261027'
VERSION='camera-live-parking-window-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
WINDOW_EDIT='''
('main=host;started=getTimer();var f:FileStream=new FileStream();',
 ''' + repr('''main=host;started=getTimer();var f:FileStream=new FileStream();
            report.nativeWindowInitiallyVisible=main.stage.nativeWindow.visible;
            report.nativeWindowEvents=[];
            main.stage.addEventListener(Event.DEACTIVATE,function(e:Event):void {
                report.nativeWindowEvents.push({type:e.type,atMs:getTimer(),phase:phase,index:index,allStat:w?w.allStat:null});
            });
            main.stage.addEventListener(Event.ACTIVATE,function(e:Event):void {
                report.nativeWindowEvents.push({type:e.type,atMs:getTimer(),phase:phase,index:index,allStat:w?w.allStat:null});
            });
            main.stage.nativeWindow.visible=true;''') + '''),
('            if(error==null && report.samples.length==20 && w && w.grafon.sceneLarge)',
 ''' + repr('''            main.stage.nativeWindow.visible=report.nativeWindowInitiallyVisible;
            report.nativeWindowRestored=main.stage.nativeWindow.visible===report.nativeWindowInitiallyVisible;
            if(error==null && report.samples.length==20 && w && w.grafon.sceneLarge)''') + '''),
'''
def generated():
    out={}
    for name in ['tests/SceneFarParkingTrial.as','probe_patch.py','summary.py','README.md','run.py']:
        s=(BASE/name).read_text('utf-8-sig').replace('camera-live-parking-return-1',VERSION)
        if name.endswith('.as'):
            s=one(s,'            w.main.stage.nativeWindow.visible=true;', '            require(w.main.stage.nativeWindow.visible,"Window must be shown before native gameplay starts");')
        if name=='probe_patch.py':
            # Extra edits are applied after the original transform, preserving
            # its reverse-exact check and unchanged seed closure.
            s=one(s,'def transform(s):', 'EDITS=EDITS+('+WINDOW_EDIT+')\ndef transform(s):')
            s=one(s,"EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',", "EXTRA_INPUTS=(HERE/'prepare.py',HERE/'summary.py',HERE.parent/'camera-live-parking-return-20261027/tests/SceneFarParkingTrial.as',HERE.parent/'camera-live-parking-return-20261027/probe_patch.py',HERE.parent/'camera-live-parking-return-20261027/summary.py',HERE.parent/'camera-live-parking-return-20261027/README.md',HERE.parent/'camera-live-parking-return-20261027/run.py',")
        if name=='summary.py':s=one(s,"assert raw['ok'] and raw['error'] is None", "assert raw['ok'] and raw['error'] is None and raw['nativeWindowRestored']")
        if name=='README.md':s+='\n前驱r1监控出现347秒/1445秒采样空档后超时；r2在任何暂存写入前触发原生失焦暂停。本变体只把私有窗口显示移至驱动初始化时，记录ACTIVATE/DEACTIVATE；不禁用原生暂停，不强改allStat，不在计时中关闭暂停面板。\n'
        out[name]=s
    return out
if __name__=='__main__':
    for name,s in generated().items():
        p=HERE/name;p.parent.mkdir(exist_ok=True)
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared early private-window visibility and native focus observations')
