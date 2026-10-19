package {
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;

    /** Combines the actual, already generated native main floor. Back rooms
     * and trials keep their native door transitions and return coordinates. */
    public class NativeSceneAdapter {
        private static var states:Dictionary=new Dictionary(true);
        private static var world:*;
        private static var boxClass:Class;
        private static var objectClass:Class;
        private static var unitClass:Class;
        private static var interOffsets:Dictionary=new Dictionary(true);
        private static var rewardOwners:Dictionary=new Dictionary(true);
        private static const ARRAYS:Array=["units","ups","objs","bonuses","areas","acts","saves","backobjs","enspawn","signposts","recalcTiles"];
        private static const ENV:Array=["black","sky","gas","rad","wrad","wdam","wtipdam","tipWater","opacWater","maxdy","levitOn","portOn","petOn","destroyOn","visMult","earMult","electroDam","backform","transpFon","homeStable"];
        public static function attach(w:*):void {
            world=w;
            if(!boxClass) {
                boxClass=getDefinitionByName("fe.loc.Box") as Class;
                objectClass=getDefinitionByName("fe.Obj") as Class;
                unitClass=getDefinitionByName("fe.unit.Unit") as Class;
            }
        }
        public static function prepare(land:*):Object {
            if(states[land]) return states[land];
            if(!ContinuousSceneMod.nativeEnabled || land.act.tip=="base" || land.act.id=="continuous_scene") return null;
            for(var old:* in states) if(old.act.id==land.act.id && old!==land) delete states[old];
            var regions:Array=[],x:int,y:int,key:String,source:*,entry:Object,field:String;
            for(x=land.minLocX;x<land.maxLocX;++x) for(y=land.minLocY;y<land.maxLocY;++y) {
                source=land.locs[x][y][0];
                if(!source) continue;
                if(source.spaceX!=48 || source.spaceY!=25) return null;
                entry={source:source,lx:x,ly:y,tx:(x-land.minLocX)*48,ty:(y-land.minLocY)*25,
                    spawn:source.spawnPoints.concat(),chain:[],arrays:{},environment:{},
                    backwall:source.backwall,color:source.color,darkness:source.darkness,
                    room:source.room?source.room.id:"",space:source.space,
                    reward:{kolXp:source.kolXp,maxXp:source.maxXp,unXp:source.unXp,
                        summXp:source.summXp,detecting:source.detecting}};
                for each(field in ARRAYS) entry.arrays[field]=source[field]?source[field].concat():[];
                for each(field in ENV) entry.environment[field]=source[field];
                for(var pt:*=source.firstObj;pt;pt=pt.nobj) entry.chain.push(pt);
                regions.push(entry);
            }
            if(regions.length<2) return null;
            var width:int=(land.maxLocX-land.minLocX)*48,height:int=(land.maxLocY-land.minLocY)*25;
            if(width>512 || height>256) throw new Error("ContinuousScene native map exceeds supported bounds");
            var dest:*=regions[0].source;
            var state:Object={land:land,loc:dest,regions:regions,byCell:{},width:width,height:height};
            var space:Array=[],Tile:Class=getDefinitionByName("fe.loc.Tile") as Class,tile:*;
            // Reuse every native tile. Allocate solid placeholders only for
            // genuinely missing room cells, not all 14,400 cells before
            // immediately replacing them with the generated factory tiles.
            for(x=0;x<width;++x) space[x]=new Array(height);
            for each(entry in regions) for(x=0;x<48;++x) for(y=0;y<25;++y)
                space[x+entry.tx][y+entry.ty]=entry.space[x][y];
            for(x=0;x<width;++x) for(y=0;y<height;++y) if(space[x][y]==null) {
                tile=new Tile(x,y);tile.mainFrame("A");space[x][y]=tile;
            }
            dest.space=space;dest.spaceX=width;dest.spaceY=height;dest.limX=width*40;dest.limY=height*40;
            dest.landX=land.minLocX;dest.landY=land.minLocY;dest.ramka=0;
            dest.firstObj=dest.nextObj=dest.lastObj=null;
            for each(field in ARRAYS) dest[field]=[];
            dest.units=[land.gg,land.gg.defpet];dest.spawnPoints=[];
            var moved:Dictionary=new Dictionary(true),seen:Dictionary,metadata:XML=<room><sceneRegions/></room>;
            for each(entry in regions) {
                var dx:int=entry.tx*40,dy:int=entry.ty*40;
                state.byCell[entry.lx+":"+entry.ly]=entry;
                for(x=0;x<48;++x) for(y=0;y<25;++y) {
                    tile=entry.space[x][y];tile.X+=entry.tx;tile.Y+=entry.ty;
                    tile.phX1+=dx;tile.phX2+=dx;tile.phY1+=dy;tile.phY2+=dy;
                    space[x+entry.tx][y+entry.ty]=tile;
                }
                for each(var spawn:Object in entry.spawn) {spawn.x+=entry.tx;spawn.y+=entry.ty;}
                for each(pt in entry.chain) {
                    rewardOwners[pt]=entry.reward;
                    moveObject(pt,dest,dx,dy,moved);
                    pt.in_chain=false;pt.pobj=pt.nobj=null;dest.addObj(pt);
                }
                for each(field in ARRAYS) {
                    for each(var value:* in entry.arrays[field]) {
                        if(value==null || value===land.gg || value===land.gg.defpet) continue;
                        rewardOwners[value]=entry.reward;
                        if(field=="signposts" || field=="enspawn") {value.x+=dx;value.y+=dy;}
                        else if(field!="recalcTiles") moveObject(value,dest,dx,dy,moved);
                        if(dest[field].indexOf(value)<0) dest[field].push(value);
                    }
                }
                land.locs[entry.lx][entry.ly][0]=dest;
                metadata.sceneRegions.appendChild(<region x={entry.tx} y={entry.ty} width="48" height="25"
                    backwall={entry.backwall} color={entry.color} dark={entry.darkness} nativeRegion="true"
                    backform={entry.environment.backform} transpFon={entry.environment.transpFon}
                    tipWater={entry.environment.tipWater} gas={entry.environment.gas} homeStable={entry.environment.homeStable}/>);
            }
            states[land]=state;
            world.grafon.sceneSetRegions(dest,metadata);
            world.grafon.sceneSetNativeEnvironment(dest,state);
            // A new native Land is a new generation. Never apply terrain from
            // a previous random mission merely because its map id is equal.
            world.grafon.sceneForgetLand(land);
            if(!land.rnd) {
                var revision:Array=[];for each(entry in regions) revision.push(entry.lx+":"+entry.ly+":"+entry.room);
                world.grafon.sceneTrack(dest,"native:"+revision.join("|"));
            }
            if(land.map) land.map.dispose();land.createMap();
            return state;
        }
        private static function moveObject(value:*,dest:*,dx:Number,dy:Number,moved:Dictionary):void {
            if(!value || moved[value]) return;
            moved[value]=true;
            if("loc" in value) value.loc=dest;
            for each(var field:String in ["X","X1","X2","begX","stX","weaponX","magicX","celX","acelX","eyeX"])
                if(field in value && isFinite(Number(value[field]))) value[field]+=dx;
            for each(field in ["Y","Y1","Y2","begY","stY","weaponY","magicY","celY","acelY","eyeY"])
                if(field in value && isFinite(Number(value[field]))) value[field]+=dy;
            if("portX" in value && value.portX>=0) value.portX+=dx/40;
            if("portY" in value && value.portY>=0) value.portY+=dy/40;
            if("inter" in value && value.inter) {
                value.inter.loc=dest;value.inter.X+=dx;value.inter.Y+=dy;
                if(value.inter.isMove && (dx!=0 || dy!=0))interOffsets[value.inter]={x:dx,y:dy};
                if(value.inter.area) moveObject(value.inter.area,dest,dx,dy,moved);
            }
            // Stationary native doors do not call runVis during their step.
            // Move their image and native shadow together with the collision.
            if(value is boxClass) value.runVis();
            else if(value is unitClass) value.setVisPos();
            else if(value is objectClass && value.vis) {value.vis.x+=dx;value.vis.y+=dy;}
            // Trap overlays are separate world-space sprites. BackObj is not
            // an Obj: its shared drawing templates must remain untranslated.
            if(value is objectClass && "vis2" in value && value.vis2) {value.vis2.x+=dx;value.vis2.y+=dy;}
            for each(field in ["currentWeapon","throwWeapon","magicWeapon","weapon"])
                if(field in value && value[field] && "loc" in value[field]) value[field].loc=dest;
            if("un" in value && value.un) moveObject(value.un,dest,dx,dy,moved);
            // Checkpoint trigger areas are owned by the checkpoint, not by
            // Location.areas. The dictionary also handles shared references.
            if("area" in value && value.area) moveObject(value.area,dest,dx,dy,moved);
        }
        public static function state(land:*):Object {return states[land];}
        public static function host():* {return world;}
        // Native room rewards remain independent even after all objects share
        // one collision world. An enemy keeps its original reward pool when
        // pursuing the player across a former room boundary.
        public static function reward(value:*):Object {return rewardOwners[value];}
        public static function detecting(value:*):Boolean {
            var r:Object=rewardOwners[value];if(!r)return false;
            r.detecting=true;return true;
        }
        public static function takeXP(value:*,amount:int,x:Number,y:Number):Boolean {
            var r:Object=rewardOwners[value];if(!r)return false;
            amount=Math.min(amount,r.summXp);r.summXp-=amount;
            value.loc.land.summXp+=amount;
            if(amount>0)world.pers.expa(amount,x,y);
            return true;
        }
        public static function moveOffset(inter:*):Object {
            var offset:Object=interOffsets[inter];delete interOffsets[inter];return offset;
        }
        public static function coordinates(land:*):void {
            var s:Object=states[land];
            if(!s || land.loc!==s.loc || land.prob!="") return;
            var lx:int=land.minLocX+int(Math.max(0,land.gg.X)/1920),ly:int=land.minLocY+int(Math.max(0,land.gg.Y)/1000);
            if(s.byCell[lx+":"+ly]) {land.locX=lx;land.locY=ly;land.locZ=0;}
        }
        public static function spawn(land:*):Boolean {
            var s:Object=states[land];
            if(!s || land.loc!==s.loc || land.prob!="") return false;
            var region:Object=s.byCell[land.locX+":"+land.locY];
            if(!region) return false;
            var point:Object=region.spawn.length?region.spawn[int(Math.random()*region.spawn.length)]:{x:region.tx+3,y:region.ty+3};
            land.gg.setLocPos((point.x+1)*40,(point.y+1)*40-1);land.gg.dx=3;
            land.loc.lighting(land.gg.X,land.gg.Y-75);return true;
        }
        public static function door(land:*,direction:int,px:Number,py:Number):Object {
            var s:Object=states[land];
            if(!s || land.prob!="") return null;
            coordinates(land);
            if(direction!=5) return land.loc===s.loc?{result:direction==3?{die:true}:null}:null;
            var region:Object=s.byCell[land.locX+":"+land.locY];
            if(!region) return null;
            var z:int=1-land.locZ,target:*=land.locs[land.locX][land.locY][z];
            if(!target) return {result:null};
            var dx:int=region.tx*40,dy:int=region.ty*40;
            var nx:Number=px+(z==0?dx:-dx),ny:Number=py+(z==0?dy:-dy);
            if(target.collisionUnit(nx,ny,land.gg.scX-4,land.gg.scY)) return {result:null};
            land.loc_t=150;land.locZ=z;land.ativateLoc();land.gg.setLocPos(nx,ny);
            return {result:{x:nx,y:ny}};
        }
    }
}
