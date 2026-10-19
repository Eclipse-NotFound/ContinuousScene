"""Bound no-return-dark native sight scans; transplant only Location.lighting."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess, sys
import objects_native_patch as methods

B=Path(__file__).resolve().parent
RAYS='--rays' in sys.argv
CEILING='--ceiling' in sys.argv or RAYS
OUT=B/('generated/motion-fog-rays' if RAYS else 'generated/motion-fog-ceiling' if CEILING else 'generated/motion-fog')
HOST=B/'generated/motion-host-incremental/pfe.swf'
ORIGINAL=B/'generated/motion-native-profile/original/scripts/fe/loc/Location.as'
JAVA='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
FF=B.parents[2]/'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
spec=importlib.util.spec_from_file_location('parser',B/'profile-vision.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def once(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new)

def ff(*args):subprocess.run([JAVA,'-Xmx1400m','-jar',str(FF),*map(str,args)],check=True)

def prepare():
    assert hashlib.sha256(HOST.read_bytes()).hexdigest().upper()=='4D9CEF1FC713E50666971DEFDAB3A313F7FB46E10A332A32367ED965027DB5FC'
    if not ORIGINAL.exists():
        ff('-selectclass','fe.loc.Location','-export','script',ORIGINAL.parents[3],HOST)
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest().upper()=='85F18E1FBEF6FDC2BD2656A22C4EA9C7B10C36EC20A21C821E78674B68E2A87C'
    source=ORIGINAL.read_text('utf-8-sig');a,z=parser._body(source,'lighting');original=source[a+1:z]
    body=once(original,'         var _loc7_:* = 1;','''         // Outside the radius the native algorithm changes nothing unless
         // returning darkness is enabled. Keep that mode's full-map fade.
         var bounded:Boolean=(this.spaceX>48 || this.spaceY>25) && !this.retDark;
         if(bounded) {
            var control:Object=World.w.main.getChildByName("ContinuousSceneCarrier");
            if(control!=null && control["nativeAPI"]!=null && control["nativeAPI"]["fogBoundsEnabled"]===false)bounded=false;
         }
         var firstX:int=bounded?Math.max(1,Math.ceil((param1-param4)/Tile.tileX)):1;
         var firstY:int=bounded?Math.max(1,Math.ceil((param2-param4)/Tile.tileY)):1;
         var lastX:int=bounded?Math.min(this.spaceX,Math.floor((param1+param4)/Tile.tileX)+1):this.spaceX;
         var lastY:int=bounded?Math.min(this.spaceY,Math.floor((param2+param4)/Tile.tileY)+1):this.spaceY;
         var _loc7_:* = firstX;''')
    body=once(body,'while(_loc7_ < this.spaceX)','while(_loc7_ < lastX)')
    body=once(body,'            _loc8_ = 1;','            _loc8_ = firstY;')
    body=once(body,'while(_loc8_ < this.spaceY)','while(_loc8_ < lastY)')
    if CEILING:
        # Occlusion only subtracts positive opacity. With persistent exploration,
        # a ray whose best possible value cannot improve visi has no effect.
        body=once(body,'if(_loc11_ <= param4 * param4)',
            'if(_loc11_ <= param4 * param4 && (!bounded || _loc6_ > _loc5_ + 0.01))')
        body=once(body,'''                                 break;
                              }
                           }
                           _loc16_++;''','''                                 break;
                              }
                              if(bounded && _loc6_ <= _loc5_ + 0.01) break;
                           }
                           _loc16_++;''')
    if RAYS:
        # An interior start and native interior destination keep the whole ray
        # inside the rectangular grid. Preserve the function's int-argument
        # conversion; use the original checked helper for all exterior starts.
        body=once(body,'         var firstX:int=',
            '''         var interiorRay:Boolean=bounded && param1>=0 && param2>=0
            && param1<this.spaceX*Tile.tileX && param2<this.spaceY*Tile.tileY;
         var raySpace:Array=this.space;
         var firstX:int=''')
        body=once(body,'_loc17_ = this.getAbsTile(param1 + _loc16_ * _loc13_,param2 + _loc16_ * _loc14_);',
            '''_loc17_ = interiorRay
                              ? raySpace[int(int(param1 + _loc16_ * _loc13_) / Tile.tileX)][int(int(param2 + _loc16_ * _loc14_) / Tile.tileY)] as Tile
                              : this.getAbsTile(param1 + _loc16_ * _loc13_,param2 + _loc16_ * _loc14_);''')
    target=OUT/'source/fe/loc/Location.as';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(source[:a+1]+body+source[z:],'utf-8')
    reference=original.replace('this.','loc.').replace('var _loc17_:Tile','var _loc17_:*').rstrip()
    template=(B/'fixtures/SceneFogChecks.as.template').read_text('utf-8')
    (B.parent/'src/tests/SceneFogChecks.as').write_text(template.replace('@@REFERENCE@@',reference),'utf-8')

def build():
    prepare()
    ff('-importScript',HOST,OUT/'donor.swf',OUT/'source')
    for variant,input in [('original',HOST),('donor',OUT/'donor.swf')]:
        ff('-format','script:pcode','-selectclass','fe.loc.Location','-export','script',OUT/(variant+'-pcode'),input)
    shutil.copy2(B/'generated/motion-host-incremental/pfe.xml',OUT/'base.xml')
    methods.GEN=OUT
    path,index,key=methods.plan_method('fe.loc.Location','lighting')
    (OUT/'replace.txt').write_text('\n'.join(['fe.loc.Location',str(path),str(index)])+'\n','utf-8')
    ff('-replace',HOST,OUT/'pfe.swf',OUT/'replace.txt')
    ff('-swf2xml',OUT/'pfe.swf',OUT/'pfe.xml')
    (OUT/'methods.json').write_text(json.dumps([key]),'utf-8')
    # Compare all other named methods, all non-renderer layouts and pool entries.
    auditBase=OUT/'audit-base';auditBase.mkdir(exist_ok=True)
    shutil.copy2(HOST,auditBase/'pfe.swf');shutil.copy2(OUT/'base.xml',auditBase/'host.xml')
    subprocess.run([sys.executable,str(B/'renderer-audit.py'),str(OUT/'pfe.swf'),str(auditBase),str(OUT/'methods.json')],check=True)

if __name__=='__main__':
    build() if '--build' in sys.argv else prepare()
