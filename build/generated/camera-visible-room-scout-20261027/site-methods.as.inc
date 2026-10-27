        private function selectReferenceSite():void {
            var ox:int=0,oy:int=0;
            var candidates:Array=[],best:Object=null;
            // Keep both axes inside the native room's camera limits. A full body
            // fits on three solid cells with three cells of clear space above.
            for(var ry:int=0;ry<(grafon.sceneLarge?5:1);++ry)for(var rx:int=0;rx<(grafon.sceneLarge?5:1);++rx) {
            ox=rx*48;oy=ry*25;
            for(var cy:int=8;cy<=22;++cy)for(var cx:int=20;cx<=28;++cx) {
                var good:Boolean=true;
                for(var dx:int=-1;dx<=1 && good;++dx) {
                    var tile:*=location.space[ox+cx+dx][oy+cy];
                    if(!tile || tile.phis!=1 || tile.diagon || tile.shelf || tile.door || tile.water || tile.trap || tile.stair ||
                       tile.phY1!=(oy+cy)*40 || tile.phX1>(ox+cx+dx)*40 || tile.phX2<(ox+cx+dx+1)*40) {good=false;break;}
                    for(var dy:int=1;dy<=3;++dy) {
                        tile=location.space[ox+cx+dx][oy+cy-dy];
                        if(!tile || tile.phis || tile.diagon || tile.shelf || tile.door || tile.water || tile.trap || tile.stair){good=false;break;}
                    }
                }
                var x:Number=(ox+cx)*40+20,y:Number=(oy+cy)*40;
                for each(var obj:* in location.objs) {
                    if(!good)break;
                    if(!obj || ("dead" in obj && obj.dead))continue;
                    if(!(("phis" in obj && obj.phis>0)||("shelf" in obj && obj.shelf)||("wall" in obj && obj.wall>0)||("door" in obj && obj.door>0)))continue;
                    if(Number(obj.X1)<x+25 && Number(obj.X2)>x-25 && Number(obj.Y1)<y && Number(obj.Y2)>y-120)good=false;
                }
                if(!good)continue;
                var roomX:int=grafon.sceneLarge?rx:int(world.land.locX),roomY:int=grafon.sceneLarge?ry:int(world.land.locY);
                var score:Number=(Math.abs(roomX-2)+Math.abs(roomY-3))*10000+Math.abs(cx*40+20-960)+Math.abs(cy*40-600);
                var c:Object={x:x,y:y,localX:cx*40+20,localY:cy*40,roomX:roomX,roomY:roomY,score:score};candidates.push(c);
                if(!best || score<best.score)best=c;
            }
            }
            report.referenceSite={roomX:best?best.roomX:-1,roomY:best?best.roomY:-1,candidates:candidates,selected:best,terrainEdited:false,spawnCalls:0};
            require(best!=null,"No verified visible reference platform in scanned rooms");
            ox=grafon.sceneLarge?best.roomX*48:0;oy=grafon.sceneLarge?best.roomY*25:0;
            var tileHash:uint=0;
            for(cx=0;cx<48;++cx)for(cy=0;cy<25;++cy) {
                tile=location.space[ox+cx][oy+cy];
                var value:String=[tile.front,tile.back,tile.phis,tile.diagon,tile.zForm,tile.door].join(":");
                for(var k:int=0;k<value.length;++k)tileHash=uint(tileHash*31+value.charCodeAt(k));
            }
            report.referenceSite.tileHash=tileHash;
            player.setLocPos(best.x,best.y-1);player.dx=player.dy=0;++report.referenceSite.spawnCalls;
            // Measurement waits for full route preparation plus 60 frames.
            // No later positioning, velocity writes or camera-bound changes.
        }
        private function coverage(b:BitmapData):Object {
            var pixels:Vector.<uint>=b.getVector(new Rectangle(96,80,stage.stageWidth-192,stage.stageHeight-160)),count:int=0;
            for(var i:int=0;i<pixels.length;++i) {
                var p:uint=pixels[i];if(Math.max(p>>>16&255,p>>>8&255,p&255)>20)++count;
            }
            return {colored:count,pixels:pixels.length,fraction:count/pixels.length,excludesMainHudMargins:true};
        }
        private function savePNG(name:String,b:BitmapData):void {
            var f:FileStream=new FileStream();
            try {f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {f.close();}
        }
