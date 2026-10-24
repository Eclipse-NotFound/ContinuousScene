      public function checkShelf(param1:Number, param2:Number = 0) : Number
      {
         var _loc3_:* = undefined;
         var _loc4_:Box = null;
         for(_loc3_ in loc.objs)
         {
            _loc4_ = loc.objs[_loc3_] as Box;
            if(!_loc4_.invis && _loc4_.shelf && !_loc4_.levit && !(X2 < _loc4_.X1 || X1 > _loc4_.X2) && Y2 + param2 <= _loc4_.Y1 && Y2 + param1 + param2 > _loc4_.Y1)
            {
               this.shX1 = this.shX2 = 1;
               if(-(X1 - _loc4_.X1) / scX < this.shX1)
               {
                  this.shX1 = -(X1 - _loc4_.X1) / scX;
               }
               if((X2 - _loc4_.X2) / scX < this.shX2)
               {
                  this.shX2 = (X2 - _loc4_.X2) / scX;
               }
               this.stayMat = _loc4_.mat;
               this.stayPhis = 2;
               this.stayOsn = _loc4_;
               if(!_loc4_.stay)
               {
                  _loc4_.dy += dy * massa / (massa + _loc4_.massa);
                  _loc4_.fixPlav = false;
               }
               return _loc4_.Y1;
            }
         }
         return 0;
      }
