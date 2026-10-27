        private function fogState():Object {
            var site:Object=report.referenceSite;
            require(site!=null && site.selected!=null,"Fog observation requires selected reference room");
            var ox:int=grafon.sceneLarge?site.roomX*48:0,oy:int=grafon.sceneLarge?site.roomY*25:0;
            var cells:Array=[];
            for(var x:int=0;x<48;++x)for(var y:int=0;y<25;++y) {
                var tile:*=location.space[ox+x][oy+y];
                cells.push({x:x,y:y,visi:tile.visi,target:tile.t_visi,opacity:tile.opac,
                    mask:grafon.lightBmp.getPixel32(ox+x,oy+y+1),water:tile.water});
            }
            return {width:grafon.lightBmp.width,height:grafon.lightBmp.height,
                localCells:cells,lightVisible:grafon.visLight.visible,lightAlpha:grafon.visLight.alpha,
                lightScaleX:grafon.visLight.scaleX,lightScaleY:grafon.visLight.scaleY,
                relight:location.isRelight,relightTicks:location.relight_t,
                player:{x:player.X,y:player.Y,y1:player.Y1,stayY:player.stayY,direction:player.storona},
                black:location.black,retDark:location.retDark,lDist1:location.lDist1,lDist2:location.lDist2};
        }
