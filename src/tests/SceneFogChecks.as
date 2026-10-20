package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.geom.Point;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Synchronous state-and-pixel comparison in owned test instances only. */
    public class SceneFogChecks {
        public static function benchmark(w:*):Array {
            var loc:*=w.loc,api:*=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            var bitmap:BitmapData=w.grafon.lightBmp,base:BitmapData=bitmap.clone(),saved:Array=[],result:Array=[];
            var oldFlag:*=api["fogTypedEnabled"],oldRelight:int=loc.relight_t;
            for(var x:int=0;x<loc.spaceX;++x)for(var y:int=0;y<loc.spaceY;++y){var t:*=loc.space[x][y];saved.push([t,t.visi,t.t_visi]);}
            try {
                for(var run:int=0;run<4;++run){
                    for each(var item:Array in saved){item[0].visi=item[1];item[0].t_visi=item[2];}
                    bitmap.copyPixels(base,base.rect,new Point());api["fogTypedEnabled"]=run==1 || run==2;
                    var start:int=getTimer();
                    for(var n:int=0;n<120;++n)loc.lighting(w.gg.X+(n%30)*8,w.gg.Y,600,2000);
                    result.push({typed:api["fogTypedEnabled"],calls:120,ms:getTimer()-start});
                }
            } finally {
                for each(item in saved){item[0].visi=item[1];item[0].t_visi=item[2];}
                bitmap.copyPixels(base,base.rect,new Point());base.dispose();api["fogTypedEnabled"]=oldFlag;loc.relight_t=oldRelight;
            }
            return result;
        }
        public static function run(w:*,check:Function):Object {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)
                throw new Error("Fog comparison requires owned motion test ID");
            var loc:*=w.loc,bitmap:BitmapData=w.grafon.lightBmp,base:BitmapData=bitmap.clone();
            var saved:Array=[],targets:Array=[];
            var oldDark:Boolean=loc.retDark,oldRelight:int=loc.relight_t;
            var result:Object={comparisons:0,referenceMs:0,candidateMs:0};
            var x:int,y:int,tile:*,row:Array;
            for(x=0;x<loc.spaceX;++x)for(y=0;y<loc.spaceY;++y) {
                tile=loc.space[x][y];saved.push([tile,tile.visi,tile.t_visi]);
            }
            targets=[[-10000,-10000,-1,-1],[w.gg.X,w.gg.Y,300,1000],
                [0,0,0,80],[loc.limX-1,loc.limY-1,100,2000],
                [1920,4000,300,1000],[-100,200,100,300],
                [loc.limX+200,loc.limY+200,100,300],[w.gg.X,w.gg.Y,0,0],
                [w.gg.X,w.gg.Y,600,2000],
                [w.gg.X+40,w.gg.Y,600,2000],[w.gg.X-40,w.gg.Y-40,600,2000],
                [w.gg.X,w.gg.Y,2000,2000],[w.gg.X,w.gg.Y,3000,2000]];
            try {
                for(var dark:int=0;dark<2;++dark)for(var pattern:int=0;pattern<3;++pattern)
                    for(var n:int=0;n<targets.length;++n) {
                        loc.retDark=dark==1;bitmap.copyPixels(base,base.rect,new Point());
                        var i:int=0;
                        for each(row in saved) {
                            row[0].visi=pattern==2?0.99:pattern?((i*13)%101)/100:row[1];
                            row[0].t_visi=pattern?((i*7)%101)/100:row[2];++i;
                        }
                        var args:Array=targets[n],start:int=getTimer();
                        reference(loc,args[0],args[1],args[2],args[3]);result.referenceMs+=getTimer()-start;
                        var expected:BitmapData=bitmap.clone(),values:Array=[];
                        for each(row in saved)values.push(row[0].visi,row[0].t_visi);
                        var expectedRelight:int=loc.relight_t;
                        bitmap.copyPixels(base,base.rect,new Point());i=0;
                        for each(row in saved) {
                            row[0].visi=pattern==2?0.99:pattern?((i*13)%101)/100:row[1];
                            row[0].t_visi=pattern?((i*7)%101)/100:row[2];++i;
                        }
                        start=getTimer();loc.lighting(args[0],args[1],args[2],args[3]);result.candidateMs+=getTimer()-start;
                        var equal:Boolean=loc.relight_t==expectedRelight;i=0;
                        for each(row in saved) {
                            if(row[0].visi!==values[i] || row[0].t_visi!==values[i+1])equal=false;
                            i+=2;
                        }
                        var difference:*=bitmap.compare(expected);
                        check("native-fog-state-and-pixels-"+dark+"-"+pattern+"-"+n,equal && difference===0);
                        if(difference is BitmapData)difference.dispose();expected.dispose();++result.comparisons;
                    }
            } finally {
                for each(row in saved){row[0].visi=row[1];row[0].t_visi=row[2];}
                bitmap.copyPixels(base,base.rect,new Point());base.dispose();loc.retDark=oldDark;loc.relight_t=oldRelight;
            }
            return result;
        }
        private static function reference(loc:*,param1:int=-10000,param2:int=-10000,param3:int=-1,param4:int=-1):* {
            var Tile:Class=getDefinitionByName("fe.loc.Tile") as Class;

         var _loc5_:Number = NaN;
         var _loc6_:Number = NaN;
         var _loc8_:* = undefined;
         var _loc9_:int = 0;
         var _loc10_:int = 0;
         var _loc11_:* = undefined;
         var _loc12_:* = undefined;
         var _loc13_:Number = NaN;
         var _loc14_:Number = NaN;
         var _loc15_:int = 0;
         var _loc16_:* = undefined;
         var _loc17_:* = null;
         var _loc18_:Number = NaN;
         if(!loc.active)
         {
            return;
         }
         if(param3 < 0)
         {
            param3 = loc.lDist1;
         }
         if(param4 < 0)
         {
            param4 = loc.lDist2;
         }
         if(param1 == -10000)
         {
            param1 = loc.gg.X + loc.gg.storona * 12;
            param2 = loc.gg.Y1 + loc.gg.stayY * 0.247;
         }
         loc.relight_t = 10;
         var _loc7_:* = 1;
         while(_loc7_ < loc.spaceX)
         {
            _loc8_ = 1;
            while(_loc8_ < loc.spaceY)
            {
               _loc5_ = Number(loc.space[_loc7_][_loc8_].visi);
               if(!(!loc.retDark && _loc5_ >= 1))
               {
                  _loc9_ = _loc7_ * Tile.tileX - param1;
                  _loc10_ = _loc8_ * Tile.tileY - param2;
                  _loc11_ = _loc9_ * _loc9_ + _loc10_ * _loc10_;
                  if(_loc11_ >= param4 * param4)
                  {
                     if(loc.retDark && loc.space[_loc7_][_loc8_].t_visi > 0)
                     {
                        loc.space[_loc7_][_loc8_].t_visi -= 0.025;
                        if(loc.space[_loc7_][_loc8_].t_visi < 0)
                        {
                           loc.space[_loc7_][_loc8_].t_visi = 0;
                        }
                        loc.grafon.lightBmp.setPixel32(_loc7_,_loc8_ + 1,Math.floor((1 - loc.space[_loc7_][_loc8_].updVisi()) * 255) * 16777216);
                     }
                  }
                  else
                  {
                     _loc12_ = Math.sqrt(_loc11_);
                     if(_loc12_ <= param3)
                     {
                        _loc6_ = 1;
                     }
                     else
                     {
                        _loc6_ = (param4 - _loc12_) / (param4 - param3);
                     }
                     if(_loc11_ <= param4 * param4)
                     {
                        if(Math.abs(_loc9_) == Math.abs(_loc10_))
                        {
                           _loc10_++;
                        }
                        if(Math.abs(_loc9_) >= Math.abs(_loc10_))
                        {
                           if(_loc9_ > 0)
                           {
                              _loc13_ = Tile.tileX;
                              _loc14_ = _loc10_ / _loc9_ * Tile.tileY;
                           }
                           else
                           {
                              _loc13_ = -Tile.tileX;
                              _loc14_ = -_loc10_ / _loc9_ * Tile.tileY;
                           }
                           _loc15_ = _loc9_ / _loc13_;
                        }
                        else
                        {
                           if(_loc10_ > 0)
                           {
                              _loc14_ = Tile.tileY;
                              _loc13_ = _loc9_ / _loc10_ * Tile.tileX;
                           }
                           else
                           {
                              _loc14_ = -Tile.tileY;
                              _loc13_ = -_loc9_ / _loc10_ * Tile.tileX;
                           }
                           _loc15_ = _loc10_ / _loc14_;
                        }
                        _loc16_ = 1;
                        while(_loc16_ <= _loc15_)
                        {
                           _loc17_ = loc.getAbsTile(param1 + _loc16_ * _loc13_,param2 + _loc16_ * _loc14_);
                           _loc18_ = _loc17_.opac;
                           if(loc.opacWater > 0 && _loc17_.water > 0 && loc.opacWater > _loc18_)
                           {
                              _loc18_ = loc.opacWater;
                           }
                           if(_loc18_ > 0)
                           {
                              _loc6_ -= _loc18_;
                              if(_loc6_ <= 0)
                              {
                                 _loc6_ = 0;
                                 break;
                              }
                           }
                           _loc16_++;
                        }
                     }
                     if(_loc6_ > 1)
                     {
                        _loc6_ = 1;
                     }
                     if(_loc6_ > _loc5_ + 0.01)
                     {
                        loc.space[_loc7_][_loc8_].t_visi = _loc6_;
                        loc.grafon.lightBmp.setPixel32(_loc7_,_loc8_ + 1,Math.floor((1 - loc.space[_loc7_][_loc8_].updVisi()) * 255) * 16777216);
                     }
                     else if(loc.retDark && _loc6_ < _loc5_ - 0.01)
                     {
                        loc.space[_loc7_][_loc8_].t_visi -= 0.025;
                        if(loc.space[_loc7_][_loc8_].t_visi < _loc6_)
                        {
                           loc.space[_loc7_][_loc8_].t_visi = _loc6_;
                        }
                        loc.grafon.lightBmp.setPixel32(_loc7_,_loc8_ + 1,Math.floor((1 - loc.space[_loc7_][_loc8_].updVisi()) * 255) * 16777216);
                     }
                  }
               }
               _loc8_++;
            }
            _loc7_++;
         }
            return;
        }
    }
}
