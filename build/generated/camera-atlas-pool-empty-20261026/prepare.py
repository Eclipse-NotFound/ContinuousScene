"""Source-only: do not display or copy proven transparent native layer centres."""
from pathlib import Path
import importlib.util
import hashlib

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-idle-v2-20261026'
VERSION='camera-atlas-pool-empty-1'

def replace_once(value,before,after):
    assert value.count(before)==1,(before,value.count(before))
    result=value.replace(before,after,1)
    assert result.replace(after,before,1)==value
    return result

def save(name,text):
    target=HERE/name;assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(text,name,'exec')
    target.write_text(text,'utf-8',newline='\n')

edits=[
('        private var stationarySkips:int=0;',
 '        private var stationarySkips:int=0;\n        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0;'),
('for each(page in pages)if(required[page.key])for each(var bitmap:Bitmap in page.layers)bitmap.visible=true;',
 'for each(page in pages)if(required[page.key])for(var displayLayer:int=0;displayLayer<4;++displayLayer)page.layers[displayLayer].visible=page.content[displayLayer];'),
('page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);',
 'page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);page.content=[false,false,false,false];'),
('        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {\n            for(var cell:int=0;cell<16;++cell){',
 '        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {\n            page.content=[false,false,false,false];\n            for(var cell:int=0;cell<16;++cell){'),
('record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false]};',
 'record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false],hasPixels:[false,false,false,false]};'),
('''                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                            page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;''',
'''                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                            var wasNonempty:Boolean=record.hasPixels[i];
                            // Bounds intersection is conservative: false proves the
                            // entire centre transparent; true may still include holes.
                            record.hasPixels[i]=source.getColorBoundsRect(0xFF000000,0,false).intersects(sourceRect);
                            ++alphaRectChecks;
                            if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}
                            else {
                                if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                                ++emptyCopiesAvoided;
                            }'''),
('''                        toHide.push(bitmap);
                    } else if(record.shown[i])''',
'''                        if(record.hasPixels[i])page.content[i]=true;
                        toHide.push(bitmap);
                    } else if(record.shown[i])'''),
('rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown});',
 'rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown,layerHasPixels:page.content.concat(),layerVisible:[page.layers[0].visible,page.layers[1].visible,page.layers[2].visible,page.layers[3].visible]});'),
('return {version:"atlas-pool-1",stationarySkips:stationarySkips,',
 'return {version:"atlas-pool-1",stationarySkips:stationarySkips,alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,')]
source=(OLD/'SceneRasterPresentation.as').read_text('utf-8-sig')
assert hashlib.sha256((OLD/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()=='6651CCFF07F244B09C67B3D5D6E61DE80791696C4BFF25607B4FE0F92B1D2D3A'
for before,after in edits:source=replace_once(source,before,after)
save('SceneRasterPresentation.as',source)
digest=hashlib.sha256((HERE/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()
patch=(OLD/'probe_patch.py').read_text('utf-8-sig').replace('camera-atlas-pool-idle-2',VERSION)
patch=replace_once(patch,"PRESENTER_SHA='6651CCFF07F244B09C67B3D5D6E61DE80791696C4BFF25607B4FE0F92B1D2D3A'","PRESENTER_SHA='"+digest+"'")
patch=replace_once(patch,'stage_cost_helper=helper_source','PRESENTER_EDITS += '+repr(edits)+'\n\nstage_cost_helper=helper_source')
save('probe_patch.py',patch)
save('tests/StationaryRefresh.as.inc',(OLD/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig'))

run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-atlas-pool-idle-2',VERSION)
extra='''
# A truly transparent page need not have a displayed Bitmap. Retain all pool
# identity/memory checks, replacing only the obsolete all-requested-pages rule.
page_source=inspect.getsource(framework.page_state)
before="assert set(state['visiblePageKeys'])==set(state['currentPageKeys'])"
after="assert set(state['visiblePageKeys'])=={p['key'] for p in state['pages'] if p['key'] in state['currentPageKeys'] and any(p['layerHasPixels'])}"
assert page_source.count(before)==1
page_source=page_source.replace(before,after,1)
page_scope=dict(framework.__dict__);exec(compile(page_source,'<transparent-page-invariant>','exec'),page_scope)
framework.page_state=page_scope['page_state']

idle_summary=summarize
def summarize(raw):
    value=idle_summary(raw);trial=raw['cameraRaster']
    states=[s for row in trial['windows'] for s in row['atlasStates']]
    moving=[s for row in trial['windows'] if row['mode']=='atlas-moving' for s in row['atlasStates'] if s['presented']]
    visible=[];empty=[]
    for state in states+[x['presentation'] for x in trial['pixels']]:
        for page in state['pages']:
            content,shown=page['layerHasPixels'],page['layerVisible']
            assert len(content)==len(shown)==4 and all(type(b) is bool for b in content+shown)
            eligible=state['presented'] and page['key'] in state['currentPageKeys']
            assert shown==[bool(eligible and b) for b in content]
            assert page['visible']==any(shown)
    for state in moving:
        pages=[p for p in state['pages'] if p['key'] in state['currentPageKeys']]
        visible.append(sum(sum(p['layerVisible']) for p in pages))
        empty.append(sum(sum(not b for b in p['layerHasPixels']) for p in pages))
    assert moving and max(empty)>0 and states[-1]['emptyCopiesAvoided']>0
    value['transparentLayers']=dict(displayedPerMovingFrame=base.metrics(visible),
        omittedPerMovingFrame=base.metrics(empty),alphaRectChecks=states[-1]['alphaRectChecks'],
        emptyCopiesAvoided=states[-1]['emptyCopiesAvoided'],
        limitation='A nonempty bounding rectangle may conservatively include an empty centre; only proven empty centres are omitted.')
    return value

'''
run=replace_once(run,'original_main=inspect.getsource(framework.framework.framework.main)',extra+'original_main=inspect.getsource(framework.framework.framework.main)')
save('run.py',run)
save('README.md',f'''# 固定池空透明层候选

呈现器SHA256 {digest}。基于已通过刷新检查的6651CCFF，仅原生位图版本/身份/显示状态需要更新时检查alpha包围盒。
包围盒不与320px中央块相交，才可证明该中央块全透明；仅此时避免复制并隐藏对应全透明合图层。
包围盒相交可能是假阳性，仍保守按有内容复制/显示。逐格记录由统一revision、源身份及显隐触发，清零及回收逻辑不变。
不改任何非空像素、不合并图层、不修改原生数据或画质。仍保留固定200MiB池、闲置回原生、几何/SATS门控。

沿v2的960帧/31截图/原生击墙和毁墙/回访/完整释放检查；额外核对逐页四层内容与实际visible逐一对应，并记录有多少空层被省略。
扫描耗时完整包含在镜头帧准备和帧间隔内；不把减少显示数量直接当性能收益。只验证候选，未部署。
''')
spec=importlib.util.spec_from_file_location('empty_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save('tests/SceneCameraRasterTrial.as',module.helper_source())
print('Prepared source only; presenter '+digest)
