from pathlib import Path
import ast, importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-active-quiet-bands-20261027'
VERSION='camera-visible-room-scout-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('visible_reference_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.desktop.NativeApplication;', '''    import flash.desktop.NativeApplication;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;''')
    s=one(s,'                makeRoute();','                selectReferenceSite();makeRoute();')
    s=one(s,'var offsetX:int=grafon.sceneLarge?3840:0,offsetY:int=grafon.sceneLarge?4000:0;',
      'var offsetX:int=grafon.sceneLarge?report.referenceSite.roomX*1920:0,offsetY:int=grafon.sceneLarge?report.referenceSite.roomY*1000:0;')
    s=one(s,'            var x:int=offsetX+960,y:int=offsetY+600;',
      '            var x:int=Math.round(player.X),y:int=offsetY+Math.max(520,Math.min(700,Math.round(player.Y)-offsetY));')
    s=one(s,'localCenterX:960,localCenterY:600,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000',
      'localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:report.referenceSite.roomX,roomGridY:report.referenceSite.roomY,roomWidth:1920,roomHeight:1000')
    s=one(s,'            checkTransform();guard();','''            checkTransform();guard();
            var px:Number=player.X+cam.vx,py:Number=player.Y+cam.vy;
            require(px>=50 && px<stage.stageWidth-50 && py>=120 && py<stage.stageHeight-50,"Player outside verified camera view");
            require(cam.vx==-(point.x-stage.stageWidth/2) && cam.vy==-(point.y-stage.stageHeight/2-100),"Room camera clamped during reference route");''')
    s=one(s,'                var a:BitmapData=capture(),b:BitmapData=capture();', '''                var a:BitmapData=capture(),b:BitmapData=capture();
                result.visibleCoverage=coverage(a);savePNG("reference-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.30,"Reference camera has insufficient visible world content");''')
    extra=(HERE/'site-methods.as.inc').read_text('utf-8-sig')
    s=one(s,'        private function makeRoute():void {',extra+'\n        private function makeRoute():void {')
    s=s.replace('y:y+48','y:y+24').replace('y:y-48','y:y-24')
    return s
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace(base.VERSION,VERSION).replace('active quiet frame bands','visible ordinary room reference')
    s=one(s,"    if mode=='normal':",'''    values=[v for v in values if v not in ('--encounter','--fixed-enemies','--native-input-motion','--native-sprint','--player-fire','--combat-route')]
    i=values.index('--combat-route-length');del values[i:i+2]
    if mode=='normal':''')
    s=one(s,"'--native-room-y','4'","'--native-room-y','3'")
    s=one(s,'def options(name,mode):','def options(name,mode,room_x,room_y):')
    s=one(s,"'--native-room-x','2','--native-room-y','3'","'--native-room-x',str(room_x),'--native-room-y',str(room_y)")
    s=one(s,"    group=parser.add_mutually_exclusive_group(required=True)","    parser.add_argument('--room-x',type=int,default=2);parser.add_argument('--room-y',type=int,default=3)\n    group=parser.add_mutually_exclusive_group(required=True)")
    s=one(s,'options(args.name,args.mode)','options(args.name,args.mode,args.room_x,args.room_y)')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared visible same-room reference with collision checked placement, full intervals and screenshots')
