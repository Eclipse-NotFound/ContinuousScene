package {
    import flash.desktop.NativeApplication;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Native Unit.run trajectories on a temporary in-bounds arena. No AI or timing claim. */
    public class ContinuousSceneMotionMod {
        private static var main:*,w:*,phase:int=0,ready:int=0,started:int,done:Boolean=false;
        private static var report:Object={ok:false,assertions:[],cases:[]};
        public static function init(host:*):void {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)return;
            main=host;started=getTimer();main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-500);
        }
        private static function check(name:String,ok:Boolean):void {
            report.assertions.push({name:name,ok:ok});if(!ok)throw new Error("Check failed: "+name);
        }
        private static function settings():Boolean {
            var c:*=main.getChildByName("ModSettingsCarrier");if(!c || !c["modAPI"])return false;
            for each(var page:Object in c["modAPI"].getPages())if(page.modId=="continuousscene")
                for each(var item:Object in page.items)if(item.key=="nativeEnabled"){item["set"](false);return true;}
            return false;
        }
        private static function snapshot(u:*):Object {
            return {x:u.X,y:u.Y,x1:u.X1,x2:u.X2,y1:u.Y1,y2:u.Y2,dx:u.dx,dy:u.dy,
                stay:u.stay,stayPhis:u.stayPhis,stayMat:u.stayMat,shX1:u.shX1,shX2:u.shX2,
                turnX:u.turnX,turnY:u.turnY,scX:u.scX,scY:u.scY,isSit:u.isSit,isLaz:u.isLaz};
        }
        private static function trajectories():void {
            var loc:*=w.loc,save:Array=[],names:Array=["phis","mat","shelf","zForm","diagon","stair","water","fake","door","trap"];
            var col:int,row:int,tile:*,key:String;
            try {
                for(col=18;col<=29;col++)for(row=4;row<=13;row++) {
                    tile=loc.space[col][row];var prior:Object={tile:tile,values:{}};
                    for each(key in names)prior.values[key]=tile[key];save.push(prior);
                    tile.phis=(col==19 || col==28 || row==5 || row==12)?1:0;
                    tile.mat=1;tile.shelf=false;tile.zForm=tile.diagon=tile.stair=tile.water=0;
                    tile.fake=false;tile.door=null;tile.trap=null;
                }
                var specs:Array=[
                    {name:"fall-right",x:960,y:400,dx:3,dy:4},
                    {name:"fall-left",x:960,y:400,dx:-3,dy:4},
                    {name:"land",x:960,y:478,dx:0,dy:4},
                    {name:"land-moving",x:960,y:478,dx:3,dy:4},
                    {name:"ceiling",x:960,y:282,dx:0,dy:-4},
                    {name:"ceiling-moving",x:960,y:282,dx:-3,dy:-4},
                    {name:"right-wall",x:1091,y:400,dx:4,dy:1},
                    {name:"left-wall",x:829,y:400,dx:-4,dy:1},
                    {name:"fly-land",x:960,y:478,dx:2,dy:4,fly:true},
                    {name:"fly-fall",x:960,y:400,dx:2,dy:4,fly:true},
                    {name:"half-step-land",x:960,y:478,dx:2,dy:4,divisor:2},
                    {name:"half-step-ceiling",x:960,y:282,dx:2,dy:-4,divisor:2}
                ];
                for each(var spec:Object in specs) {
                    var u:*,entry:Object={name:spec.name,frames:[]};
                    try {
                        u=getDefinitionByName("fe.unit.Unit")["create"]("molerat",1);
                        u.putLoc(loc,spec.x,spec.y);u.dx=spec.dx;u.dy=spec.dy;
                        u.osndx=u.osndy=0;u.stay=false;u.isLaz=0;u.throu=false;u.mater=true;
                        u.isFly=Boolean(spec.fly);u.levit=false;u.isPlav=false;u.t_throw=0;u.destroy=0;u.massa=0;
                        entry.before=snapshot(u);
                        for(var i:int=0;i<12;i++) {
                            u.run(spec.divisor?spec.divisor:1);entry.frames.push(snapshot(u));
                            check(spec.name+"-finite-inside-"+i,isFinite(u.X) && isFinite(u.Y) && u.X1>=0 && u.X2<loc.limX);
                        }
                        if(spec.name=="land" || spec.name=="land-moving" || spec.name=="half-step-land")
                            check(spec.name+"-floor-collision",u.Y==480 && u.stay && u.dy==0);
                        if(spec.name=="ceiling" || spec.name=="ceiling-moving" || spec.name=="half-step-ceiling")
                            check(spec.name+"-ceiling-collision",u.Y1==240 && u.dy==0);
                        if(spec.name=="right-wall")check(spec.name+"-blocked",u.X2==1120 && u.dx==0);
                        if(spec.name=="left-wall")check(spec.name+"-blocked",u.X1==800 && u.dx==0);
                        if(spec.name=="fly-land")check(spec.name+"-floor-collision",u.Y==480 && u.dy==0);
                        report.cases.push(entry);
                    } finally {if(u)u.remVisual();}
                }
            } finally {for each(var saved:Object in save)for each(key in names)saved.tile[key]=saved.values[key];}
        }
        private static function finish(error:String=null):void {
            if(done)return;done=true;main.stage.removeEventListener(Event.ENTER_FRAME,tick);
            report.ok=error==null;report.error=error;report.elapsedMs=getTimer()-started;
            var fs:FileStream=new FileStream();fs.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            fs.writeUTFBytes(JSON.stringify(report,null,2));fs.close();NativeApplication.nativeApplication.exit(error?1:0);
        }
        private static function tick(e:Event):void {
            try {
                w=getDefinitionByName("fe.World")["w"];
                if(getTimer()-started>120000)throw new Error("Timed out in phase "+phase);
                if(w && w.verror && w.verror.visible)throw new Error(w.verror.txt.text);
                if(w && w.gg){w.godMode=true;w.gg.invulner=true;}
                if(phase==0 && w && w.mm && w.mm.loaded && w.allLandsLoaded && w.textLoaded && settings()) {
                    w.mm.active=false;w.newGame(-1,"Collision regression",{propusk:true});phase=1;
                } else if(phase==1 && w.ng_wait==0 && w.allStat==1 && w.gg && w.loc && w.t_exit==0) {
                    if(!w.gg.ggControl || w.pip.noAct){ready=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
                    if(++ready<30)return;w.ctr.clearAll();trajectories();finish();
                }
            }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}
        }
    }
}
