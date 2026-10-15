"""Exact-value memoization for repeated wall-edge and protection calculations."""
from render_camera_patch import _replace


def apply(relative, source):
    if relative == 'src/wallblend/BlendLayer.as':
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
