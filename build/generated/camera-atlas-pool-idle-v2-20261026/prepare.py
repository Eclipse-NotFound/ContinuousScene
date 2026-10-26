"""Keep the candidate unchanged; select an exposed, visibly rendered native wall."""
from pathlib import Path
import importlib.util
import hashlib

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-idle-20261026'
assert hashlib.sha256((OLD/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()=='6651CCFF07F244B09C67B3D5D6E61DE80791696C4BFF25607B4FE0F92B1D2D3A'

def save(name,text):
    target=HERE/name;assert not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    if name.endswith('.py'):compile(text,name,'exec')
    target.write_text(text,'utf-8',newline='\n')

for name in ('run.py','probe_patch.py','SceneRasterPresentation.as'):
    text=(OLD/name).read_text('utf-8-sig').replace('camera-atlas-pool-idle-1','camera-atlas-pool-idle-2')
    if name=='probe_patch.py':
        before="'    import flash.utils.getDefinitionByName;\\n    import flash.utils.getQualifiedClassName;'"
        after="'    import flash.display.PNGEncoderOptions;\\n    import flash.filesystem.File;\\n    import flash.filesystem.FileMode;\\n    import flash.filesystem.FileStream;\\n    import flash.utils.getDefinitionByName;\\n    import flash.utils.getQualifiedClassName;'"
        assert text.count(before)==1;text=text.replace(before,after,1)
    save(name,text)

source=(OLD/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig')
begin=source.index('        private function stationaryFixture(')
end=source.index('        private function stationaryRefresh(',begin)
replacement='''        private function stationaryFixture(breakWall:Boolean,screen:BitmapData):Object {
            // sceneViewport includes an 80px prefetch border; use the actual
            // Stage viewport, avoid HUD, and require an exposed bright face.
            var view:Rectangle=new Rectangle(-cam.vx,-cam.vy,cam.screenX,cam.screenY);
            var left:int=Math.max(1,Math.ceil((view.left+160)/40)),right:int=Math.min(location.spaceX-2,Math.floor((view.right-160)/40));
            var top:int=Math.max(1,Math.ceil((view.top+180)/40)),bottom:int=Math.min(location.spaceY-2,Math.floor((view.bottom-180)/40));
            var best:Object=null,bestDistance:Number=Number.POSITIVE_INFINITY;
            var surfaces:Array=grafon.sceneSurfaces();
            for(var y:int=top;y<=bottom;++y)for(var x:int=left;x<=right;++x) {
                var t:*=location.getTile(x,y),px:Number=x*40+20,py:Number=y*40+20;
                if(!t || t.phis!=1 || t.fake || t.trap || t.door || t.front=="" || t.water>0 || t.mat<1 || t.mat>6 || t.mat==5 || !(t.hp>0))continue;
                if(breakWall && (t.indestruct || !isFinite(t.hp) || !isFinite(t.thre) || (!location.destroyOn && t.hp>500)))continue;
                var dx:int=0,dy:int=0;
                var neighbor:*=location.getTile(x-1,y);
                if(neighbor && neighbor.phis==0){dx=1;px=t.phX1+2;}
                else {
                    neighbor=location.getTile(x,y-1);
                    if(neighbor && neighbor.phis==0){dy=1;py=t.phY1+2;}
                    else continue;
                }
                if(px<t.phX1 || px>t.phX2 || py<t.phY1 || py>t.phY2)continue;
                var sx:int=int(px+cam.vx),sy:int=int(py+cam.vy);
                if(sx<160 || sx>=screen.width-160 || sy<180 || sy>=screen.height-180)continue;
                var color:uint=screen.getPixel(sx,sy);
                if(Math.max(color>>>16&255,color>>>8&255,color&255)<24)continue;
                var nativeVisible:Boolean=false;
                for each(var surface:Object in surfaces)if(surface.cx==int(px/320) && surface.cy==int(py/320)) {
                    var bitmap:Bitmap=surface.bitmaps[0];
                    if(bitmap.visible && bitmap.parent!=null && bitmap.parent.visible &&
                        (surface.nativeBuffers[0].getPixel32(int(px)-surface.cx*320+surface.gutter,int(py)-surface.cy*320+surface.gutter)>>>24)>0)nativeVisible=true;
                    break;
                }
                if(!nativeVisible)continue;
                var distance:Number=Math.abs(sx-screen.width/2)+Math.abs(sy-screen.height/2);
                if(distance>=bestDistance)continue;
                bestDistance=distance;
                best={x:px,y:py,tileX:x,tileY:y,material:t.mat,hp:t.hp,threshold:t.thre,dx:dx,dy:dy,screenX:sx,screenY:sy,screenRGB:color};
            }
            return best;
        }

        private function mutationDiagnostic(name:String,data:BitmapData):String {
            var folder:File=File.applicationStorageDirectory.resolvePath("mutation-diagnostics");folder.createDirectory();
            var target:File=folder.resolvePath(name+".png"),stream:FileStream=new FileStream();
            try {stream.open(target,FileMode.WRITE);stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally {stream.close();}return target.nativePath;
        }

'''
source=source[:begin]+replacement+source[end:]
edits=[
    ('var fixture:Object=stationaryFixture(breakWall);item.fixture=fixture;',
     'var beforeImage:BitmapData=capture();\n                var fixture:Object=stationaryFixture(breakWall,beforeImage);item.fixture=fixture;'),
    ('var beforeImage:BitmapData=capture();item.before=presenter.snapshot();','item.before=presenter.snapshot();'),
    ('new Bullet(player,fixture.x-1,fixture.y,null,false);','new Bullet(player,fixture.x-fixture.dx,fixture.y-fixture.dy,null,false);'),
    ('bullet.dx=1;bullet.dy=0;bullet.vel=1;','bullet.dx=fixture.dx;bullet.dy=fixture.dy;bullet.vel=1;'),
    ('            } finally {presenter.beginFrame();disposeOwned();item.endedAtMs=getTimer();}',
'''            } catch(error:Error) {
                if(beforeImage)item.beforePNG=mutationDiagnostic((breakWall?"break":"impact")+"-before",beforeImage);
                if(changed)item.changedPNG=mutationDiagnostic((breakWall?"break":"impact")+"-changed",changed);
                throw error;
            } finally {presenter.beginFrame();disposeOwned();item.endedAtMs=getTimer();}''')]
for before,after in edits:
    assert source.count(before)==1;source=source.replace(before,after,1)
save('tests/StationaryRefresh.as.inc',source)
save('README.md','''# 固定池静止路径 v2：可见墙面夹具

呈现器仍为6651CCFF，未变更。v1完成960帧但击墙只改变revision、Stage像素0变化，按原门槛失败；原证据不改。
原夹具把包含80px预绘边框的sceneViewport当成实视口，且没有检查墙面是否在屏幕上可见。
v2使用实际Stage矩形，避开HUD，选择有空气相邻的亮墙面且原生前景有alpha；在外露边缘产生同一原生子弹撞击。
仍要求完整截图非空变化、revision变化、静止精确、恢复移动RGB≤2/alpha0，任何失败留PNG。
原960帧、19基础截图、12终态截图、资源/计数/隔离与4GB内存门禁保留。不代表玩家开火或实战验收，不部署。
''')
spec=importlib.util.spec_from_file_location('idle2_patch',HERE/'probe_patch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
save('tests/SceneCameraRasterTrial.as',module.helper_source())
print('Prepared v2 source only; candidate is still 6651CCFF')
