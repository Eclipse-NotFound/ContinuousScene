"""Same-window native raster quality attribution, never production quality policy."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-native-gpu-20261027'
VERSION='camera-native-quality-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-native-gpu-1',VERSION)
    s=one(s,'import flash.display.Stage;', '''import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;''')
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,1,2,3,4,5,5,4,3,2,1,0];')
    s=one(s,'look:w.ctr.keyLook,zoom:w.ctr.keyZoom,frameRate:stage.frameRate,','look:w.ctr.keyLook,zoom:w.ctr.keyZoom,frameRate:stage.frameRate,quality:stage.quality,')
    s=s.replace('measurementFrames:960','measurementFrames:1440')
    s=one(s,'row.workMs.push(pending.workMs);','row.quality.push(pending.quality);row.workMs.push(pending.workMs);')
    s=one(s,'try {stage.frameRate=saved.frameRate;}', 'try {stage.quality=saved.quality;stage.frameRate=saved.frameRate;}')
    s=one(s,'stage.frameRate==saved.frameRate,"Camera/pause/frameRate restore mismatch"', 'stage.frameRate==saved.frameRate && stage.quality===saved.quality,"Camera/pause/frameRate/quality restore mismatch"')
    s=one(s,'require(stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content");',
        'require(stage.stageWidth==2032 && stage.stageHeight==1084,"Native quality comparison requires 2032x1084 content");')
    s=one(s,'var x:int=offsetX+960,y:int=offsetY+600;', 'var x:int=offsetX+960,y:int=offsetY+400;')
    s=one(s,'localCenterX:960,localCenterY:600,', 'localCenterX:960,localCenterY:400,')
    s=one(s,'var condition:int=order[segment];age=0;', 'var condition:int=order[segment];age=0;stage.quality=["HIGH","MEDIUM","LOW"][int(condition/2)];')
    s=one(s,'mode:["native-static","native-horizontal","native-vertical","native-combined"][condition]',
        'mode:["high-static","high-moving","medium-static","medium-moving","low-static","low-moving"][condition]')
    s=one(s,'hidden:false,moving:condition!=0,','hidden:false,moving:condition%2==1,')
    s=one(s,'worldVisible:[],windowVisible:[],start:snapshot()', 'worldVisible:[],windowVisible:[],quality:[],start:snapshot()')
    s=one(s,'var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};','var point:Object=target;')
    s=one(s,'pending={vx:cam.vx,', 'pending={quality:stage.quality,vx:cam.vx,')
    s=one(s,'var a:BitmapData=capture(),b:BitmapData=capture();\n                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;\n                require(result.passed,"Native consecutive captures changed");', '''require(stage.quality==="HIGH","Pixel check must begin in HIGH");
                var a:BitmapData=capture(),b:BitmapData=capture();result.nativeRepeat=compare(a,b);
                stage.quality="MEDIUM";var medium:BitmapData=capture();result.medium=compare(a,medium);
                stage.quality="LOW";var low:BitmapData=capture();result.low=compare(a,low);
                stage.quality="HIGH";var back:BitmapData=capture();result.restored=compare(a,back);
                if(index==0) {savePNG(a,"quality-high.png");savePNG(medium,"quality-medium.png");savePNG(low,"quality-low.png");savePNG(back,"quality-restored.png");}
                result.passed=result.nativeRepeat.equal && result.restored.equal;
                require(result.passed,"Native HIGH repeat/restore changed");''')
    s=one(s,'private function capture():BitmapData {', '''private function savePNG(b:BitmapData,name:String):void {
            var path:File=File.applicationStorageDirectory.resolvePath(name);
            var stream:FileStream=new FileStream();
            try {stream.open(path,FileMode.WRITE);stream.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
        }
        private function capture():BitmapData {''')
    s=s.replace('World display stays visible in every arm; compare only native camera axes.',
        'World and Stage stay the same; quality deliberately changes raster precision for attribution, not production approval.')
    return s
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-native-gpu-1',VERSION)
    s=s.replace("'--window-width','1296'","'--window-width','2048'").replace("'--window-height','759'","'--window-height','1123'")
    s=s.replace("choices=['normal','scene']", "choices=['scene']")
    start=s.index('def summarize(raw):');end=s.index('\ndef main():',start)
    s=s[:start]+SUMMARY+'\n\n'+s[end:]
    s=s.replace('ContinuousScene / native GPU renderer camera axes / 01a13816','ContinuousScene / native quality attribution / 01a13816')
    s=s.replace('960 native renderer camera-axis intervals; OS pixels and filter compatibility unverified, no deployment',
        '1440 same-window quality intervals; visual differences retained, no production quality reduction or deployment')
    return s
SUMMARY='''def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config'];trial=raw['cameraRaster'];cleanup=raw['cameraRasterCleanup']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert trial['roomAxis']['continuous'] and trial['airRenderMode']=='direct' and trial['windowPixelsNotCaptured']
    assert trial['stage']==dict(width=2032,height=1084,quality='HIGH')
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==25
    assert trial['pixelsValid'] and len(trial['pixels'])==5
    for check in trial['pixels']:
        assert check['passed']
        for key in ('nativeRepeat','restored'):
            c=check[key];assert c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==12 and len(trial['framesMs'])==len(trial['sampleAtMs'])==1440
    previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    names=['high-static','high-moving','medium-static','medium-moving','low-static','low-moving']
    initial=trial['timingStart']
    for i,(row,condition) in enumerate(zip(trial['windows'],[0,1,2,3,4,5,5,4,3,2,1,0])):
        assert row['index']==i and row['condition']==condition and row['mode']==names[condition]
        assert row['startAtMs']==previous and row['hidden'] is False and row['moving'] is (condition%2==1)
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','quality'):assert len(row[key])==120,key
        assert all(x is True for x in row['worldVisible']+row['windowVisible'])
        assert set(row['quality'])=={['HIGH','MEDIUM','LOW'][condition//2]}
        assert (len(set(row['vx']))>1)==row['moving'] and (len(set(row['vy']))>1)==row['moving']
        assert all(v==initial['gg'] for v in row['gg'])
        for scene in row['scene']:
            for key in ('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced'):assert scene[key]==initial['scene'][key]
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,mode=row['mode'],frame=metric(row['framesMs']),work=metric(row['workMs'])))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in names}
    pairs=[dict(baseIndex=a,candidateIndex=b,candidateMinusBaseMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in [(1,3),(1,5),(10,8),(10,6)]]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        airRenderMode='direct',windowPixelsNotCaptured=True,roomAxis=trial['roomAxis'],rows=rows,arms=arms,pairs=pairs,
        viewport=raw['viewport'],world=raw['world'],pixels=trial['pixels'],cleanup=cleanup,
        limits=['Paused simulation, live timelines; not gameplay FPS.','Deliberately different raster precision; not visual acceptance.',
            'Same original Stage; no reparenting.','All transition and observation costs retained.'])
'''
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared native HIGH/MEDIUM/LOW attribution; no production edits')
