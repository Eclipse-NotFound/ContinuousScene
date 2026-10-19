package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;
    public class BoundaryWallProbe {
        private static var main:*,w:*,api:*,prepare:Function,records:Array=[];
        private static var phase:int=0,ready:int=0,start:int,done:Boolean=false,config:Object;
        private static var result:Object={checks:[],samples:[],probe:"boundary-wall-2"};
        private static var damageRecord:Object;
        public static function init(host:*):void {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-cs-boundary-")!=0)return;
            main=host;start=getTimer();config=JSON.parse(read(File.applicationDirectory.resolvePath("boundary-test.json")));
            result.map=config.map;result.enabled=config.enabled;
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1100);
        }
        private static function read(file:File):String {var s:FileStream=new FileStream();s.open(file,FileMode.READ);var t:String=s.readUTFBytes(s.bytesAvailable);s.close();return t;}
        private static function write(name:String,value:*):void {var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);s.writeUTFBytes(JSON.stringify(value,null,2));s.close();}
        private static function check(name:String,ok:Boolean,detail:*=null):void {result.checks.push({name:name,ok:ok,detail:detail});}
        private static function image(name:String):void {var b:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);b.draw(main.stage);var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);s.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));s.close();b.dispose();}
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-start>180000)throw new Error("Timeout phase="+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded) {
                    var c:*=main.getChildByName("ContinuousSceneCarrier"),s:*=main.getChildByName("ModSettingsCarrier");
                    if(!c || !c.sceneAPI.ready || !s || !s.modAPI)return;
                    var set:Boolean=false;
                    for each(var page:Object in s.modAPI.getPages())if(page.modId=="continuousscene")for each(var item:Object in page.items)if(item.key=="nativeEnabled"){item["set"](config.enabled);set=item["get"]()===config.enabled;}
                    if(!set)return;
                    result.version=c.sceneAPI.version;api=c.nativeAPI;prepare=api.prepare;
                    api.prepare=function(land:*):Object {
                        if(land.act.id!=config.map)return prepare(land);
                        capture(land);var state:Object=prepare(land);compare(state);return state;
                    };
                    w.grafon.scenePreload=false;w.mm.active=false;w.newGame(-1,"Boundary Wall",{propusk:true});phase=1;
                }else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<20)return;w.ctr.clearAll();w.pers.healAll();w.game.beginMission(config.map);phase=2;ready=0;
                }else if(phase==2 && w.land && w.land.act.id==config.map && w.game.curLandId==config.map && w.t_exit==0 && w.allStat==1 && ++ready>=16) {
                    check("captured-native-generation",records.length>0);
                    check("mode-matches-request",Boolean(api.state(w.land))==Boolean(config.enabled));
                    fixtures();
                    if(config.enabled && result.eligible>0){
                        for each(var r:Object in records)if(r.eligible && !r.tile.indestruct){damageRecord=r;break;}
                        check("native-hit-coverage",damageRecord!=null);
                        if(!damageRecord){finish();return;}
                        holdPosition();phase=3;ready=0;
                    }else finish();
                }else if(phase==3){holdPosition();if(++ready>=12){damage();phase=4;ready=0;}}
                else if(phase==4){holdPosition();if(++ready>=8){image("after-damage");finish();}}
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static function capture(land:*):void {
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class,Form:Class=getDefinitionByName("fe.loc.Form") as Class;
            result.border=land.act.border;result.rooms=0;result.eligible=0;result.protected=0;result.outside=0;
            for(var lx:int=land.minLocX;lx<land.maxLocX;lx++)for(var ly:int=land.minLocY;ly<land.maxLocY;ly++){
                var loc:*=land.locs[lx][ly][0];if(!loc)continue;result.rooms++;
                for(var y:int=0;y<25;y++){
                    var row:Array=String(loc.room.xml.a[y]).split(".");
                    for(var x:int=0;x<48;x++) {
                        var t:*=loc.space[x][y],edge:Boolean=x==0 || x==47 || y==0 || y==24;
                        var exterior:Boolean=(x==0 && !neighbor(land,lx-1,ly)) || (x==47 && !neighbor(land,lx+1,ly)) || (y==0 && !neighbor(land,lx,ly-1)) || (y==24 && !neighbor(land,lx,ly+1));
                        var nativeTile:*=null,f:*=Form.fForms[t.front],eligible:Boolean=false;
                        if(edge && !exterior && t.indestruct && t.phis==1 && !t.door && !t.trap && f && !f.indestruct && f.hp>0){
                            var token:String=row[loc.mirror?47-x:x];nativeTile=new Tile(x,y);nativeTile.dec(token==null?"":token,loc.mirror);
                            eligible=nativeTile.phis>0 && !nativeTile.indestruct && t.front==land.act.border && t.hp==10000;
                        }
                        if(eligible)result.eligible++;if(edge && exterior && t.phis==1)result.outside++;
                        if(edge && t.indestruct && f && f.indestruct)result.protected++;
                        records.push({tile:t,x:x+(lx-land.minLocX)*48,y:y+(ly-land.minLocY)*25,eligible:eligible,hp:t.hp,thre:t.thre,indestruct:t.indestruct,front:t.front,back:t.back,mat:t.mat,phis:t.phis,door:t.door,trap:t.trap,expectedHp:eligible?f.hp:t.hp,expectedThre:eligible?f.thre:t.thre});
                    }
                }
            }
        }
        private static function neighbor(land:*,x:int,y:int):Boolean {return x>=land.minLocX && x<land.maxLocX && y>=land.minLocY && y<land.maxLocY && land.locs[x][y] && land.locs[x][y][0]!=null;}
        private static function compare(state:Object):void {
            var changed:int=0,bad:int=0,untouched:int=0,geometry:int=0;
            for each(var r:Object in records){var t:*=r.tile;
                if(config.enabled && r.eligible){
                    if(!t.indestruct && t.hp==r.expectedHp && t.thre==r.expectedThre)changed++;else {bad++;if(result.samples.length<8)result.samples.push({x:r.x,y:r.y,hp:t.hp,expectedHp:r.expectedHp,indestruct:t.indestruct,front:t.front});}
                }else if(t.indestruct!=r.indestruct || t.hp!=r.hp || t.thre!=r.thre)untouched++;
                if(t.front!=r.front || t.back!=r.back || t.phis!=r.phis || t.mat!=r.mat || t.door!==r.door || t.trap!==r.trap)geometry++;
            }
            result.restored=changed;
            check("all-eligible-internal-walls-restored",bad==0,{eligible:result.eligible,restored:changed});
            check("all-other-tiles-preserved",untouched==0,untouched);
            check("appearance-collision-objects-preserved",geometry==0,geometry);
            check("outer-boundary-coverage",result.outside>0,result.outside);
            if(config.map=="random_mane")check("breakable-seam-coverage",result.eligible>0,result.eligible);
            if(config.map=="random_plant")check("intrinsic-steel-coverage",result.protected>0,result.protected);
        }
        private static function holdPosition():void {
            var t:*=damageRecord.tile;w.gg.setLocPos(t.X*40-80,t.Y*40-60);w.gg.dx=w.gg.dy=0;w.cam.calc(w.gg);
        }
        private static function damage():void {
            var r:Object=damageRecord,item:Object;
            var t:*=r.tile,loc:*=w.loc,x:Number=t.X*40+20,y:Number=t.Y*40+20;
            w.grafon.sceneTick();image("before-damage");
            var hp:int=t.hp;loc.hitTile(t,Math.max(0,t.thre-1),x,y,9);
            check("native-threshold-still-blocks-small-hit",t.hp==hp && t.phis==1,{hp:t.hp,threshold:t.thre});
            var hit:int=Math.max(t.thre,Math.min(hp-1,Math.max(1,int(hp/2))));loc.hitTile(t,hit,x,y,9);
            check("native-hit-decreases-health",t.hp==hp-hit && t.phis==1,{before:hp,after:t.hp,damage:hit});
            loc.hitTile(t,Math.max(t.hp,t.thre)+1,x,y,9);
            check("native-hit-removes-collision-and-foreground",t.phis==0 && t.front=="" && t.opac==0,{x:t.X,y:t.Y,hp:t.hp,phis:t.phis,front:t.front});
            check("native-destruction-invalidates-render",w.grafon.sceneLastDirtyCount>0,w.grafon.sceneLastDirtyCount);
            for each(item in records)if(item.indestruct && !item.eligible && item.tile.phis==1){var p:*=item.tile,oldHp:int=p.hp;loc.hitTile(p,100000,p.X*40+20,p.Y*40+20,9);check("protected-wall-rejects-native-hit",p.indestruct && p.hp==oldHp && p.phis==1);break;}
        }
        private static function fixtures():void {
            // Focused protection controls use real native Tile.dec and the exact
            // production helper, separately from the actual mission integration.
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class;
            var regions:Array=[];
            for each(var lx:int in [0,1,3]) {
                var grid:Array=[],xml:XML=<room/>;
                for(var x:int=0;x<48;x++)grid[x]=[];
                for(var y:int=0;y<25;y++) {
                    var row:Array=[];
                    for(x=0;x<48;x++) {
                        var code:String=(x==47 && y==4)?"A":"C";
                        var t:*=new Tile(x,y);t.dec(code);t.indestruct=true;
                        grid[x][y]=t;row.push(code);
                    }
                    xml.appendChild(<a>{row.join(".")}</a>);
                }
                var source:Object={room:{xml:xml},mirror:false};
                regions.push({source:source,lx:lx,ly:0,space:grid});
            }
            var a:Array=regions[0].space,b:Array=regions[1].space;
            a[47][3].hp=350;a[47][5].hp=1600;
            // door/trap typed fields cannot accept artificial values; real mission
            // snapshots above verify those object references remain unchanged.
            NativeSceneWalls.restore({rnd:false,act:{border:"C"}},regions);
            check("fixed-map-restores-flag-preserves-damage",!a[47][3].indestruct && a[47][3].hp==350 && a[47][3].thre==100);
            check("fixed-map-intrinsic-steel-stays-protected",a[47][4].indestruct);
            check("unknown-health-override-is-preserved",a[47][5].indestruct && a[47][5].hp==1600);
            check("world-edge-and-corner-stay-protected",a[0][3].indestruct && a[47][0].indestruct);
            check("both-sides-of-internal-seam-restore",!b[0][3].indestruct);
            check("missing-neighbor-stays-protected",b[47][3].indestruct && regions[2].space[0][3].indestruct);
            var count:int=NativeSceneWalls.restore({rnd:false,act:{border:"C"}},regions);
            check("restoration-is-idempotent",count==0 && a[47][3].hp==350);
            // A mirrored template puts its intrinsic steel protection on the left.
            regions[1].source.mirror=true;b[0][4].dec("C");b[0][4].indestruct=true;
            NativeSceneWalls.restore({rnd:false,act:{border:"C"}},regions);
            check("mirrored-intrinsic-protection-is-preserved",b[0][4].indestruct);
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;if(api && prepare!=null)api.prepare=prepare;
            result.error=error;result.ok=error==null;result.elapsedMs=getTimer()-start;
            for each(var c:Object in result.checks)if(!c.ok)result.ok=false;
            write("boundary-result.json",result);NativeApplication.nativeApplication.exit(result.ok?0:1);
        }
    }
}
