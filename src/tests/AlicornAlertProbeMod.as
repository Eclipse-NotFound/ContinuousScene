package {
    import flash.desktop.NativeApplication;
    import flash.display.*;
    import flash.events.Event;
    import flash.filesystem.*;
    import flash.media.SoundMixer;
    import flash.media.SoundTransform;
    import flash.utils.*;
    import fe.unit.AlicornAlertAccess;

    public class AlicornAlertProbeMod {
        private static var main:*,w:*,api:*,scene:*,setting:Object,mode:Object;
        private static var phase:int=0,frames:int=0,start:int,done:Boolean=false;
        private static var units:Array=[],report:Object={checks:[],errors:[]};
        private static var persistence:Boolean=false;
        public static function init(host:*):void {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-cs-alicorn-")!=0)return;
            main=host;start=getTimer();SoundMixer.soundTransform=new SoundTransform(0);
            persistence=File.applicationDirectory.resolvePath("persistence-only.txt").exists;
            main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1100);
        }
        private static function check(name:String,ok:Boolean,detail:*=null):void {
            report.checks.push({name:name,ok:ok,detail:detail});
            if(!ok)throw new Error(name+": "+JSON.stringify(detail));
        }
        private static function arrived(id:String):Boolean {return w.land&&w.land.act.id==id&&w.game.curLandId==id&&w.ng_wait==0&&w.t_exit==0&&w.allStat==1;}
        private static function tick(e:Event):void {
            if(done)return;
            try {
                SoundMixer.soundTransform=new SoundTransform(0);frames++;
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-start>150000)throw new Error("timeout phase "+phase);
                if(w&&w.verror&&w.verror.visible)throw new Error(w.verror.txt.text);
                if(phase==0&&w&&w.mm&&w.mm.loaded&&w.allLandsLoaded&&w.textLoaded) {
                    var c:*=main.getChildByName("ContinuousSceneCarrier"),s:*=main.getChildByName("ModSettingsCarrier");
                    if(!c||!c.sceneAPI.ready||!s||!s.modAPI)return;
                    api=c.nativeAPI;scene=c.sceneAPI;
                    for each(var p:Object in s.modAPI.getPages())if(p.modId=="continuousscene")for each(var f:Object in p.items) {
                        if(f.key=="alicornRelayPercent")setting=f;if(f.key=="nativeEnabled")mode=f;
                    }
                    if(!setting||!mode)return;
                    check("loaded-version",scene.version=="0.9.1",scene.version);
                    check("slider-contract",setting.kind=="slider"&&setting.min==0&&setting.max==100&&setting.step==1&&setting.suffix=="%");
                    if(persistence) {check("preference-reloaded",setting["get"]()==37&&mode["get"]()===true);finish();return;}
                    check("legacy-preference-default",setting["get"]()==0&&mode["get"]()===true);
                    setting["set"](150);check("clamp-upper",setting["get"]()==100);
                    setting["set"](-5);check("clamp-lower",setting["get"]()==0);
                    setting["set"](NaN);check("invalid-number",setting["get"]()==0);
                    mode["set"](false);w.mm.active=false;w.newGame(-1,"Alicorn verification",{propusk:true});phase=1;frames=0;
                } else if(phase==1&&w.gg&&w.loc&&w.ng_wait==0&&w.allStat==1) {
                    w.godMode=true;w.gg.invulner=true;
                    if(!w.gg.ggControl||w.pip.noAct){frames=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(frames<10)return;
                    w.ctr.clearAll();w.pers.healAll();scene.travel();phase=2;frames=0;
                } else if(phase==2&&arrived("continuous_scene")&&frames>10) {
                    check("real-large-map",w.grafon.sceneLarge&&w.loc.spaceX==192&&w.loc.spaceY==50);
                    runChecks();
                    setting["set"](37);mode["set"](true);
                    var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("ContinuousScene.preferences.json"),FileMode.READ);
                    var prefs:Object=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));fs.close();
                    check("both-preferences-preserved",prefs.nativeEnabled===true&&prefs.alicornRelayPercent==37);
                    check("muted",SoundMixer.soundTransform.volume==0);
                    finish();
                }
            } catch(error:Error) {report.errors.push(error.message+" "+error.getStackTrace());finish();}
        }
        private static function spok(i:int):int {return AlicornAlertAccess.state(units[i]).spok;}
        private static function reset(chance:int):void {
            setting["set"](chance);
            for(var i:int=0;i<units.length;i++) {
                AlicornAlertAccess.calm(units[i]);units[i].setPos(300+750*i,700);
                units[i].fraction=2;units[i].unres=false;units[i].sost=1;
            }
        }
        private static function runChecks():void {
            w.enemyAct=1; // Native decisions run; perception/attacks cannot contaminate these directed assertions.
            var C:Class=getDefinitionByName("fe.unit.UnitAlicorn") as Class;
            for(var i:int=0;i<6;i++) {
                var u:*=new C("2",20);u.putLoc(w.loc,300+750*i,700);units.push(u);
                if(w.loc.units.indexOf(u)<0)w.loc.units.push(u);
            }
            reset(0);check("native-internal-access",spok(0)==0);
            units[0].budilo();check("zero-first-hop",spok(1)>0&&spok(2)==0);
            for(i=0;i<50;i++){AlicornAlertAccess.decide(units[1]);units[1].setCel(w.gg);units[1].telepat();}
            check("zero-no-native-decision-or-telepath-relay",spok(2)==0&&units[2].celUnit==null);

            reset(100);units[0].budilo();
            for(i=1;i<5;i++)AlicornAlertAccess.decide(units[i]);
            check("hundred-native-five-hop-chain",spok(5)>0);
            for(i=0;i<6;i++)units[i].budilo();check("cycle-returns",spok(5)>0);

            reset(0);units[0].setCel(w.gg);units[0].telepat();
            check("telepath-first-hop",units[1].celUnit===w.gg&&units[2].celUnit==null);
            units[1].telepat();units[1].budilo();check("telepath-cannot-bypass-zero",units[2].celUnit==null&&spok(2)==0);
            reset(100);units[0].setCel(w.gg);
            for(i=0;i<5;i++)units[i].telepat();check("hundred-telepath-chain",units[5].celUnit===w.gg);

            reset(0);units[0].setPos(1800,700);units[1].setPos(2760,1200);units[2].setPos(2761,700);units[3].setPos(1800,1201);
            units[4].setPos(1900,700);units[4].fraction=3;units[5].setPos(1900,700);units[5].unres=true;
            units[0].budilo();check("inclusive-room-rectangle-crosses-old-boundary",spok(1)>0);
            check("outside-x-y-and-native-filters",spok(2)==0&&spok(3)==0&&spok(4)==0&&spok(5)==0);

            reset(0);units[0].budilo();setting["set"](100);units[1].budilo();check("setting-does-not-reroll-active-recipient",spok(2)==0);
            AlicornAlertAccess.calmDecision(units[1]);units[0].budilo();units[1].budilo();
            check("native-calm-allows-new-decision",spok(2)>0);
            reset(0);units[0].budilo();units[1].setNull(true);units[1].budilo();check("native-explicit-reset-clears-decision",spok(2)>0);

            reset(0);units[1].alarma();units[1].budilo();check("direct-hurt-alarm-is-origin",spok(2)>0);
            reset(0);units[1].alarma(300,700);units[1].budilo();check("native-incoming-alarm-is-recipient",spok(2)==0);
            reset(0);units[0].setPos(300,700);units[1].setPos(5000,700);units[1].budilo();
            units[1].setPos(600,700);units[0].budilo();units[1].setPos(1050,700);units[1].budilo();
            check("independent-source-keeps-qualification",spok(2)>0);

            reset(0);w.grafon.sceneLarge=false;
            units[0].budilo();check("ordinary-native-global-broadcast-preserved",spok(5)>0);
            for(i=1;i<6;i++)units[i].setCel(null);
            units[0].setCel(w.gg);units[0].telepat();check("ordinary-native-global-telepathy-preserved",units[5].celUnit===w.gg);
            w.grafon.sceneLarge=true;

            setting["set"](50);var allowed:int=0,stable:Boolean=true;
            for(i=0;i<256;i++) {
                var fake:Object={loc:w.loc};api.alicornReceive(fake);var decision:Boolean=api.alicornAllow(fake);
                if(decision)allowed++;
                for(var j:int=0;j<20;j++){api.alicornReceive(fake);if(api.alicornAllow(fake)!==decision)stable=false;}
            }
            check("intermediate-chance-sampled-once",stable&&allowed>70&&allowed<186,{accepted:allowed,total:256});
        }
        private static function finish():void {
            if(done)return;done=true;report.ok=report.errors.length==0;report.phase=phase;
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("alicorn-result.json"),FileMode.WRITE);fs.writeUTFBytes(JSON.stringify(report,null,2));fs.close();
            NativeApplication.nativeApplication.exit(report.ok?0:1);
        }
    }
}
