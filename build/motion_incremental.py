"""Derive the exact native raster operations, splitting only their scheduling."""
from pathlib import Path
import importlib.util,re
B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('parser',B/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
def patch(s):
    start,end=parser._body(s,'drawLoc');body=s[start+1:end]
    declarations=body[body.index('         var transpFon:'):body.index('         try\n')]
    drawing=body[body.index('            World.w.gr_stage = 1;'):body.index('\n         }\n         catch')]
    stages=re.split(r'            World.w.gr_stage = \d+;',drawing)[1:]
    assert len(stages)==18
    # Native display-list configuration does not belong to an offscreen job.
    stages[2]=stages[2].replace('            this.visLight.visible = this.loc.black && World.w.black;','').replace('            this.warShadow();','')
    stages[17]=stages[17][:stages[17].index('            if(Boolean(nloc.cTransform)')]
    code='      private function sceneDrawSteps(param1:Location):Array\n      {\n'+declarations+'\n         var self:Grafon=this;\n         var steps:Array=[];\n'
    for i,stage in enumerate(stages,1):
        if i in (8,9,17):
            table='arrBack' if i==9 else 'arrFront'
            args='true' if i==8 else 'false,true' if i==17 else 'false'
            code+='''         steps.push((function():Function {
            var remaining:Array=null;
            var next:int=0;
            return function():Boolean {
               if(remaining==null) {
                  remaining=[];
                  for each(var material:Material in self.'''+table+''')if(material.used)remaining.push(material);
               }
               if(next<remaining.length)self.drawKusok(remaining[next++],'''+args+''');
               return next>=remaining.length;
            };
         })());
'''
            if i==17:
                tail=stage[stage.index('            this.backBmp2.draw(back2,'):]
                code+='         steps.push(function():void {\n'+tail.replace('this.','self.')+'\n         });\n'
        elif i==11:
            chunk=stage[stage.index('               if(j == -1)'):stage.rindex('               j++;')]
            code+='         for(var layer:int=-2;layer<=3;++layer)steps.push((function(layerId:int):Function{return function():void {j=layerId;\n'+chunk.replace('this.','self.')+'\n};})(layer));\n'
        else:code+='         steps.push(function():void {\n'+stage.replace('this.','self.').replace('= this;','= self;')+'\n         });\n'
    code+='         steps.push(function():void {self.sceneRestoreMarks();++self.sceneRedraws;});\n         return steps;\n      }\n'
    s=s.replace('      public function Grafon(',code+(B.parent/'src/patches/SceneWarmJob.as.inc').read_text('utf-8')+'\n      public function Grafon(')
    s=s.replace('      private function sceneClear() : void\n      {','      private function sceneClear() : void\n      {\n         this.sceneClearWarm();this.sceneWarmViewX=this.sceneWarmViewY=NaN;this.sceneWarmMean=48;')
    s=s.replace('         if(kind == "decal" || kind == "paint" || kind == "gwall") this.sceneMarks.push', '         this.sceneCancelWarm(affected);\n         if(kind == "decal" || kind == "paint" || kind == "gwall") this.sceneMarks.push')
    old='if(!this.sceneChunks[x+":"+y]) {++this.sceneMisses;this.sceneRender(x,y);}'
    new='''if(!this.sceneChunks[x+":"+y]) {
               ++this.sceneMisses;
               if(this.sceneWarmJob && this.sceneWarmJob.cx==x && this.sceneWarmJob.cy==y)this.sceneAdvanceWarm(true);
               if(!this.sceneChunks[x+":"+y])this.sceneRender(x,y);
            }'''
    assert s.count(old)==1;s=s.replace(old,new)
    s=s.replace('         if(getTimer() < this.sceneNextWarm) return;','         if(this.sceneWarmJob) {this.sceneAdvanceWarm();return;}\n         if(getTimer() < this.sceneNextWarm) return;')
    s=s.replace('            this.sceneRender(bestX,bestY);','            if(this.sceneAsyncWarm) {this.sceneBeginWarm(bestX,bestY);this.sceneAdvanceWarm();return;}\n            this.sceneRender(bestX,bestY);')
    start,end=parser._body(s,'sceneEnsureUpcoming');body=s[start+1:end]
    anchor='         if(!this.sceneUpcomingReady)'
    body=body.replace(anchor,'''         var travelX:Number=isNaN(this.sceneWarmViewX)?0:left-this.sceneWarmViewX;
         var travelY:Number=isNaN(this.sceneWarmViewY)?0:top-this.sceneWarmViewY;
         this.sceneWarmViewX=left;this.sceneWarmViewY=top;
         travelX=Math.abs(travelX)>80?0:travelX;travelY=Math.abs(travelY)>80?0:travelY;
         if(Math.abs(travelX)<0.5)travelX=this.loc.gg.dx;
         if(Math.abs(travelY)<0.5)travelY=this.loc.gg.dy;
         var demand:Number=(Math.abs(travelX)*(maxY-minY+1)+Math.abs(travelY)*(maxX-minX+1))/this.sceneSide;
         this.sceneWarmBudget=Math.max(6,Math.min(24,Math.ceil(this.sceneWarmMean*demand*1.35+2)));
'''+anchor)
    body=body.replace('var dx:Number = this.loc.gg.dx;','var dx:Number = travelX;').replace('var dy:Number = this.loc.gg.dy;','var dy:Number = travelY;')
    anchor='               if(score < best)'
    body=body.replace(anchor,'''               if((dx>0.5 && x>maxX && y>=minY && y<=maxY) || (dx< -0.5 && x<minX && y>=minY && y<=maxY)
                  || (dy>0.5 && y>maxY && x>=minX && x<=maxX) || (dy< -0.5 && y<minY && x>=minX && x<=maxX))score-=100000;
'''+anchor)
    s=s[:start+1]+body+s[end:]
    return s
