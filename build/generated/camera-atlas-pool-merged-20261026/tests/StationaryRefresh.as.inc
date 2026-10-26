        private function stationaryFixture(breakWall:Boolean,screen:BitmapData):Object {
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

        private function stationaryRefresh(breakWall:Boolean):void {
            var item:Object={breakWall:breakWall,passed:false,startedAtMs:getTimer()};
            report.stationaryRefresh.push(item);
            try {
                presenter.beginFrame();applyCamera(views[0].x,views[0].y);
                require(grafon.sceneViewReady(),"Mutation viewport must already be resident");
                // Populate a genuinely current cache before changing native pixels.
                presenter.update(world,true,true);require(presenter.presented,"Mutation cache not populated");
                presenter.beginFrame();
                var beforeImage:BitmapData=capture();
                var fixture:Object=stationaryFixture(breakWall,beforeImage);item.fixture=fixture;
                require(fixture!=null,"No visible native wall fixture; do not silently skip mutation coverage");
                var revisions:Array=[];
                for each(var surface:Object in grafon.sceneSurfaces())revisions.push({surface:surface,revision:surface.revision});
                item.before=presenter.snapshot();
                if(breakWall) {
                    var tile:*=location.getTile(fixture.tileX,fixture.tileY);
                    var damage:Number=Math.max(Number(tile.hp),Number(tile.thre))+1;
                    location.hitTile(tile,damage,fixture.x,fixture.y,1);
                    item.nativeAction={phis:tile.phis,hp:tile.hp,damage:damage};
                    require(tile.phis==0,"Native wall did not break");
                } else {
                    var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
                    var bullet:*=new Bullet(player,fixture.x-fixture.dx,fixture.y-fixture.dy,null,false);
                    bullet.dx=fixture.dx;bullet.dy=fixture.dy;bullet.vel=1;bullet.damage=0;bullet.destroy=0;
                    bullet.damageExpl=0;bullet.explRadius=0;bullet.tipDecal=1;bullet.partEmit=false;bullet.off=true;
                    bullet.run();
                    item.nativeAction={tilehit:bullet.tilehit,babah:bullet.babah,detached:true,unitCollisionSkipped:true};
                    require(bullet.tilehit && bullet.babah,"Native bullet did not hit the wall");
                }
                var changed:BitmapData=capture();item.nativeChanged=compare(beforeImage,changed);
                item.changedSurfaceRevisions=0;
                for each(var previousSurface:Object in revisions)if(previousSurface.surface.revision!==previousSurface.revision)++item.changedSurfaceRevisions;
                require(item.nativeChanged.differentPixels>0 && item.changedSurfaceRevisions>0,"Native mutation produced no visible pixel/revision change");
                // No frame advance or sceneTick between mutation and static readback.
                presenter.update(world,true);item.skipped=presenter.snapshot();
                require(!presenter.presented && item.skipped.stationarySkips==item.before.stationarySkips+1,"Stationary shortcut not used");
                require(item.skipped.copies==item.before.copies && item.skipped.rebuilds==item.before.rebuilds,"Stationary shortcut copied pixels");
                var staticImage:BitmapData=capture();item.staticExact=compare(changed,staticImage);
                require(item.staticExact.equal,"Static path concealed a native mutation");
                applyCamera(views[0].x+4,views[0].y);require(grafon.sceneViewReady(),"Resume view not ready");
                var movedNative:BitmapData=capture();presenter.update(world,true);item.moving=presenter.snapshot();
                require(presenter.presented && item.moving.copies>item.skipped.copies,"Moving resume did not synchronize changed pixels");
                var movedAtlas:BitmapData=capture();item.movingPixels=compare(movedNative,movedAtlas);
                require(item.movingPixels.maxAlpha==0 && item.movingPixels.maxRGB<=2,"Moving resume contains stale or invalid pixels");
                presenter.beginFrame();var restored:BitmapData=capture();item.restoreExact=compare(movedNative,restored);
                require(item.restoreExact.equal,"Moving resume did not restore native pixels exactly");
                guard();item.passed=true;
            } catch(error:Error) {
                if(beforeImage)item.beforePNG=mutationDiagnostic((breakWall?"break":"impact")+"-before",beforeImage);
                if(changed)item.changedPNG=mutationDiagnostic((breakWall?"break":"impact")+"-changed",changed);
                throw error;
            } finally {presenter.beginFrame();disposeOwned();item.endedAtMs=getTimer();}
        }
