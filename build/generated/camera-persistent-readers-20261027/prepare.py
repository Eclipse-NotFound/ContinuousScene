from pathlib import Path
import ast,importlib.util,re
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-persistent-fullpage-20261027'
MOD=HERE.parents[2];RV=MOD.parent/'RealisticVision/build/combat-render-output/production-final2/src/RVWallSurface.as'
VERSION='camera-persistent-readers-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('persistent_readers_generation',BASE/'prepare.py');one=base.one
PROVIDER='''        /** Read-only native foreground order for consumers before atlas refresh.
         * Caller must apply the original Bitmap crop/transform validation.
         * Null means the normal visible display tree is authoritative. */
        public function nativeTerrainSources(front:DisplayObjectContainer):Array {
            if(!presented || !atlasWorld || atlasWorld.loc!==location || front!==atlasWorld.grafon.visFront)return null;
            var g:*=atlasWorld.grafon,view:Rectangle=g.sceneViewport();
            if(view==null)return null;
            var originals:Dictionary=new Dictionary(),result:Array=[];
            for each(var surface:Object in g.sceneSurfaces()) {
                var bitmap:Bitmap=surface.bitmaps[0] as Bitmap;
                if(bitmap && bitmap.parent===front)originals[bitmap]=view.intersects(new Rectangle(surface.cx*CELL,surface.cy*CELL,CELL,CELL));
            }
            for(var i:int=0;i<front.numChildren;++i) {
                var node:*=front.getChildAt(i);
                if(isOwnedLayer(node))continue;
                if(node in originals) {if(originals[node])result.push(node);}
                else if(node.visible)result.push(node);
            }
            return result;
        }

'''
def classic_source():return base.persistent_source().replace('class ScenePersistentAtlas','class SceneClassicAtlas')
def persistent_source():return one(base.persistent_source(),'        private function createPage(',PROVIDER+'        private function createPage(')
def rv_source(native):
    name='SceneNativeRVWallSurface' if native else 'SceneLegacyRVWallSurface'
    s,n=re.subn(r'\bRVWallSurface\b',name,RV.read_text('utf-8-sig'));assert n==2,n
    s=one(s,'      private static const CELL:int = 40;', '''      public var nativeTerrainSources:Function;
      public function diagnosticSources(front:DisplayObjectContainer):Array {left=0;top=0;return foregroundSources(front);}
      private static const CELL:int = 40;''')
    if native:
        start=s.index('         var node:DisplayObject,bmp:Bitmap,i:int;',s.index('private function foregroundSources('))
        end=s.index('            var scroll:Rectangle=bmp.scrollRect;',start)
        old=s[start:end]
        assert old.count('front.getChildAt(i)')==2
        s=s[:start]+'''         var node:DisplayObject,bmp:Bitmap,i:int;
         var nodes:Array=nativeTerrainSources==null?null:nativeTerrainSources(front);
         if(nodes==null) {
            nodes=[];
            for(i=0;i<front.numChildren;i++) {node=front.getChildAt(i);if(node.visible)nodes.push(node);}
         }
         for each(node in nodes)if(!(node is Bitmap)||!plain(node))return null;
         var sources:Array=[];
         for each(node in nodes){
            bmp=node as Bitmap;
            if(bmp==null||bmp.bitmapData==null)continue;
'''+s[end:]
    return s
def fixture_source():
    s=(BASE/'tests/ScenePersistentAtlasChecks.as').read_text('utf-8-sig')
    return one(s,'                checkpoint(ctx,"first");','                checkpoint(ctx,"first");\n                out.readerContract=SceneNativeReaderChecks.run(ctx);\n                require(out.readerContract.passed,"Native terrain reader contract failed");')
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'measurementFrames:2880','measurementFrames:0')
    s=one(s,'                        phase=2;settle=0;','                        report.functionalOnly=true;report.complete=true;report.passed=true;clear(w);')
    return s
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=s.replace('len(after) == 89','len(after) == 92').replace("len(value['frozenSourceSHA256']) == 89","len(value['frozenSourceSHA256']) == 92")
    s=one(s,"2880 persistent atlas camera intervals, active quiet world; no deployment","Native terrain reader functional checks only; no timing or deployment")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('SceneClassicAtlas.as',classic_source()),('ScenePersistentAtlas.as',persistent_source()),('SceneLegacyRVWallSurface.as',rv_source(False)),('SceneNativeRVWallSurface.as',rv_source(True)),('tests/ScenePersistentAtlasChecks.as',fixture_source()),('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared read-only native terrain provider and isolated D44 RV source comparison')
