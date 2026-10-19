"""Build only Grafon on the exact current host; candidates stay in build."""
from pathlib import Path
import hashlib, shutil, subprocess, sys, importlib.util

B=Path(__file__).resolve().parent
GAME=B.parents[2]
OUT=B/'generated'/('motion-host-'+(sys.argv[1] if len(sys.argv)>1 else 'small'))
BASE=B/'cache/motion-02bf'
JAVA=Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
FF=GAME/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
EXPECTED='02BFABE6A3B4881DFA1227515E71F2A8EA863D4B1B468FBE1D8008AEBA7D9240'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def ff(*args):subprocess.run([str(JAVA),'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)
def main():
    BASE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    if not (BASE/'pfe.swf').exists():
        assert sha(GAME/'pfe.swf')==EXPECTED,'Host updated; review new baseline'
        shutil.copy2(GAME/'pfe.swf',BASE/'pfe.swf')
    assert sha(BASE/'pfe.swf')==EXPECTED
    if not (BASE/'host.xml').exists():ff('-swf2xml',BASE/'pfe.swf',BASE/'host.xml')
    subprocess.run([sys.executable,str(B/'prepare.py'),str(GAME/'pfe_before_ContinuousScene_20261014-181702.swf'),'--sources-only'],check=True)
    source=(B/'generated/scripts/fe/graph/Grafon.as').read_text(encoding='utf-8-sig')
    # This compact-impact patch is already present in the published 02BF renderer.
    # Its historical build applied it after prepare.py; retain it in regeneration.
    from decal_compact_experiment import HELPER,apply_compact
    source=source.replace('      // Match the two native decal frame choices',HELPER+'      // Match the two native decal frame choices')
    source=apply_compact(source)
    mode=sys.argv[1] if len(sys.argv)>1 else 'small'
    if mode=='small':
        # Rejected experiment: more compositing and repeated raster work.
        source=source.replace('this.sceneChunkSide == 640 ? 640 : 320','this.sceneChunkSide == 640 ? 640 : 160')
        source=source.replace('minX-2','minX-4').replace('maxX+2','maxX+4').replace('minY-2','minY-4').replace('maxY+2','maxY+4')
        source=source.replace('this.sceneNextWarm = getTimer()+100;','this.sceneNextWarm = getTimer();')
    elif mode in ['masks','bitmap-masks']:
        old='''         var list:Array = this.sceneMaskPool[factory];
         if(list == null) this.sceneMaskPool[factory] = list = [];
         var index:int = int(this.sceneMaskCursor[factory]);
         this.sceneMaskCursor[factory] = index + 1;'''
        new='''         var variants:Object = this.sceneMaskPool[factory];
         if(variants == null) this.sceneMaskPool[factory] = variants = {};
         var list:Array = variants[key];
         if(list == null) variants[key] = list = [];
         var cursors:Object = this.sceneMaskCursor[factory];
         if(cursors == null) this.sceneMaskCursor[factory] = cursors = {};
         var index:int = int(cursors[key]);
         cursors[key] = index + 1;'''
        assert source.count(old)==1
        source=source.replace(old,new).replace('sceneMask(factory:Class)','sceneMask(factory:Class,key:String="")')
        for mask in ['textureMask','borderMask']:
            source=source.replace('this.sceneMask(param1.'+mask+')','this.sceneMask(param1.'+mask+',param2 ? [_loc4_.kont1,_loc4_.kont2,_loc4_.kont3,_loc4_.kont4].join(":") : [_loc4_.pont1,_loc4_.pont2,_loc4_.pont3,_loc4_.pont4].join(":"))')
        source=source.replace('this.sceneMask(param1.floorMask)','this.sceneMask(param1.floorMask,"floor:"+_loc4_.kont1+":"+_loc4_.kont2)')
        for prefix,tile,fields in [('param1','param2',['kont','pont']),('_loc5_','_loc4_',['kont'])]:
            for kind in fields:
                for n in range(1,5):
                    call=f'{prefix}.c{n}.gotoAndStop({tile}.{kind}{n} + 1);'
                    source=source.replace(call,f'if({prefix}.c{n}.currentFrame != {tile}.{kind}{n} + 1) '+call)
        if mode=='bitmap-masks':
            source=source.replace('      private function sceneMask(factory:', '      public var sceneMaskBitmaps:Boolean=true;\n      private function sceneMask(factory:')
            source=source.replace('         result.scaleX = result.scaleY = 1;','         result.scaleX = result.scaleY = 1;\n         result.cacheAsBitmap = this.sceneMaskBitmaps;')
    elif mode=='incremental':
        from motion_incremental import patch
        if 'public var sceneAsyncWarm:' not in source:
            source=patch(source)
    elif mode=='profile':
        spec=importlib.util.spec_from_file_location('profile_parser',B/'profile-vision.py')
        parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
        for name in ['drawLoc','drawKusok','sceneMaterialFill','sceneRender','sceneDrawRegionChunk','scenePrepare','sceneBackdropObjects','drawBackWall','warShadow']:
            start,end=parser._body(source,name);body=source[start+1:end];tail=parser._default_return(source,name,start)
            source=source[:start+1]+'\nvar profileStart:int=getTimer();try {\n'+body+'\n} finally {this.sceneMotionRecord("'+name+'",getTimer()-profileStart);}\n'+tail+'\n'+source[end:]
        for n in range(4,20):
            anchor='            World.w.gr_stage = '+str(n)+';'
            # Local drawLoc milestones (same method only).
            start,end=parser._body(source,'drawLoc');body=source[start+1:end]
            if anchor in body:body=body.replace(anchor,'            this.sceneMotionRecord("stage-'+str(n-1)+'",getTimer()-profileStage);profileStage=getTimer();\n'+anchor)
            source=source[:start+1]+body+source[end:]
        source=source.replace('var profileStart:int=getTimer();try {\n\n         if(!this.sceneRasterizing','var profileStage:int=getTimer();var profileStart:int=getTimer();try {\n\n         if(!this.sceneRasterizing')
        anchor='      public function Grafon('
        source=source.replace(anchor,'''      public var sceneMotionProfile:Object={};
      private function sceneMotionRecord(key:String,ms:int):void {
         var row:Object=this.sceneMotionProfile[key];
         if(row==null)this.sceneMotionProfile[key]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
'''+anchor)
    else:raise ValueError(mode)
    target=OUT/'source/fe/graph/Grafon.as';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
    if '--source-only' in sys.argv:
        print('Regenerated source '+sha(target));return
    ff('-importScript',BASE/'pfe.swf',OUT/'pfe.swf',OUT/'source')
    ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
    subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(BASE)],check=True)
    print(sha(OUT/'pfe.swf'))
if __name__=='__main__':main()
