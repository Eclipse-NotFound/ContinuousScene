package {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.events.UncaughtErrorEvent;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;
    import tests.SceneObjectChecks;

    /** Independent, isolated native-entry oracle; no production sources altered. */
    public class ContinuousSceneObjectProbe {
        private static var main:*,w:*,api:*,originalPrepare:Function;
        private static var phase:int=0,ready:int=0,started:int,nextHeartbeat:int;
        private static var done:Boolean=false,target:String,interactions:GeneratedInteractions;
        private static var report:Object={probe:"native-object-audit-1",checks:[]};
        public static function init(host:*):void {
            if(NativeApplication.nativeApplication.applicationID!="pfe-modsettings-continuous-objects-01a151d4") return;
            main=host;started=getTimer();
            var fs:FileStream=new FileStream();fs.open(File.applicationDirectory.resolvePath("object-map.txt"),FileMode.READ);
            target=fs.readUTFBytes(fs.bytesAvailable).replace(/\s/g,"");fs.close();
            if(target!="random_plant" && target!="random_mane") throw new Error("Unsupported object map");
            report.map=target;
            main.stage.addEventListener(Event.ENTER_FRAME,before,false,1000);
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1000);
            main.loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(e:UncaughtErrorEvent):void {finish(String(e.error));});
            log("START "+target);
        }
        private static function log(text:String):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("ObjectProbe.log"),FileMode.APPEND);
            fs.writeUTFBytes(getTimer()+" "+text+"\n");fs.close();
        }
        private static function write(name:String,value:*):void {
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);
            fs.writeUTFBytes(JSON.stringify(value,null,2));fs.close();
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {report.checks.push({name:name,ok:ok,detail:detail});log((ok?"PASS ":"FAIL ")+name);}
        private static function screenshot(name:String):void {
            var b:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);
            b.draw(main.stage);
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);
            fs.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));fs.close();b.dispose();
        }
        private static function before(e:Event):void {if(!done && interactions)interactions.beforeFrame();}
        private static function tick(e:Event):void {
            if(done)return;
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()>nextHeartbeat){nextHeartbeat=getTimer()+10000;log("heartbeat phase="+phase);}
                if(getTimer()-started>210000)throw new Error("Timeout phase="+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && main.getChildByName("ContinuousSceneCarrier") && main.getChildByName("ContinuousSceneCarrier")["sceneAPI"].ready) {
                    var carrier:*=main.getChildByName("ContinuousSceneCarrier");
                    report.sceneVersion=carrier["sceneAPI"].version;
                    var settingsCarrier:*=main.getChildByName("ModSettingsCarrier");
                    if(!settingsCarrier || !settingsCarrier["modAPI"])return;
                    var settings:*=settingsCarrier["modAPI"],enabled:Boolean=false;
                    for each(var page:Object in settings.getPages())if(page.modId=="continuousscene")
                        for each(var item:Object in page.items)if(item.key=="nativeEnabled"){item["set"](true);enabled=item["get"]()===true;}
                    if(!enabled)return; // Settings pages register after asynchronous module loading.
                    api=carrier["nativeAPI"];originalPrepare=api.prepare;
                    api.prepare=function(land:*):Object {
                        if(land.act.id!=target)return originalPrepare(land);
                        var snapshot:Object=SceneObjectChecks.capture(land);
                        var merged:Object=originalPrepare(land);
                        report.merge=SceneObjectChecks.compare(snapshot,merged);
                        write("merge.json",report.merge);log("MERGE captured");return merged;
                    };
                    w.grafon.scenePreload=false;w.mm.active=false;w.newGame(-1,"Object Audit",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<20)return;
                    w.ctr.clearAll();w.pers.healAll();w.game.beginMission(target);phase=2;ready=0;
                } else if(phase==2 && w.land && w.land.act.id==target && w.game.curLandId==target && w.t_exit==0 && w.allStat==1 && ++ready>=16) {
                    var state:Object=api.state(w.land);
                    check("actual-native-generation",w.land.rnd && state && state.loc===w.loc && state.regions.length>1);
                    check("pre-post-merge-captured",report.merge!=null);
                    report.entry=entryAudit();write("entry.json",report.entry);screenshot("entry");
                    interactions=new GeneratedInteractions(w);phase=3;ready=0;
                } else if(phase==3) {
                    interactions.afterFrame();
                    if(interactions.done){report.interactions=interactions.result;interactions=null;screenshot("interaction-end");finish();}
                }
            } catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
        private static function entryAudit():Object {
            var result:Object={classes:{},boxCount:0,boxVisualMismatch:0,shadowMismatch:0,bonusCount:0,bonusVisualMismatch:0,turretCount:0,turretVisualMismatch:0,detached:0,samples:[]};
            var Box:Class=getDefinitionByName("fe.loc.Box") as Class,Bonus:Class=getDefinitionByName("fe.loc.Bonus") as Class;
            var n:int=0;
            for(var obj:*=w.loc.firstObj;obj;obj=obj.nobj) {
                if(++n>20000)throw new Error("Object-chain cycle");
                var name:String=getQualifiedClassName(obj);result.classes[name]=int(result.classes[name])+1;
                var kind:String=obj is Box?"box":obj is Bonus?"bonus":name=="fe.unit::UnitTurret"?"turret":"";
                if(!kind)continue;
                if(("dead" in obj && obj.dead) || ("invis" in obj && obj.invis) || (obj is Bonus && obj.sost!=1))continue;
                result[kind+"Count"]++;
                var mismatch:Boolean=!obj.vis || Math.abs(obj.vis.x-obj.X)>0.01 || Math.abs(obj.vis.y-obj.Y)>0.01;
                if(mismatch)result[kind+"VisualMismatch"]++;
                if(!obj.vis || !obj.vis.stage)result.detached++;
                if(obj is Box && obj.shad && (Math.abs(obj.shad.x-obj.X)>0.01 || Math.abs(obj.shad.y-obj.Y-(obj.wall?2:6))>0.01))result.shadowMismatch++;
                if(mismatch && result.samples.length<18)result.samples.push({kind:kind,id:obj.id,x:obj.X,y:obj.Y,visX:obj.vis?obj.vis.x:null,visY:obj.vis?obj.vis.y:null});
            }
            return result;
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;
            if(api && originalPrepare!=null)api.prepare=originalPrepare;
            report.error=error;report.elapsedMs=getTimer()-started;
            report.ok=error==null;
            for each(var c:Object in report.checks)if(!c.ok)report.ok=false;
            if(report.entry && (report.entry.boxVisualMismatch || report.entry.bonusVisualMismatch || report.entry.turretVisualMismatch || report.entry.shadowMismatch || report.entry.detached))report.ok=false;
            if(report.interactions && !report.interactions.ok)report.ok=false;
            if(report.merge && !report.merge.ok)report.ok=false;
            // Initial unit sprites may settle on their first native step; entryAudit checks actual turret coordinates after activation.
            write("result.json",report);log("RESULT "+report.ok+" "+error);
            NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
    }
}
