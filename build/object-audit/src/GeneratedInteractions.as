package {
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    /** Uses objects born by the actual mission. No object creation, direct act or take. */
    public class GeneratedInteractions {
        public var done:Boolean=false;
        public var result:Object={ok:false,checks:[],frames:[],policy:"generated remote objects; explicit target; native E and collision pickup"};
        private var w:*,box:*,bonus:*,pose:Object,phase:int=0,age:int=0;
        public function GeneratedInteractions(world:*) {
            w=world;
            try {
                var Box:Class=getDefinitionByName("fe.loc.Box") as Class;
                for each(var obj:* in w.loc.objs){
                    if(!(obj is Box) || obj.dead || obj.invis || (obj.X<1920 && obj.Y<1000) || !obj.inter)continue;
                    var i:*=obj.inter;
                    if(!i.active || i.open || i.action!=1 || i.cont==null || i.cont=="empty" || i.lock>0 || i.mine>0 || i.needSkill || i.allact || i.cons || i.prob || i.t_action>20 || obj.door>0 || i.scrAct || i.scrOpen || i.scrClose || i.scrTouch || i.actFun)continue;
                    var p:Object=findPose(obj);if(p){box=obj;pose=p;break;}
                }
                check("generated-remote-container-coverage",box!=null);
                if(box){result.container={id:box.id,x:box.X,y:box.Y,visX:box.vis?box.vis.x:null,visY:box.vis?box.vis.y:null,pose:pose,display:display(box),contentBefore:box.inter.cont,knop:box.inter.knop};check("container-image-at-interaction-position",aligned(box));}
                for each(obj in w.loc.bonuses)if(obj.sost==1 && (obj.X>=1920 || obj.Y>=1000)){bonus=obj;break;}
                check("generated-remote-bonus-coverage",bonus!=null);
                if(bonus){result.bonus={id:bonus.id,x:bonus.X,y:bonus.Y,visX:bonus.vis?bonus.vis.x:null,visY:bonus.vis?bonus.vis.y:null};check("bonus-image-at-pickup-position",aligned(bonus));}
                var turrets:int=0,bad:int=0;
                var Turret:Class=getDefinitionByName("fe.unit.UnitTurret") as Class;
                for each(obj in w.loc.units)if(obj is Turret && obj.sost<3){turrets++;if(!aligned(obj))bad++;}
                result.turrets={count:turrets,covered:turrets>0,misplacedOrDetached:bad};if(turrets>0)check("native-turret-position-and-display",bad==0);
                if(!box)phase=1;
            }catch(e:Error){fail(e);}
        }
        private function check(name:String,ok:Boolean,detail:*=null):void {result.checks.push({name:name,ok:ok,detail:detail});}
        private function aligned(obj:*):Boolean {return obj.vis && obj.vis.stage && Math.abs(obj.vis.x-obj.X)<0.01 && Math.abs(obj.vis.y-obj.Y)<0.01;}
        private function display(obj:*):Object {return obj.vis?{visible:obj.vis.visible,alpha:obj.vis.alpha,onStage:obj.vis.stage!=null,mask:obj.vis.mask!=null}:null;}
        private function findPose(b:*):Object {
            for each(var dy:Number in [0,-20,20,-40,40,-80,80])for each(var dx:Number in [-65,65,-100,100,-40,40,0]){
                var x:Number=b.X+dx,y:Number=b.Y+dy;
                if(dx*dx+dy*dy>w.actionDist || x<w.gg.scX || y<w.gg.scY || x>=w.loc.limX-w.gg.scX || y>=w.loc.limY)continue;
                if(w.loc.collisionUnit(x,y,w.gg.scX,w.gg.scY))continue;
                if(w.loc.isLine(x,y-w.gg.scY*.75,b.X,b.Y-b.scY/2,b))return {x:x,y:y};
            }return null;
        }
        private function place(x:Number,y:Number):void {
            var p:*=w.gg;p.X=x;p.Y=y;p.X1=x-p.scX/2;p.X2=x+p.scX/2;p.Y1=y-p.scY;p.Y2=y;
            p.dx=p.dy=p.osndx=p.osndy=0;p.isTake=0;
        }
        public function beforeFrame():void {
            if(done)return;
            try {
                w.ctr.clearAll();w.gg.ctr.clearAll();w.ctr.keyAction=false;w.gg.ctr.keyAction=false;w.godMode=true;w.gg.invulner=true;
                if(phase==0 && box){
                    place(pose.x,pose.y);
                    w.celX=box.X;w.celY=box.Y-box.scY/2;
                    w.cam.celX=w.celX*w.cam.scaleV+w.cam.vx;w.cam.celY=w.celY*w.cam.scaleV+w.cam.vy;
                    box.onCursor=box.prior;w.loc.celObj=box;w.loc.celDist=(w.gg.X-box.X)*(w.gg.X-box.X)+(w.gg.Y-box.Y)*(w.gg.Y-box.Y);
                    w.ctr.keyAction=age>=5 && age<35;
                    w.gg.ctr.keyAction=age>=5 && age<35;
                }else if(phase==1 && bonus){place(bonus.X,bonus.Y+w.gg.scY/2);}
            }catch(e:Error){fail(e);}
        }
        public function afterFrame():void {
            if(done)return;
            try {
                age++;
                if(phase==0 && [1,5,6,7,10,20,39].indexOf(age)>=0)result.frames.push({age:age,open:box.inter.open,isAct:box.inter.is_act,selected:w.loc.celObj===box,onCursor:box.onCursor,control:w.gg.ggControl,disabled:w.gg.disabled,trigDis:w.gg.trigDis,emerg:w.gg.t_emerg,action:w.gg.actionObj!=null,tAction:w.gg.t_action,key:w.ctr.keyAction,playerKey:w.gg.ctr.keyAction,sameController:w.gg.ctr===w.ctr,work:w.gg.work,rat:w.gg.rat,teleObj:w.gg.teleObj!=null,distance:w.loc.celDist,range:w.actionDist,allStat:w.allStat,pause:w.onPause,x:w.gg.X,y:w.gg.Y,ray:w.loc.isLine(w.gg.X,w.gg.Y-w.gg.scY*.75,box.X,box.Y-box.scY/2,box)});
                if(phase==0 && (box.inter.cont=="empty" || age>=40)){
                    check("native-E-loots-generated-container",box.inter.cont=="empty",{frames:age,open:box.inter.open,contentBefore:result.container.contentBefore,contentAfter:box.inter.cont,selected:w.loc.celObj===box});
                    phase=1;age=0;
                }else if(phase==1 && age>=5){
                    if(bonus)check("native-collision-picks-generated-bonus",bonus.sost==2,{sost:bonus.sost});
                    w.ctr.clearAll();done=true;result.ok=true;
                    for each(var c:Object in result.checks)if(!c.ok)result.ok=false;
                }
            }catch(e:Error){fail(e);}
        }
        private function fail(e:Error):void {result.error=e.message;result.ok=false;done=true;}
    }
}
