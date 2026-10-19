package {
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;
    public class ContinuousSceneLightRayChecks {
        private static function lights(x:Number,y:Number,frame:int):Array {
            var result:Array=[];
            for(var i:int=0;i<8;++i)result.push({id:"test"+i,x:x+(i-4)*24+frame*.75,y:y+(i%3)*19,
                radius:90+(i%4)*35,color:0xffeebb,power:0.8,angle:frame*.03,cone:i%2?Math.PI:Math.PI*2,transient:true});
            return result;
        }
        public static function run(main:*,w:*,check:Function):Array {
            var runtime:*=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
            var Field:Class=runtime.field.constructor as Class;
            var reference:*=new Field(),cached:*=new Field();
            reference.useOpacitySnapshot=false;cached.useOpacitySnapshot=true;
            reference.reuseSceneFrames=cached.reuseSceneFrames=false;
            var x:Number=w.gg.X,y:Number=w.gg.Y-60,view:Rectangle=new Rectangle(x-240,y-160,480,320);
            var tile:*=w.loc.getAbsTile(x+40,y),opacity:Number=tile.opac;
            var rows:Array=[];
            try {
                for(var i:int=0;i<20;++i) {
                    tile.opac=[0,0.25,0.7,1][i%4];
                    var values:Array=lights(x,y,i);
                    reference.render(w.loc,view,values,0.14,null,1,true);
                    cached.render(w.loc,view,values,0.14,null,1,true);
                    var diff:*=reference.data.compare(cached.data);
                    check("light-opacity-snapshot-exact-pixels-"+i,diff===0);
                    if(diff is BitmapData)diff.dispose();
                    // External gameplay queries must read the current tile,
                    // including a wall changed after the render snapshot.
                    tile.opac=1-tile.opac;
                    check("light-external-ray-current-wall-"+i,
                        reference.traceRay(x,y,1,0,220)===cached.traceRay(x,y,1,0,220));
                }
                tile.opac=opacity;
                for(var pass:int=0;pass<4;++pass) {
                    var field:*=(pass%2)==1?cached:reference;field.clear();
                    var start:int=getTimer();
                    for(i=0;i<40;++i)field.render(w.loc,view,lights(x,y,i),0.14,null,1,true);
                    rows.push({snapshot:(pass%2)==1,renders:40,ms:getTimer()-start});
                }
            } finally {tile.opac=opacity;reference.clear();cached.clear();}
            return rows;
        }
    }
}
