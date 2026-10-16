"""Exact-value memoization for repeated wall-edge and protection calculations."""
from render_camera_patch import _replace


def apply(relative, source):
    if relative == 'src/wallblend/ReadableJoin.as':
        # The contour's offset depends on material pair, seam and along-edge
        # coordinate. All pixels across that edge share precisely that offset.
        # Keep the original calculation/arithmetic; only memoize its result.
        source = _replace(source,
            '        public static function distance(a:String,b:String,x:Number,y:Number,boundary:int,vertical:Boolean,back:Boolean=false):Number {\n            var signed:Number=(vertical?x:y)-boundary, along:Number=vertical?y:x;',
            '''        private static var edgeOffsets:Object={};
        private static var edgeOffsetCount:int=0;
        public static function distance(a:String,b:String,x:Number,y:Number,boundary:int,vertical:Boolean,back:Boolean=false):Number {
            var along:Number=vertical?y:x;
            var key:String=a+":"+b+":"+boundary+":"+vertical+":"+back;
            var edge:Object=edgeOffsets[key];
            if(!edge) edgeOffsets[key]=edge={};
            var index:String=String(along);
            if(!edge.hasOwnProperty(index)) {
                var value:Number=offset(a,b,along,boundary,vertical,back);
                // Bounded across level changes; no terrain, light or save state.
                if(edgeOffsetCount>=65536) {edgeOffsets={};edgeOffsetCount=0;edgeOffsets[key]=edge={};}
                edge[index]=value;++edgeOffsetCount;
            }
            return (vertical?x:y)-boundary-Number(edge[index]);
        }
        private static function offset(a:String,b:String,along:Number,boundary:int,vertical:Boolean,back:Boolean):Number {''')
        source = _replace(source, '            return signed-offset;', '            return offset;')
    if relative == 'src/wallblend/BlendLayer.as':
        source = _replace(source, '                        if (!materials[id].tone)',
                          '                        if (style!="readable" && !materials[id].tone)')
        source = _replace(source,
            '            var bottomWidth:int = joinWidth(id,cell(tx,ty+1));',
            '''            var bottomWidth:int = joinWidth(id,cell(tx,ty+1));
            var xStrength:Vector.<Number>,yStrength:Vector.<Number>;
            var leftContact:Vector.<Boolean>,rightContact:Vector.<Boolean>;
            var topContact:Vector.<Boolean>,bottomContact:Vector.<Boolean>;
            if(style=="readable") {
                xStrength=new Vector.<Number>(TILE,true);yStrength=new Vector.<Number>(TILE,true);
                leftContact=new Vector.<Boolean>(TILE,true);rightContact=new Vector.<Boolean>(TILE,true);
                topContact=new Vector.<Boolean>(TILE,true);bottomContact=new Vector.<Boolean>(TILE,true);
                for(var edgeIndex:int=0;edgeIndex<TILE;++edgeIndex) {
                    var firstHalf:Boolean=edgeIndex<TILE/2;
                    var edgeDistance:Number=firstHalf?edgeIndex+0.5:TILE-edgeIndex-0.5;
                    xStrength[edgeIndex]=(firstHalf?hasLeft:hasRight)?edgeStrength(edgeDistance,firstHalf?leftWidth:rightWidth):0;
                    yStrength[edgeIndex]=(firstHalf?hasTop:hasBottom)?edgeStrength(edgeDistance,firstHalf?topWidth:bottomWidth):0;
                    leftContact[edgeIndex]=hasLeft && touches(tx,ty,tx-1,ty,edgeIndex);
                    rightContact[edgeIndex]=hasRight && touches(tx,ty,tx+1,ty,edgeIndex);
                    topContact[edgeIndex]=hasTop && touches(tx,ty,tx,ty-1,edgeIndex);
                    bottomContact[edgeIndex]=hasBottom && touches(tx,ty,tx,ty+1,edgeIndex);
                }
            }''')
        source = _replace(source,
            '                    var sx:Number = supported(id,otherX) && touches(tx,ty,nx,ty,py) ? edgeStrength(dx,joinWidth(id,otherX)) : 0;\n'
            '                    var sy:Number = supported(id,otherY) && touches(tx,ty,tx,ny,px) ? edgeStrength(dy,joinWidth(id,otherY)) : 0;',
            '''                    var sx:Number = style=="readable" ? ((px<TILE/2?leftContact[py]:rightContact[py])?xStrength[px]:0) :
                        supported(id,otherX) && touches(tx,ty,nx,ty,py) ? edgeStrength(dx,joinWidth(id,otherX)) : 0;
                    var sy:Number = style=="readable" ? ((py<TILE/2?topContact[px]:bottomContact[px])?yStrength[py]:0) :
                        supported(id,otherY) && touches(tx,ty,tx,ny,px) ? edgeStrength(dy,joinWidth(id,otherY)) : 0;''')
        source = _replace(source, '                guardPixels=source.getVector(guardRect);',
                          '                guardPixels=alphaPrefix(source.getVector(guardRect),int(guardRect.width),int(guardRect.height));')
        start = source.index('        private function alphaGuard(')
        end = source.index('        private function withContactRelief(', start)
        source = source[:start] + '''        private function alphaPrefix(raw:Vector.<uint>,width:int,height:int):Vector.<uint> {
            var stride:int=width+1;
            var sums:Vector.<uint>=new Vector.<uint>(stride*(height+1),true);
            for(var y:int=0;y<height;++y) {
                var row:int=0;
                for(var x:int=0;x<width;++x) {
                    if((raw[y*width+x]>>>24)!=255) ++row;
                    sums[(y+1)*stride+x+1]=sums[y*stride+x+1]+row;
                }
            }
            return sums;
        }
        private function alphaGuard(x:int,y:int,rect:Rectangle,sums:Vector.<uint>):Number {
            var width:int=int(rect.width),height:int=int(rect.height),stride:int=width+1;
            x-=int(rect.x);y-=int(rect.y);
            if(x<1 || y<1 || x+1>=width || y+1>=height) return 0;
            if(sums[(y+2)*stride+x+2]-sums[(y-1)*stride+x+2]-sums[(y+2)*stride+x-1]+sums[(y-1)*stride+x-1]>0) return 0;
            if(x<2 || y<2 || x+2>=width || y+2>=height) return 0.5;
            if(sums[(y+3)*stride+x+3]-sums[(y-2)*stride+x+3]-sums[(y+3)*stride+x-2]+sums[(y-2)*stride+x-2]>0) return 0.5;
            return 1;
        }

''' + source[end:]
    if relative == 'src/wallblend/BackgroundBlendLayer.as':
        source = _replace(source, '    import flash.utils.getTimer;',
                          '    import flash.utils.getTimer;\n    import flash.utils.ByteArray;')
        source = _replace(source, '        private var native:Vector.<uint>;',
                          '        private var native:Vector.<uint>;\n        private var protectedMemo:ByteArray;')
        source = _replace(source, '                native=source.getVector(source.rect);',
                          '                native=source.getVector(source.rect);\n                protectedMemo=new ByteArray();protectedMemo.length=source.width*source.height;')
        source = _replace(source, '                native=null;', '                native=null;protectedMemo=null;')
        source = _replace(source, '        private function protectedAt(x:int,y:int):Boolean {', '''        private function protectedAt(x:int,y:int):Boolean {
            if(!protectedMemo || x<0 || y<0 || x>=source.width || y>=source.height) return protectedUncached(x,y);
            var index:int=y*source.width+x;
            var known:int=int(protectedMemo[index]);
            if(known) return known==2;
            var result:Boolean=protectedUncached(x,y);
            protectedMemo[index]=result?2:1;
            return result;
        }
        private function protectedUncached(x:int,y:int):Boolean {''')
    return source
