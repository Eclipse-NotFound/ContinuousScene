package {
    import flash.utils.getDefinitionByName;
    /** Destructive fixtures are confined to the isolated test game. */
    public class ContinuousSceneMechanicsChecks {
        private static var fixture:*,baseX:Number,baseY:Number,deltaX:Number;
        private static var migration:Object;
        public static function prepare(main:*):void {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var original:Function=api.prepare;
            api.prepare=function(land:*):Object {
                if(land.act.tip!="base" && fixture==null) {
                    var Box:Class=getDefinitionByName("fe.loc.Box") as Class;
                    outer:for(var x:int=land.minLocX;x<land.maxLocX;++x)for(var y:int=land.minLocY;y<land.maxLocY;++y) {
                        var loc:*=land.locs[x][y][0];
                        if(!loc || (x==land.minLocX && y==land.minLocY) || loc.objs.length==0)continue;
                        fixture=new Box(loc,loc.objs[0].id,400,400,<o inter="1"><move dx="3" dy="-1" tstay="10" tmove="20"/></o>);
                        loc.objs.push(fixture);loc.addObj(fixture);
                        baseX=400+(x-land.minLocX)*1920;baseY=400+(y-land.minLocY)*1000;
                        deltaX=loc.mirror?-120:120;
                        break outer;
                    }
                }
                var result:Object=original(land);
                if(fixture && migration==null)migration={x:fixture.X,y:fixture.Y,moving:fixture.inter && fixture.inter.isMove};
                return result;
            };
        }
        public static function run(main:*,w:*,check:Function):Object {
            var api:*=main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var state:Object=api.state(w.land),groups:Array=[];
            for each(var region:Object in state.regions) {
                var bonuses:Array=[];
                for each(var b:* in region.chain)if("id" in b && b.id=="xp" && "take" in b && b.sost==1)bonuses.push(b);
                if(bonuses.length>=2)groups.push({r:region.reward,bonuses:bonuses});
            }
            check("reward-regions-available",groups.length>=2,groups.length);
            if(groups.length<2)throw new Error("Missing native reward coverage");
            var first:Object=groups[0],other:Object=groups[1],a:Object=first.r,z:Object=other.r;
            a.kolXp=2;a.maxXp=2;a.unXp=5;a.summXp=17;a.detecting=false;
            z.summXp=31;z.detecting=false;
            var otherCount:int=z.kolXp,before:int=w.land.summXp;
            first.bonuses[0].take();
            check("first-pickup-keeps-other-room-count",a.kolXp==1 && z.kolXp==otherCount && a.summXp==17);
            first.bonuses[1].take();
            check("room-completion-awards-only-own-stealth-pool",a.kolXp==0 && a.summXp==0 && z.summXp==31 && w.land.summXp-before==17);
            var enemy:*=null;
            for each(var u:* in w.loc.units)if(u && !u.player && u.xp>0 && u.sost==1 && api.reward(u)===z){enemy=u;break;}
            check("native-enemy-reward-coverage",enemy!=null);
            if(enemy) {
                enemy.setCel(w.gg);
                check("enemy-detection-belongs-to-original-room",z.detecting && !a.detecting);
                // Moving across a former boundary must not transfer its pool.
                enemy.X=w.gg.X;enemy.Y=w.gg.Y;enemy.xp=7;enemy.isRes=false;enemy.lootIsDrop=false;
                before=w.land.summXp;enemy.die();
                check("cross-room-kill-uses-original-pool",z.summXp==24 && a.summXp==0 && w.land.summXp-before==7 && enemy.xp==0);
            }
            check("moving-fixture-migrated",migration && migration.moving && Math.abs(migration.x-baseX)<0.01 && Math.abs(migration.y-baseY)<0.01,migration);
            if(fixture) {
                fixture.inter.moveTo(1);
                for(var i:int=0;i<25;++i)fixture.inter.move();
                check("moving-path-forward-world-coordinates",Math.abs(fixture.inter.X-(baseX+deltaX))<0.01 && Math.abs(fixture.inter.Y-(baseY-40))<0.01,{x:fixture.inter.X,y:fixture.inter.Y,expectedX:baseX+deltaX,expectedY:baseY-40});
                fixture.inter.moveTo(2);
                for(i=0;i<25;++i)fixture.inter.move();
                check("moving-path-return-does-not-double-shift",Math.abs(fixture.inter.X-baseX)<0.01 && Math.abs(fixture.inter.Y-baseY)<0.01);
            }
            return {regions:groups.length,movingFixture:fixture!=null};
        }
    }
}
