package tests {
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;
    public class SceneObjectChecks {
        private static const ARRAYS:Array=["units","ups","objs","bonuses","areas","acts","saves","backobjs","enspawn","signposts","recalcTiles"];
        private static const XF:Array=["X","X1","X2","begX","stX","weaponX","magicX","celX","acelX","eyeX"];
        private static const YF:Array=["Y","Y1","Y2","begY","stY","weaponY","magicY","celY","acelY","eyeY"];
        public static function capture(land:*):Object {
            var s:Object={records:[],arrays:{},chain:new Dictionary(),seen:new Dictionary(),regions:[],gg:land.gg,pet:land.gg.defpet};
            for each(var field:String in ARRAYS)s.arrays[field]=new Dictionary();
            for(var x:int=land.minLocX;x<land.maxLocX;++x)for(var y:int=land.minLocY;y<land.maxLocY;++y){
                var loc:*=land.locs[x][y][0];if(!loc)continue;
                var dx:Number=(x-land.minLocX)*1920,dy:Number=(y-land.minLocY)*1000;
                s.regions.push({x:x,y:y,kolXp:loc.kolXp,maxXp:loc.maxXp,unXp:loc.unXp,summXp:loc.summXp});
                var count:int=0;
                for(var obj:*=loc.firstObj;obj;obj=obj.nobj){
                    if(++count>20000)throw new Error("Native chain cycle");
                    if(obj===s.gg || obj===s.pet)continue;
                    s.chain[obj]=true;record(s,obj,dx,dy,false);
                }
                for each(field in ARRAYS)if(loc[field])for each(obj in loc[field]){
                    if(obj==null || obj===s.gg || obj===s.pet)continue;
                    s.arrays[field][obj]=true;
                    if(field!="recalcTiles")record(s,obj,dx,dy,field=="enspawn" || field=="signposts");
                }
            }
            return s;
        }
        private static function record(s:Object,obj:*,dx:Number,dy:Number,lower:Boolean):void {
            if(s.seen[obj] || typeof(obj)!="object")return;s.seen[obj]=true;
            var name:String=getQualifiedClassName(obj),r:Object={ref:obj,name:name,id:"id" in obj?obj.id:"",dx:dx,dy:dy,values:{},visuals:{},isBack:name=="fe.graph::BackObj"};
            var field:String;
            if(lower){for each(field in ["x","y"])if(field in obj)r.values[field]=obj[field]+(field=="x"?dx:dy);}
            else {
                for each(field in XF)if(field in obj && isFinite(Number(obj[field])))r.values[field]=obj[field]+dx;
                for each(field in YF)if(field in obj && isFinite(Number(obj[field])))r.values[field]=obj[field]+dy;
                if("inter" in obj && obj.inter)r.inter={x:obj.inter.X+dx,y:obj.inter.Y+dy,hasX:isFinite(obj.inter.X),hasY:isFinite(obj.inter.Y)};
                // BackObj images are shared raster templates, not world display nodes.
                if(!r.isBack)for each(field in ["vis","shad","vis2"])if(field in obj && obj[field])
                    r.visuals[field]={x:obj[field].x+dx,y:obj[field].y+dy};
            }
            s.records.push(r);
            if("un" in obj && obj.un)record(s,obj.un,dx,dy,false);
            if("area" in obj && obj.area)record(s,obj.area,dx,dy,false);
            if("inter" in obj && obj.inter && obj.inter.area)record(s,obj.inter.area,dx,dy,false);
        }
        private static function count(d:Dictionary):int {var n:int=0;for(var key:* in d)++n;return n;}
        public static function compare(s:Object,state:Object):Object {
            var r:Object={ok:true,regions:s.regions,arrays:{},classes:{},logicalMismatch:0,ownershipMismatch:0,interMismatch:0,staticVisualMismatch:0,unitVisualMismatch:0,missing:0,extra:0,samples:[]};
            if(!state){r.ok=false;r.error="No merge state";return r;}
            var loc:*=state.loc,actual:Dictionary=new Dictionary(),obj:*,field:String,n:int=0,chainObjects:int=0;
            for(obj=loc.firstObj;obj;obj=obj.nobj){if(++n>20000){r.ok=false;r.error="Merged chain cycle";return r;}if(obj!==s.gg && obj!==s.pet){chainObjects++;actual[obj]=true;}}
            r.chain={before:count(s.chain),after:count(actual),missing:0,extra:0,duplicates:chainObjects-count(actual)};
            for(obj in s.chain)if(!actual[obj])r.chain.missing++;
            for(obj in actual)if(!s.chain[obj])r.chain.extra++;
            r.missing+=r.chain.missing;r.extra+=r.chain.extra;
            for each(field in ARRAYS){
                actual=new Dictionary();var duplicate:int=0;
                for each(obj in loc[field]){if(obj==null || obj===s.gg || obj===s.pet)continue;if(actual[obj])duplicate++;actual[obj]=true;}
                var a:Object={before:count(s.arrays[field]),after:count(actual),missing:0,extra:0,duplicates:duplicate};
                for(obj in s.arrays[field])if(!actual[obj])a.missing++;
                for(obj in actual)if(!s.arrays[field][obj])a.extra++;
                r.arrays[field]=a;r.missing+=a.missing;r.extra+=a.extra;
                if(duplicate)r.ok=false;
            }
            var Unit:Class=getDefinitionByName("fe.unit.Unit") as Class;
            for each(var old:Object in s.records){
                obj=old.ref;
                if(!r.classes[old.name])r.classes[old.name]={count:0,logical:0,visual:0};
                r.classes[old.name].count++;
                for(field in old.values)if(!isFinite(Number(obj[field])) || Math.abs(Number(obj[field])-old.values[field])>0.001){r.logicalMismatch++;r.classes[old.name].logical++;sample(r,old,field,old.values[field],obj[field]);}
                if("loc" in obj && obj.loc!==loc){r.ownershipMismatch++;sample(r,old,"loc","merged","other");}
                if(old.inter && (!obj.inter || obj.inter.loc!==loc || (old.inter.hasX && (!isFinite(obj.inter.X) || Math.abs(obj.inter.X-old.inter.x)>0.001)) || (old.inter.hasY && (!isFinite(obj.inter.Y) || Math.abs(obj.inter.Y-old.inter.y)>0.001)))){r.interMismatch++;sample(r,old,"inter",old.inter,obj.inter?{x:obj.inter.X,y:obj.inter.Y}:null);}
                for(field in old.visuals){var v:*=obj[field],exp:Object=old.visuals[field];
                    if(!v || !isFinite(v.x) || !isFinite(v.y) || Math.abs(v.x-exp.x)>0.001 || Math.abs(v.y-exp.y)>0.001){
                        if(obj is Unit)r.unitVisualMismatch++;else r.staticVisualMismatch++;
                        r.classes[old.name].visual++;sample(r,old,field,exp,v?{x:v.x,y:v.y}:null);
                    }
                }
            }
            r.ok=r.ok && !r.chain.duplicates && !r.missing && !r.extra && !r.logicalMismatch && !r.ownershipMismatch && !r.interMismatch && !r.staticVisualMismatch;
            return r;
        }
        private static function sample(r:Object,old:Object,field:String,expected:*,actual:*):void {
            if(r.samples.length<35)r.samples.push({className:old.name,id:old.id,offset:{x:old.dx,y:old.dy},field:field,expected:expected,actual:actual});
        }
    }
}
