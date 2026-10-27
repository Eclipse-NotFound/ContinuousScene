        private function selectReferenceSite():void {
            var ox:int=grafon.sceneLarge?96:0,oy:int=grafon.sceneLarge?75:0;
            var candidates:Array=[],best:Object=null;
            // Keep both axes inside the native room's camera limits. A full body
            // fits on three solid cells with three cells of clear space above.
            for(var cy:int=13;cy<=17;++cy)for(var cx:int=20;cx<=28;++cx) {
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
                var score:Number=Math.abs(cx*40+20-960)+Math.abs(cy*40-600);
                var c:Object={x:x,y:y,localX:cx*40+20,localY:cy*40,score:score};candidates.push(c);
                if(!best || score<best.score)best=c;
            }
            report.referenceSite={roomX:2,roomY:3,candidates:candidates,selected:best,terrainEdited:false,spawnCalls:0};
            require(best!=null,"No verified visible reference platform in room 2,3");
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
