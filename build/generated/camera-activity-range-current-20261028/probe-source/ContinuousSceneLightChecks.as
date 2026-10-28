package {
    import flash.display.BitmapData;
    import flash.geom.Rectangle;
    public class ContinuousSceneLightChecks {
        public static function run(main:*,w:*,check:Function):void {
            var runtime:*=main.getChildByName("LightAndDarknessCarrier")["ladAPI"].runtime;
            var Field:Class=runtime.field.constructor as Class;
            var cached:*=new Field(),reference:*=new Field();
            var x:Number=w.gg.X,y:Number=w.gg.Y-40;
            var view:Rectangle=new Rectangle(x-180,y-120,360,240);
            var lights:Array=[{id:"test",x:x,y:y,radius:200,color:0xffeebb,power:1,angle:0,cone:Math.PI*2,transient:true}];
            var zones:Array=[],ambient:Number=0.14;
            var tile:*=w.loc.getAbsTile(x+40,y),oldOpacity:Number=tile.opac;
            try {
                for(var i:int=0;i<10;++i) {
                    if(i==1)lights[0].power=0.35;
                    if(i==2)lights[0].color=0x66bbff;
                    if(i==3){lights[0].angle=1.2;lights[0].cone=Math.PI/2;}
                    if(i==4)tile.opac=1-oldOpacity;
                    if(i==5)view.x+=17.5;
                    if(i==6){view.width+=85;view.height+=9;}
                    if(i==7)zones=[{x:x-180,y:y-120,width:360,height:240,feather:35,factor:0.25}];
                    if(i==8)ambient=0.45;
                    if(i==9)lights=[];
                    // A fresh forced render is the reference. The other field
                    // carries its previous output through every changed input.
                    reference.render(w.loc,view,lights,ambient,zones,1,false);
                    cached.render(w.loc,view,lights,ambient,zones,1,true);
                    var difference:*=reference.data.compare(cached.data);
                    check("scene-light-input-change-pixels-"+i,difference===0);
                    if(difference is BitmapData)difference.dispose();
                    var count:int=cached.reusedFrames;
                    cached.render(w.loc,view,lights,ambient,zones,1,true);
                    difference=reference.data.compare(cached.data);
                    check("scene-light-identical-frame-reused-"+i,difference===0 && cached.reusedFrames==count+1);
                    if(difference is BitmapData)difference.dispose();
                }
                cached.clear();cached.render(w.loc,view,lights,ambient,zones,1,true);
                difference=reference.data.compare(cached.data);
                check("scene-light-clear-invalidates-cache",difference===0);
                if(difference is BitmapData)difference.dispose();
            } finally {tile.opac=oldOpacity;cached.clear();reference.clear();}
        }
    }
}
