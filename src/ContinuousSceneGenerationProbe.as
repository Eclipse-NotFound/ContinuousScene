package {
    import flash.desktop.NativeApplication;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;
    /** Repeats native stage-5 generation with merging disabled; no performance claims. */
    public class ContinuousSceneGenerationProbe {
        private static var main:*,w:*,phase:int=0,ready:int=0,round:int=0,started:int,done:Boolean=false;
        private static var report:Object={mode:"native-generation",assertions:[],entries:[],seed:4077752896};
        public static function init(host:*):void {
            main=host;started=getTimer();main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-500);
        }
        private static function settingsReady():Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c || !c["modAPI"])return false;
            for each(var page:Object in c["modAPI"].getPages())if(page.modId=="continuousscene")
                for each(var item:Object in page.items)if(item.key=="nativeEnabled"){item["set"](false);return true;}
            return false;
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;report.ok=error==null;report.error=error;report.elapsedMs=getTimer()-started;
            if(error) {
                report.suspects=[];
                try {
                    var land:*=w.game.curLand.land;
                    if(land)for(var x:int=land.minLocX;x<land.maxLocX;++x)for(var y:int=land.minLocY;y<land.maxLocY;++y)
                        for each(var loc:* in land.locs[x][y])if(loc)for each(var u:* in loc.units)if(u && u!==w.gg) {
                            if(String(u.nazv).toLowerCase().indexOf("scorpion")<0 && u.X>=0 && u.X<=loc.limX && u.Y>=0 && u.Y<=loc.limY)continue;
                            report.suspects.push({type:getQualifiedClassName(u),name:u.nazv,room:loc.id,x:u.X,y:u.Y,
                                x1:u.X1,x2:u.X2,y1:u.Y1,y2:u.Y2,dx:u.dx,dy:u.dy,limX:loc.limX,limY:loc.limY});
                        }
                }catch(ignore:Error){report.captureError=String(ignore);}
            }
            var f:FileStream=new FileStream();f.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            f.writeUTFBytes(JSON.stringify(report,null,2));f.close();NativeApplication.nativeApplication.exit(error?1:0);
        }
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-started>420000)throw new Error("Generation timeout phase="+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settingsReady()) {
                    w.mm.active=false;w.newGame(-1,"Native generation",{propusk:true});phase=1;
                }else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc && w.t_exit==0) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;ready=0;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function(land:*):uint{return 4077752896;};
                    w.ctr.clearAll();w.pers.healAll();w.game.lands["random_mane"].landStage=4;
                    w.game.beginMission("random_mane");phase=2;
                }else if(phase==2 && w.land && w.land.act.id=="random_mane" && w.t_exit==0 && w.allStat==1) {
                    if(++ready<20)return;ready=0;
                    if(w.grafon.sceneLarge || w.loc.spaceX!=48 || w.loc.spaceY!=25)throw new Error("Expected original rooms");
                    if(w.land.rconnectLayoutSeed!=4077752896)throw new Error("Seed override missing");
                    report.assertions.push({name:"native-generation-"+round,ok:true});
                    report.entries.push({round:round,stage:w.land.act.landStage,seed:w.land.rconnectLayoutSeed,units:w.loc.units.length});
                    if(++round>=6){finish();return;}
                    w.ctr.clearAll();w.pers.healAll();w.game.gotoLand(w.game.baseId);phase=3;
                }else if(phase==3 && w.land && w.land.act.id==w.game.baseId && w.t_exit==0 && w.allStat==1) {phase=1;ready=0;}
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
    }
}
