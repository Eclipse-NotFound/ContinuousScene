"""Candidate: raster up to three adjacent upcoming chunks in one private job."""
from pathlib import Path
import hashlib, importlib.util, shutil, subprocess, sys

B=Path(__file__).resolve().parent
BASE=B/'generated/motion-direction-rays';OUT=B/'generated/motion-strip'
spec=importlib.util.spec_from_file_location('parser',B/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
JAVA='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
FF=B.parents[2]/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)
def ff(*args):subprocess.run([JAVA,'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)

def patch(s):
    s=once(s,'this.sceneWarmJob.cx==x && this.sceneWarmJob.cy==y',
        'x>=this.sceneWarmJob.cx && x<=this.sceneWarmJob.lastX && y>=this.sceneWarmJob.cy && y<=this.sceneWarmJob.lastY')
    a,z=parser._body(s,'sceneBeginWarm');body=s[a+1:z]
    body=once(body,'''         var size:int = this.sceneSide + 2*this.sceneGutter;
         var bounds:Rectangle = new Rectangle(cx*this.sceneSide-this.sceneGutter,cy*this.sceneSide-this.sceneGutter,size,size);''',
        '''         var lastX:int=cx;
         var lastY:int=cy;
         var view:Rectangle=this.sceneViewport();
         if(view!=null) {
            var horizontal:Boolean=Math.abs(this.loc.gg.dx)>=Math.abs(this.loc.gg.dy);
            if(horizontal && Math.abs(this.loc.gg.dx)>0.5) {
               var lowY:int=Math.max(0,Math.floor(view.top/this.sceneSide));
               var highY:int=Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,Math.ceil(view.bottom/this.sceneSide)-1);
               while(cy>lowY && lastY-cy<2 && !this.sceneChunks[cx+":"+(cy-1)])--cy;
               while(lastY<highY && lastY-cy<2 && !this.sceneChunks[cx+":"+(lastY+1)])++lastY;
            } else if(Math.abs(this.loc.gg.dy)>0.5) {
               var lowX:int=Math.max(0,Math.floor(view.left/this.sceneSide));
               var highX:int=Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,Math.ceil(view.right/this.sceneSide)-1);
               while(cx>lowX && lastX-cx<2 && !this.sceneChunks[(cx-1)+":"+cy])--cx;
               while(lastX<highX && lastX-cx<2 && !this.sceneChunks[(lastX+1)+":"+cy])++lastX;
            }
         }
         var width:int=(lastX-cx+1)*this.sceneSide+2*this.sceneGutter;
         var height:int=(lastY-cy+1)*this.sceneSide+2*this.sceneGutter;
         var bounds:Rectangle=new Rectangle(cx*this.sceneSide-this.sceneGutter,cy*this.sceneSide-this.sceneGutter,width,height);''')
    body=once(body,'{cx:cx,cy:cy,bounds:bounds','{cx:cx,cy:cy,lastX:lastX,lastY:lastY,bounds:bounds')
    body=once(body,'         if(this.sceneWarmBuffers==null) {','''         if(this.sceneWarmBuffers!=null && (this.sceneWarmBuffers[0].width!=width || this.sceneWarmBuffers[0].height!=height)) {
            for each(var oldBuffer:BitmapData in this.sceneWarmBuffers)oldBuffer.dispose();
            this.sceneWarmBuffers=null;
         }
         if(this.sceneWarmBuffers==null) {''')
    body=body.replace('new BitmapData(size,size,true,0)','new BitmapData(width,height,true,0)')
    s=s[:a+1]+body+s[z:]
    s=once(s,'this.rectX=this.rectY=job.bounds.width;', 'this.rectX=job.bounds.width;this.rectY=job.bounds.height;')
    a,z=parser._body(s,'sceneAdvanceWarm');body=s[a+1:z]
    begin=body.index('         if(this.sceneWarmVerify)')
    body=body[:begin]+'''         var parents:Array=[this.visFront,this.visBack,this.visBack2,this.visVoda];
         var size:int=this.sceneSide+2*this.sceneGutter;
         var count:int=0;
         for(var cx:int=job.cx;cx<=job.lastX;++cx)for(var cy:int=job.cy;cy<=job.lastY;++cy) {
            var cut:Rectangle=new Rectangle((cx-job.cx)*this.sceneSide,(cy-job.cy)*this.sceneSide,size,size);
            var pixels:Array=[];
            for(n=0;n<4;++n) {
               var buffer:BitmapData=new BitmapData(size,size,true,0);
               buffer.copyPixels(job.output[n],cut,new Point());pixels.push(buffer);
            }
            if(this.sceneWarmVerify) {
               this.sceneRender(cx,cy);
               var reference:Object=this.sceneChunks[cx+":"+cy];
               var comparison:Object={cx:cx,cy:cy,equal:true,changed:0,max:0,layers:[]};
               for(n=0;n<4;++n) {
                  var layerStats:Object={layer:n,changed:0,max:0,examples:[]};
                  var actual:Vector.<uint> = pixels[n].getVector(pixels[n].rect);
                  var expected:Vector.<uint> = reference.nativeBuffers[n].getVector(reference.nativeBuffers[n].rect);
                  for(var p:int=0;p<actual.length;++p)if(actual[p]!=expected[p]) {
                     comparison.equal=false;++comparison.changed;++layerStats.changed;
                     if(layerStats.examples.length<3)layerStats.examples.push({x:p%size,y:int(p/size),actual:actual[p].toString(16),expected:expected[p].toString(16)});
                     for(var shift:int=0;shift<=24;shift+=8)layerStats.max=Math.max(layerStats.max,Math.abs(int((actual[p]>>>shift)&255)-int((expected[p]>>>shift)&255)));
                  }
                  comparison.max=Math.max(comparison.max,layerStats.max);comparison.layers.push(layerStats);
               }
               this.sceneWarmComparisons.push(comparison);
               this.sceneDrop(reference);delete this.sceneChunks[cx+":"+cy];
            }
            var bitmaps:Array=[];
            for(n=0;n<4;++n) {
               var bitmap:Bitmap=new Bitmap(pixels[n]);
               bitmap.scrollRect=new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
               bitmap.x=cx*this.sceneSide;bitmap.y=cy*this.sceneSide;
               parents[n].addChild(bitmap);bitmaps.push(bitmap);
            }
            var x:Number=cx*this.sceneSide-this.sceneGutter;
            var y:Number=cy*this.sceneSide-this.sceneGutter;
            this.sceneChunks[cx+":"+cy]={cx:cx,cy:cy,bitmaps:bitmaps,sats:null,nativeBuffers:pixels,revision:0,
               backobjs:this.sceneBackdropObjects(x,y,size,size),x:x,y:y,side:this.sceneSide,gutter:this.sceneGutter};
            ++this.sceneResident;++this.sceneWarmCount;++count;
         }
         for each(var output:BitmapData in job.output)output.dispose();
         this.sceneDrawMs=job.work;this.sceneMaxDrawMs=Math.max(this.sceneMaxDrawMs,job.work);
         this.sceneWarmMean=this.sceneWarmMean*0.8+Math.min(200,job.work/count)*0.2;
         this.sceneWarmJob=null;this.sceneNextWarm=getTimer();
      '''
    return s[:a+1]+body+s[z:]

def main():
    assert sha(BASE/'pfe.swf')=='81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015'
    source=patch((BASE/'source/fe/graph/Grafon.as').read_text('utf-8'))
    target=OUT/'source/fe/graph/Grafon.as';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,'utf-8')
    if '--source-only' in sys.argv:return
    ff('-importScript',BASE/'pfe.swf',OUT/'pfe.swf',OUT/'source')
    ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
    baseline=OUT/'audit-base';baseline.mkdir(exist_ok=True)
    shutil.copy2(BASE/'pfe.swf',baseline/'pfe.swf');shutil.copy2(BASE/'pfe.xml',baseline/'host.xml')
    subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(baseline)],check=True)

if __name__=='__main__':main()
