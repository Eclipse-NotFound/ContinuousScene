package {
    import flash.desktop.NativeApplication;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Private, deterministic native Unit.run boundary reproduction, then native mission entries. */
    public class ContinuousSceneMotionMod {
        private static var main:*,w:*,phase:int=0,ready:int=0,started:int,round:int=0,done:Boolean=false;
        private static var plan:Object,report:Object={ok:false,assertions:[],cases:[],entries:[]};
        public static function init(host:*):void {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)return;
            main=host;started=getTimer();
            var fs:FileStream=new FileStream();fs.open(File.applicationDirectory.resolvePath("unit-boundary-plan.json"),FileMode.READ);
            plan=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));fs.close();report.plan=plan;
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-500);
        }
        private static function check(name:String,ok:Boolean):void {
            report.assertions.push({name:name,ok:ok});if(!ok)throw new Error("Check failed: "+name);
        }
        private static function settings(enabled:Boolean):Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c || !c["modAPI"])return false;
            for each(var page:Object in c["modAPI"].getPages())if(page.modId=="continuousscene")
                for each(var item:Object in page.items)if(item.key=="nativeEnabled"){item["set"](enabled);return true;}
            return false;
        }
        private static function snapshot(u:*):Object {
            return {type:getQualifiedClassName(u),x:u.X,y:u.Y,x1:u.X1,x2:u.X2,y1:u.Y1,y2:u.Y2,
                dx:u.dx,dy:u.dy,scX:u.scX,scY:u.scY,stay:u.stay,spaceX:u.loc.spaceX,spaceY:u.loc.spaceY};
        }
        private static function boundaryCase(id:String,right:Boolean):void {
            var loc:*=w.loc,row:int=8,col:int=right?loc.spaceX-1:0;
            var tile:*=loc.space[col][row];var prior:Object={};
            var names:Array=["phis","mat","phX1","phX2","phY1","phY2","shelf","zForm"];
            var unit:*,result:Object={id:id,side:right?"right":"left",row:row,col:col};
            for each(var key:String in names)prior[key]=tile[key];
            try {
                tile.phis=1;tile.mat=0;tile.shelf=false;tile.zForm=0;
                tile.phX1=col*40;tile.phX2=(col+1)*40;tile.phY1=row*40;tile.phY2=(row+1)*40;
                unit=getDefinitionByName("fe.unit.Unit")["create"](id,1);
                check(id+"-created-"+result.side,unit!=null);
                unit.putLoc(loc,right?loc.limX-unit.scX/2-1:unit.scX/2+1,row*40+35);
                unit.dx=right?-1:1;unit.dy=1;unit.osndx=unit.osndy=0;
                unit.stay=false;unit.isLaz=0;unit.throu=false;unit.mater=true;
                unit.isFly=false;unit.levit=false;unit.isPlav=false;unit.t_throw=0;
                result.before=snapshot(unit);
                try {unit.run();result.error=null;}catch(error:Error){result.error={id:error.errorID,text:String(error),stack:error.getStackTrace()};}
                result.after=snapshot(unit);
                result.outsideColumn=unit.X1<0 || unit.X2>=loc.limX;
                report.cases.push(result);
                check(id+"-actual-native-run-"+result.side,plan.expectError ? result.error!=null && result.error.id==1010 : result.error==null);
                if(!plan.expectError){unit.run();check(id+"-recovers-inside-"+result.side,unit.X1>=0 && unit.X2<loc.limX);}
            } finally {
                for each(key in names)tile[key]=prior[key];
                if(unit)unit.remVisual();
            }
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;main.stage.removeEventListener(Event.ENTER_FRAME,tick);
            report.ok=error==null;report.error=error;report.elapsedMs=getTimer()-started;
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            fs.writeUTFBytes(JSON.stringify(report,null,2));fs.close();NativeApplication.nativeApplication.exit(error?1:0);
        }
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-started>420000)throw new Error("Timed out in phase "+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settings(false)) {
                    w.mm.active=false;w.newGame(-1,"Boundary regression",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc && w.t_exit==0) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;ready=0;w.ctr.clearAll();
                    boundaryCase("molerat",false);boundaryCase("molerat",true);
                    if(plan.rounds==0){finish();return;}
                    phase=2;
                } else if(phase==2) {
                    settings(round%2==1);w.pers.healAll();w.game.lands["random_mane"].landStage=4;
                    getDefinitionByName("fe.loc.Land")["rconnectSeedSource"]=function(land:*):uint{return 4077752896;};
                    w.game.beginMission("random_mane");phase=3;
                } else if(phase==3 && w.land && w.land.act.id=="random_mane" && w.t_exit==0 && w.allStat==1) {
                    if(++ready<30)return;ready=0;
                    check("entry-"+round+"-mode",Boolean(w.grafon.sceneLarge)==(round%2==1));
                    report.entries.push({round:round,large:w.grafon.sceneLarge,stage:w.land.act.landStage,seed:w.land.rconnectLayoutSeed});
                    if(++round>=plan.rounds){finish();return;}
                    w.ctr.clearAll();w.pers.healAll();w.game.gotoLand(w.game.baseId);phase=4;
                } else if(phase==4 && w.land && w.land.act.id==w.game.baseId && w.t_exit==0 && w.allStat==1) {phase=2;ready=0;}
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
    }
}
