"""Prepare an isolated page-level background composite, preserving native fallback."""
from pathlib import Path
import importlib.util
import hashlib

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-empty-20261026'
VERSION='camera-atlas-pool-merged-1'

def once(value,before,after):
    assert value.count(before)==1,(before,value.count(before))
    result=value.replace(before,after,1)
    assert result.replace(after,before,1)==value
    return result

def save(name,text):
    target=HERE/name;assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(text,name,'exec')
    target.write_text(text,'utf-8',newline='\n')

compat='''        private function backgroundCompatible(parents:Array,surfaces:Array):Boolean {
            var lower:DisplayObjectContainer=parents[1],upper:DisplayObjectContainer=parents[2];
            if(lower.parent==null || lower.parent!==upper.parent ||
                lower.parent.getChildIndex(upper)!=lower.parent.getChildIndex(lower)+1)return false;
            var allowed:Dictionary=new Dictionary();
            for each(var s:Object in surfaces){allowed[s.bitmaps[1]]=true;allowed[s.bitmaps[2]]=true;}
            for each(var p:Object in pages){allowed[p.layers[1]]=true;allowed[p.layers[2]]=true;}
            for each(var parent:DisplayObjectContainer in [lower,upper]) {
                if(!parent.visible || parent.alpha!=1 || parent.x!=0 || parent.y!=0 || parent.scaleX!=1 || parent.scaleY!=1 ||
                    parent.rotation!=0 || parent.blendMode!="normal" || parent.mask!=null || parent.filters.length!=0 ||
                    parent.scrollRect!=null || parent.transform.matrix3D!=null)return false;
                var color:*=parent.transform.colorTransform;
                if(color.redMultiplier!=1 || color.greenMultiplier!=1 || color.blueMultiplier!=1 || color.alphaMultiplier!=1 ||
                    color.redOffset!=0 || color.greenOffset!=0 || color.blueOffset!=0 || color.alphaOffset!=0)return false;
                for(var index:int=0;index<parent.numChildren;++index) {
                    var child:*=parent.getChildAt(index);
                    if(child.visible && !allowed[child])return false;
                }
            }
            return true;
        }

'''
edits=[
('    import flash.geom.Rectangle;', '    import flash.geom.Rectangle;\n    import flash.utils.Dictionary;'),
('        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0;',
 '        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0,backgroundMerges:int=0;'),
('            if(!surfaces.length){fallback("no-native-surfaces");return;}','            if(!surfaces.length){fallback("no-native-surfaces");return;}\n            if(!backgroundCompatible(parents,surfaces)){fallback("background-order-or-effects");return;}'),
('        private function fallback(reason:String):void {',compat+'        private function fallback(reason:String):void {'),
('''                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                        page.cells[cell]=null;''',
'''                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                        if(record.shown[1] && !record.shown[2]){page.data[2].fillRect(page.rects[cell],0);++cellClears;}
                        page.cells[cell]=null;'''),
('''                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;
                var sourceRect:Rectangle=null;''',
'''                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;
                var backgroundChanged:Boolean=changed || record.sources[1]!==surface.nativeBuffers[1] ||
                    record.sources[2]!==surface.nativeBuffers[2] || record.shown[1]!==surface.bitmaps[1].visible ||
                    record.shown[2]!==surface.bitmaps[2].visible;
                var sourceRect:Rectangle=null;'''),
('''                            if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}
                            else {
                                if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                                ++emptyCopiesAvoided;
                            }''',
'''                            if(i==0 || i==3) {
                                if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}
                                else {
                                    if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}
                                    ++emptyCopiesAvoided;
                                }
                            } else if(!record.hasPixels[i])++emptyCopiesAvoided;'''),
('                    } else if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}',
 '                    } else if(record.shown[i] && (i==0 || i==3)){page.data[i].fillRect(page.rects[cell],0);++cellClears;}'),
('''                record.entry=surface;record.revision=surface.revision;
            }
        }

        public function beginFrame()''',
'''                var lowerVisible:Boolean=record.shown[1] && record.hasPixels[1];
                var upperVisible:Boolean=record.shown[2] && record.hasPixels[2];
                page.content[1]=false;
                if(lowerVisible || upperVisible)page.content[2]=true;
                if(backgroundChanged) {
                    if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);
                    if(lowerVisible){page.data[2].copyPixels(surface.nativeBuffers[1],sourceRect,page.points[cell]);++copies;}
                    else {page.data[2].fillRect(page.rects[cell],0);++cellClears;}
                    if(upperVisible){page.data[2].copyPixels(surface.nativeBuffers[2],sourceRect,page.points[cell],null,null,lowerVisible);++copies;}
                    ++backgroundMerges;
                }
                record.entry=surface;record.revision=surface.revision;
            }
        }

        public function beginFrame()'''),
('alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,',
 'alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,backgroundMerges:backgroundMerges,')]
source=(OLD/'SceneRasterPresentation.as').read_text('utf-8-sig')
assert hashlib.sha256((OLD/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()=='65F48207AEACB18879EE41FD61CBB28F0BB9BEA468D9DC3FAA941F51548480CE'
for before,after in edits:source=once(source,before,after)
save('SceneRasterPresentation.as',source)
digest=hashlib.sha256((HERE/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()
patch=(OLD/'probe_patch.py').read_text('utf-8-sig').replace('camera-atlas-pool-empty-1',VERSION)
patch=once(patch,"PRESENTER_SHA='65F48207AEACB18879EE41FD61CBB28F0BB9BEA468D9DC3FAA941F51548480CE'","PRESENTER_SHA='"+digest+"'")
patch=once(patch,'stage_cost_helper=helper_source','PRESENTER_EDITS += '+repr(edits)+'\n\nstage_cost_helper=helper_source')
extra_patch='''
empty_helper=helper_source
def helper_source():
    source=empty_helper()
    edits=[('report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);',
        'mergeFallbackCheck();report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);'),
        ('        private function capture():BitmapData {',
        (HERE/'tests/MergeFallback.as.inc').read_text('utf-8-sig')+'\\n        private function capture():BitmapData {')]
    value=source
    for before,after in edits:
        assert value.count(before)==1;value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==source
    return value

'''
patch=once(patch,'def prepare(source:Path,destination:Path):',extra_patch+'def prepare(source:Path,destination:Path):')
save('probe_patch.py',patch)
save('tests/StationaryRefresh.as.inc',(OLD/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig'))

run=(OLD/'run.py').read_text('utf-8-sig').replace('camera-atlas-pool-empty-1',VERSION)
run=once(run,"HERE/'tests/StationaryRefresh.as.inc',patch.HELPER,","HERE/'tests/StationaryRefresh.as.inc',HERE/'tests/MergeFallback.as.inc',patch.HELPER,")
run=once(run,"verify_source.replace(\"trial['pixelBitmapsDisposed'] == 19\",\"trial['pixelBitmapsDisposed'] == 31\",1)",
    "verify_source.replace(\"trial['pixelBitmapsDisposed'] == 19\",\"trial['pixelBitmapsDisposed'] == 36\",1)")
extra_summary='''
empty_summary=summarize
def summarize(raw):
    value=empty_summary(raw);trial=raw['cameraRaster'];fallback=trial['mergeFallback']
    assert fallback['passed'] and fallback['native']['equal'] and fallback['restore']['equal']
    assert not fallback['during']['presented'] and fallback['during']['fallbackReason']=='background-order-or-effects'
    assert fallback['resumed']['presented'] and fallback['merged']['maxAlpha']==0 and fallback['merged']['maxRGB']<=2
    assert fallback['startedAtMs']>=trial['timingEndAtMs']
    assert all(not p['layerVisible'][1] and not p['layerHasPixels'][1]
        for row in trial['windows'] for state in row['atlasStates'] for p in state['pages'])
    assert trial['timingEnd']['atlas']['backgroundMerges']>0
    value['backgroundMerge']=dict(updates=trial['timingEnd']['atlas']['backgroundMerges'],fallback=fallback,
        limitation='Only adjacent neutral background parents without foreign visible overlays qualify; other cases use native pixels.')
    return value

'''
run=once(run,'original_main=inspect.getsource(framework.framework.framework.main)',extra_summary+'original_main=inspect.getsource(framework.framework.framework.main)')
save('run.py',run)
save('README.md',f'''# 固定页背景合成候选

源SHA256 {digest}。基于65F48207空层候选，仍预留32张固定池位图/200MiB，上层背景槽保存原back+back2顺序的合成；下层槽保持隐藏。
仅两背景父层相邻、单位几何、normal混合、无透明度/滤镜/遮罩/颜色变换和未知可见子物体时适用，否则完全回原生。
原生借用像素不写；所有更新完成后才隐藏原图。共同revision、两层身份和显隐变化触发重合成，空洞/消失格同步清除。
没有加入旧background-v4/v5的400px逐块合成或不透明格式路线；这里合成已通过整页布局的中央320px数据。

仍含960移动/静止帧及原有画面/原生击墙/毁墙/资源验证；额外计时后临时改变背景父层alpha，必须原生回退精确、恢复后合成RGB≤2/alpha0。
共36截图。父层资格扫描与合成写入完整计入帧耗时。仅候选，不部署，不声称未经实测的收益。
''')
spec=importlib.util.spec_from_file_location('merged_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save('tests/SceneCameraRasterTrial.as',module.helper_source())
print('Prepared source only; presenter '+digest)
