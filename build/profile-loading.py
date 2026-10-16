"""Prepare isolated-only load profiling sources; never changes installed files."""
from pathlib import Path
import importlib.util
import json
import hashlib
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated/load-profile'
spec = importlib.util.spec_from_file_location('vision_profile', ROOT / 'profile-vision.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def wrap(source, name, label, owner):
    start, end = parser._body(source, name)
    body = source[start+1:end]
    tail = parser._default_return(source, name, start)
    return source[:start+1] + '\nvar csLoadStarted:int=getTimer();\ntry {\n' + body + \
        '\n} finally { ' + owner + '("' + label + '",getTimer()-csLoadStarted); }' + tail + '\n' + source[end:]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    native = ROOT / 'generated/scripts/fe/graph/Grafon.as'
    source = native.read_text(encoding='utf-8-sig')
    anchor = '      public function Grafon(param1:Sprite)'
    source=source.replace(anchor,'''      private var sceneProfileLegacyMaterials:Boolean = false;
      public var sceneProfileWantOracle:Boolean = false;
      public var sceneProfileRasterResult:Object;
''' + anchor)
    source=source.replace('if(this.sceneLarge)\n         {\n            var scenePaintRect:',
                          'if(this.sceneLarge && !this.sceneProfileLegacyMaterials)\n         {\n            var scenePaintRect:')
    # Separate mask construction from Flash's bitmap caching/material filters.
    start,end=parser._body(source,'drawKusok')
    body=source[start+1:end]
    body=body.replace('         var _loc6_:Sprite = new Sprite();','         var materialStart:int=getTimer();\n         var _loc6_:Sprite = new Sprite();')
    body=body.replace('         this.m.tx = 0;', '         this.sceneProfileRecord("material-mask-build",getTimer()-materialStart);\n         materialStart=getTimer();\n         this.m.tx = 0;')
    body=body.replace('         if(this.sceneLarge)\n         {\n            _loc7_.mask = null;', '         this.sceneProfileRecord("material-raster-filters",getTimer()-materialStart);\n         materialStart=getTimer();\n         if(this.sceneLarge)\n         {\n            _loc7_.mask = null;')
    body+='\n         this.sceneProfileRecord("material-cleanup",getTimer()-materialStart);\n'
    source=source[:start+1]+body+source[end:]
    anchor = '               this.sceneRegionDrawPass(style);\n               buffers = '
    assert source.count(anchor)==1
    source=source.replace(anchor, '               this.sceneRegionDrawPass(style);\n               this.sceneProfileComparePass(style);\n               buffers = ')
    start,end=parser._body(source,'sceneOpen')
    source=source[:end]+'         this.sceneProfileWantOracle = false;\n'+source[end:]
    for name in ['sceneOpen','sceneClear','sceneRender','sceneIndexBackdrops','sceneDrawRegionChunk',
                 'drawLoc','drawKusok','drawBackWall','setLight','drawAllObjs']:
        source = wrap(source,name,'Grafon.'+name,'this.sceneProfileRecord')
    anchor = '      public function Grafon(param1:Sprite)'
    assert source.count(anchor)==1
    source=source.replace(anchor,(ROOT.parent/'src/tests/SceneRasterProbe.as.inc').read_text(encoding='utf-8')+anchor)
    source=source.replace(anchor,'''      public var sceneLoadProfile:Object = {};
      public function sceneProfileBuffers():Array {
         var values:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
         var names:Array = ["front","back","back2","water"];
         var result:Array = [];
         for(var n:int = 0; n < 4; ++n) {
            var aliases:int = 0;
            for each(var surface:Object in this.sceneChunks)
               for each(var data:BitmapData in surface.nativeBuffers) if(data === values[n]) ++aliases;
            var row:Object = {name:names[n],residentAliases:aliases,scratchSame:values[n] === this.sceneScratch[n]};
            try { row.width = values[n].width; row.height = values[n].height; }
            catch(e:Error) {row.error = e.message;}
            result.push(row);
         }
         return result;
      }
      private function sceneProfileRecord(key:String,ms:int):void {
         var row:Object=this.sceneLoadProfile[key];
         if(row==null) this.sceneLoadProfile[key]=row={calls:0,ms:0,max:0};
         ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
      }
''' + anchor)
    grafon=OUT/'host/fe/graph/Grafon.as';grafon.parent.mkdir(parents=True,exist_ok=True)
    grafon.write_text(source,encoding='utf-8')
    wb=OUT/'wb'
    shutil.copytree(ROOT/'generated/wb-production',wb,dirs_exist_ok=True)
    (wb/'wallblend/LoadProfile.as').write_text('''package wallblend {
    public final class LoadProfile {
        public static var rows:Object={};
        public static function record(key:String,ms:int):void {
            var row:Object=rows[key];
            if(row==null) rows[key]=row={calls:0,ms:0,max:0};
            ++row.calls;row.ms+=ms;row.max=Math.max(row.max,ms);
        }
    }
}
''',encoding='utf-8')
    groups={'SceneBlendCache':['update','makePasses','view','refreshView','compose'],
            'BlendLayer':['update','rebuild','prepareMaterials','makePatch'],
            'BackgroundBlendLayer':['update','prepare','addStrip']}
    for cls,names in groups.items():
        path=wb/('wallblend/'+cls+'.as');text=path.read_text(encoding='utf-8-sig')
        if 'import flash.utils.getTimer;' not in text:
            text=text.replace('package wallblend {','package wallblend {\n    import flash.utils.getTimer;')
        for name in names:text=wrap(text,name,cls+'.'+name,'LoadProfile.record')
        path.write_text(text,encoding='utf-8')
    path=wb/'WallBlendMod.as';text=path.read_text(encoding='utf-8-sig')
    anchor='return {version:VERSION, enabled:enabled, failed:failed, mode:mode,'
    assert text.count(anchor)==1
    path.write_text(text.replace(anchor,'return {loadProfile:wallblend.LoadProfile.rows,version:VERSION, enabled:enabled, failed:failed, mode:mode,'),encoding='utf-8')
    (OUT/'provenance.json').write_text(json.dumps({'purpose':'isolated profiling only','grafonSourceSHA256':hashlib.sha256(native.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    print(OUT)


if __name__=='__main__':main()
