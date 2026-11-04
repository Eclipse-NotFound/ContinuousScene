package {
    import flash.utils.getDefinitionByName;
    import flash.utils.Dictionary;
    public class ActivityFixture {
        public static var world:Object,currentLoc:Object;
        private static var caseResult:Array;
        private static const FIELDS:Array=["X","Y","scX","scY","hp","maxhp","celUnit","cut","poison","player","npc","boss","fraction","sost","stun","bind","levit","t_emerg","onCursor"];
        public static function state(land:*):Object {return {loc:currentLoc};}
        public static function host():Object {return world;}
        private static function record(r:Object,u:*):Object {return r?{hp:r.hp,engaged:r.engaged,leashed:r.leashed,deadline:r.deadline,until:r.until}:{hp:u.hp,engaged:false,leashed:false,deadline:0,until:0};}
        public static function capture(loc:*,w:*,s:Object):Object {
            var f:Object={tick:s.tick-1,budget:NativeSceneActivity.wakeBudget,duration:NativeSceneActivity.disengageTicks,
                cam:{scaleV:w.cam.scaleV,vx:w.cam.vx,vy:w.cam.vy,screenX:w.cam.screenX,screenY:w.cam.screenY},pause:w.grafon.scenePauseDistant,gg:-1,units:[],records:[],sleeping:[],objects:[]};
            var cls:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
            for(var p:*=loc.firstObj;p;p=p.nobj)f.objects.push(p is cls?{bullet:true,off:p.off,X:p.X,Y:p.Y,dx:p.dx,dy:p.dy,explRadius:p.explRadius}:{bullet:false});
            for each(var u:* in loc.units) {
                if(!u){f.units.push(null);f.records.push(null);f.sleeping.push(false);continue;}
                if(u===loc.gg)f.gg=f.units.length;
                var x:Object={};for each(var key:String in FIELDS)x[key]=u[key];
                x.celUnit=u.celUnit!=null?{}:null;x.bind=u.bind!=null?{}:null;
                x.effects=u.effects?new Array(u.effects.length):[];x.inter=u.inter?{isMove:u.inter.isMove}:null;
                f.units.push(x);f.records.push(record(s.records[u],u));f.sleeping.push(Boolean(s.sleeping[u]));
            }
            if(f.gg<0){f.gg=f.units.length;f.units.push({X:loc.gg.X,Y:loc.gg.Y,fraction:loc.gg.fraction,hp:loc.gg.hp,maxhp:loc.gg.maxhp,player:true,effects:[]});f.records.push(null);f.sleeping.push(false);f.externalGG=true;}
            return f;
        }
        public static function project(loc:*,s:Object):Object {
            var rows:Array=[];
            for each(var u:* in loc.units)rows.push(u?{r:record(s.records[u],u),sleeping:Boolean(s.sleeping[u]),onCursor:u.onCursor}:null);
            return {awake:s.awake,asleep:s.asleep,leashed:s.leashed,units:rows};
        }
        private static function clone(f:Object,klass:Class):Object {
            var loc:Object={land:{},units:[],firstObj:null},rs:Array=[],sleep:Array=f.sleeping.concat(),prior:Object;
            for each(var o:Object in f.objects) {
                var p:Object={};for(var k:String in o)p[k]=o[k];p.nobj=null;
                if(prior)prior.nobj=p;else loc.firstObj=p;prior=p;
            }
            for(var i:int=0;i<f.units.length;++i) {
                o=f.units[i];if(!o){loc.units.push(null);rs.push(null);continue;}
                var u:Object={};for(k in o)u[k]=o[k];u.vis=null;u.setVisPos=function():void{};
                loc.units.push(u);rs.push(f.records[i]);
            }
            loc.gg=loc.units[f.gg];if(f.externalGG){loc.units.pop();rs.pop();sleep.pop();}
            currentLoc=loc;world={cam:f.cam,grafon:{scenePauseDistant:f.pause}};
            klass["wakeBudget"]=f.budget;klass["disengageTicks"]=f.duration;
            klass["proofSeed"](loc,f.tick,rs,sleep);klass["update"](loc);
            return {state:project(loc,klass["proofState"](loc)),trace:klass["proofTrace"]};
        }
        public static function compare(f:Object):Object {
            var a:Object=clone(f,DryActivityA),b:Object=clone(f,DryActivityB);
            return {equal:JSON.stringify(a)==JSON.stringify(b),a:a,b:b};
        }
        private static function unit(x:Number,y:Number):Object {return {X:x,Y:y,scX:20,scY:50,hp:100,maxhp:100,celUnit:null,cut:0,poison:0,player:false,npc:false,boss:false,fraction:2,sost:1,stun:0,bind:null,levit:false,t_emerg:0,onCursor:7,effects:[],inter:null};}
        public static function cases():Array {
            if(caseResult)return caseResult;caseResult=[];
            var names:Array=["empty-units","no-query","empty-table-multi-query","danger","first-halo-match","expiry-clear","inside-leash","damage-renews","visible-reactivates","sleep-resume","deferred-budget","cross-frame-appear-move-disappear"];
            for(var c:int=0;c<names.length;++c){
                var gg:Object=unit(0,0);gg.fraction=1;gg.player=true;
                var f:Object={tick:149,budget:1,duration:150,cam:{scaleV:1,vx:0,vy:0,screenX:1280,screenY:720},pause:true,gg:0,units:[gg,unit(6000,3000),unit(6100,3000)],records:[null,null,null],sleeping:[false,false,false],objects:[]};
                var r:Object={hp:100,engaged:true,leashed:false,deadline:150,until:194};
                if(c==0){f.externalGG=true;f.units=[gg];}
                if(c==1){f.units[1].X=100;f.units[1].Y=0;f.units[2].X=200;f.units[2].Y=0;}
                if(c==3||c==4||c==9)f.objects=[{bullet:true,off:false,X:6000,Y:3000,dx:0,dy:0,explRadius:0}];
                if(c==4)f.objects.unshift({bullet:true,off:false,X:6300,Y:3000,dx:0,dy:0,explRadius:0});
                if(c>=5&&c<=8)f.records[1]=r;
                if(c==6){f.units[1].X=2000;f.units[1].Y=0;}
                if(c==7)f.units[1].hp=90;
                if(c==8){f.cam.vx=-6000;f.cam.vy=-3000;}
                if(c==9)f.sleeping[1]=true;
                if(c==10){f.units[1].X=100;f.units[1].Y=0;f.units[2].X=200;f.units[2].Y=0;f.sleeping=[false,true,true];}
                var result:Object=compare(f),semantic:Boolean=true;
                if(c==5)semantic=result.a.state.units[1].r.until==0 && result.a.state.units[1].sleeping;
                if(c==7)semantic=result.a.state.units[1].r.deadline==300;
                if(c==0)semantic=result.a.state.units.length==0;
                if(c==2)semantic=result.a.state.asleep==2;
                if(c==3)semantic=result.a.trace[1][3]===true;
                if(c==4)semantic=result.a.trace[1][3]===false&&result.a.trace[1][4]===true;
                if(c==6)semantic=result.a.state.units[1].r.engaged&&!result.a.state.units[1].r.leashed;
                if(c==8)semantic=result.a.state.units[1].r.until==195&&!result.a.state.units[1].sleeping;
                if(c==9)semantic=!result.a.state.units[1].sleeping;
                if(c==10)semantic=!result.a.state.units[1].sleeping&&result.a.state.units[2].sleeping;
                if(c==11){
                    var flags:Array=[];
                    for(var j:int=0;j<3;++j){
                        f.tick+=1;f.objects=j==2?[]:[{bullet:true,off:false,X:6000+j*700,Y:3000,dx:0,dy:0,explRadius:0}];
                        var step:Object=compare(f);semantic=semantic&&step.equal;flags.push(step.a.trace[1][3]);
                        for(var n:int=0;n<f.units.length;++n){f.records[n]=step.a.state.units[n].r;f.sleeping[n]=step.a.state.units[n].sleeping;}
                    }
                    semantic=semantic&&flags[0]===true&&flags[1]===false&&flags[2]===false;
                }
                caseResult.push({name:names[c],ok:result.equal&&semantic});
            }
            return caseResult;
        }
    }
}
