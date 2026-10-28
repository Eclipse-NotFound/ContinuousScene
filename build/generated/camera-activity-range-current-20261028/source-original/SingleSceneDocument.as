package {
    /** Shared editor/runtime format. One room owns every tile and object. */
    public final class SingleSceneDocument {
        public static const MIN_WIDTH:int=48, MIN_HEIGHT:int=25, MAX_WIDTH:int=512, MAX_HEIGHT:int=256;
        public static function validate(doc:XML, playable:Boolean=true):XML {
            var room:XML=doc.name()=="room"?doc:doc.room[0];
            if(!room || (doc.name()!="room" && doc.room.length()!=1)) throw new Error("大地图文件必须恰好包含一个场景。");
            var w:Number=Number(room.@sceneWidth),h:Number=Number(room.@sceneHeight);
            if(w!=int(w)||h!=int(h)||w<MIN_WIDTH||h<MIN_HEIGHT||w>MAX_WIDTH||h>MAX_HEIGHT)
                throw new Error("地图尺寸须为整数：宽 48–512 格，高 25–256 格。");
            if(room.a.length()!=h) throw new Error("地图行数与高度不一致。");
            for(var y:int=0;y<h;y++) if(String(room.a[y]).split(".").length!=w)
                throw new Error("第 "+(y+1)+" 行的格数与宽度不一致。");
            var players:int=0;
            for each(var obj:XML in room.obj) {
                var x:Number=Number(obj.@x),oy:Number=Number(obj.@y);
                if(!obj.@x.length()||!obj.@y.length()||!isFinite(x)||!isFinite(oy)||x<0||oy<0||x>=w||oy>=h)
                    throw new Error("物体超出地图："+obj.@id+" ("+obj.@x+", "+obj.@y+")");
                if(String(obj.@id)=="player") {
                    players++;
                    if(playable && (x<1 || oy<2 || x>=w-1 || oy>=h-1)) throw new Error("出生点需要离开地图外沿。");
                }
            }
            if(playable && players!=1) throw new Error("请保留一个且仅一个 player 出生点（当前 "+players+" 个）。");
            return room;
        }
        public static function pack(room:XML, land:XML=null):XML {
            var r:XML=room.copy();r.@x=0;r.@y=0;delete r.@z;delete r.doors;
            // Content identity prevents terrain from another edited revision being restored.
            delete r.@sceneRevision;
            var value:String=r.toXMLString();var hash:uint=2166136261;
            for(var i:int=0;i<value.length;i++) {hash^=value.charCodeAt(i);hash+= (hash<<1)+(hash<<4)+(hash<<7)+(hash<<8)+(hash<<24);}
            r.@sceneRevision="authored-"+hash.toString(16);
            var all:XML=<all sceneFormat="1"/>;
            var l:XML=<land serial="1"/>;
            if(land && land.options.length()) l.appendChild(land.options[0].copy());
            all.appendChild(l);all.appendChild(r);validate(all);return all;
        }
        public static function blank(w:int,h:int):XML {
            if(w<MIN_WIDTH||h<MIN_HEIGHT||w>MAX_WIDTH||h>MAX_HEIGHT) throw new Error("地图尺寸超出支持范围。");
            var r:XML=<room name="新大地图" sceneWidth={w} sceneHeight={h} x="0" y="0"/>;
            r.appendChild(<options backwall="tBackWall" music="music_plant_2"/>);
            for(var y:int=0;y<h;y++) {
                var row:Array=[];
                for(var x:int=0;x<w;x++) row.push(x==0||y==0||x==w-1||y>=h-2?"A":"_");
                r.appendChild(<a>{row.join(".")}</a>);
            }
            r.appendChild(<obj id="player" x="5" y={h-3}/>);
            return pack(r);
        }
        /** Existing static renderer previews the 48x25 window around the edit viewport. */
        public static function window(room:XML, x:int,y:int):XML {
            var w:int=int(room.@sceneWidth),h:int=int(room.@sceneHeight);
            x=Math.max(0,Math.min(w-48,x));y=Math.max(0,Math.min(h-25,y));
            var r:XML=<room name={String(room.@name)+" · 局部 ("+x+", "+y+")"}/>;
            if(room.options.length()) r.appendChild(room.options[0].copy());
            for(var yy:int=0;yy<25;yy++) r.appendChild(<a>{String(room.a[y+yy]).split(".").slice(x,x+48).join(".")}</a>);
            for each(var region:XML in room.sceneRegions.region) {
                if(x+24>=Number(region.@x)&&x+24<Number(region.@x)+Number(region.@width)&&y+12>=Number(region.@y)&&y+12<Number(region.@y)+Number(region.@height)) {
                    for each(var attr:XML in region.attributes()) if(["backwall","color","dark","fon","music"].indexOf(String(attr.name()))>=0) r.options[0].@[attr.name()]=attr;
                }
            }
            for each(var node:XML in room.children()) if(node.name()=="obj"||node.name()=="back") {
                var nx:Number=Number(node.@x)-x,ny:Number=Number(node.@y)-y;
                if(nx<0||ny<0||nx>=48||ny>=25) continue;
                var c:XML=node.copy();c.@x=nx;c.@y=ny;r.appendChild(c);
            }
            return r;
        }
    }
}
