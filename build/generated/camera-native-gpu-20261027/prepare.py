"""Compare native window renderer modes using the same room-axis probe."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-room-axis-baseline-v2-20261027'
spec=importlib.util.spec_from_file_location('native_gpu_room_seed',BASE/'probe_patch.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def one(source,old,new):
    assert source.count(old)==1,(old,source.count(old))
    return source.replace(old,new,1)


def helper_source():
    s=base.helper_source().replace('camera-room-axis-baseline-2','camera-native-gpu-1')
    s=one(s,'require(saved.worldVisible===true,"World must start visible");','''require(saved.worldVisible===true,"World must start visible");
                require(w.mm!=null && w.mm.active===false,"Main menu must be inactive");
                report.nativeMenuChildren=[];
                for(var menuChild:int=0;menuChild<w.main.numChildren;++menuChild) {
                    var menuClass:String=getQualifiedClassName(w.main.getChildAt(menuChild));
                    report.nativeMenuChildren.push({className:menuClass,visible:w.main.getChildAt(menuChild).visible});
                    require(menuClass!="visMainMenu","Actual native menu shutdown required");
                }
                report.airRenderMode=stage.nativeWindow.renderMode;
                report.windowPixelsNotCaptured=true;''')
    return s


def transform(source):
    s=base.transform(source)
    return one(s,'w.mm.active=false;w.newGame(-1,"Scene Motion",{propusk:true});phase=1;',
        'w.mm.mainMenuOff();if(w.mm.active)throw new Error("Native menu shutdown failed");w.newGame(-1,"Scene Motion",{propusk:true});phase=1;')


def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-room-axis-baseline-2','camera-native-gpu-1')
    s=one(s,"assert trial['roomAxis']['continuous'] is (cfg['benchmark']=='scene')", """assert trial['roomAxis']['continuous'] is (cfg['benchmark']=='scene')
    assert trial['airRenderMode'] in ('direct','gpu') and trial['windowPixelsNotCaptured']
    assert trial['nativeMenuChildren'] and all(x['className']!='visMainMenu' for x in trial['nativeMenuChildren'])""")
    s=one(s,'roomAxis=trial[\'roomAxis\'],originalZoom=', "airRenderMode=trial['airRenderMode'],windowPixelsNotCaptured=True,roomAxis=trial['roomAxis'],originalZoom=")
    s=one(s,"parser=argparse.ArgumentParser(description=__doc__)", "parser=argparse.ArgumentParser(description=__doc__)\n    parser.add_argument('--renderer',required=True,choices=['direct','gpu'])")
    s=one(s,'record=dict(version=VERSION,options=options(args.name,args.mode),diagnosticOnly=True,deployed=False)',
        'record=dict(version=VERSION,renderer=args.renderer,options=options(args.name,args.mode),diagnosticOnly=True,deployed=False)')
    s=one(s,"            run_error=None\n            try:m.run_owned(m.parse_args(record['options']),lease)", """            runtime_descriptor=m.RUNTIME/'application.xml'
            before=runtime_descriptor.read_bytes()
            assert before.count(b'<renderMode>direct</renderMode>')==1
            during=before.replace(b'<renderMode>direct</renderMode>',('<renderMode>'+args.renderer+'</renderMode>').encode('ascii'),1)
            assert b'depthAndStencil' not in during
            record['runtimeDescriptor']=dict(beforeSHA256=hashlib.sha256(before).hexdigest().upper(),duringSHA256=hashlib.sha256(during).hexdigest().upper())
            original_process=m.HiddenProcess
            def verify_launch(command,**kwargs):
                assert len(command)==4
                path=Path(command[3]);assert path.parent==m.RUNTIME and path.name.startswith('pfe-modsettings-continuous-motion-') and path.suffix=='.xml'
                text=path.read_text('utf-8-sig')
                assert text.count('<renderMode>'+args.renderer+'</renderMode>')==1
                assert '<id>pfe</id>' not in text and 'depthAndStencil' not in text
                record['launchDescriptor']=dict(path=str(path),text=text,sha256=r.sha(path))
                r.save(folder/'launch-descriptor.json',record['launchDescriptor'])
                return original_process(command,**kwargs)
            run_error=None
            try:
                runtime_descriptor.write_bytes(during);m.HiddenProcess=verify_launch
                m.run_owned(m.parse_args(record['options']),lease)""")
    s=one(s,"            finally:\n                if folder.exists():", """            finally:
                m.HiddenProcess=original_process
                assert runtime_descriptor.read_bytes()==during,'Test descriptor changed externally; retain it for review'
                runtime_descriptor.write_bytes(before)
                assert runtime_descriptor.read_bytes()==before
                record['runtimeDescriptor']['restored']=True
                if folder.exists():""")
    s=one(s,'            summary=summarize(raw)', """            assert actual['application.xml']==record['runtimeDescriptor']['duringSHA256']
            summary=summarize(raw)
            assert summary['airRenderMode']==args.renderer""")
    s=s.replace('ContinuousScene / camera room axes / 01a13816','ContinuousScene / native GPU renderer camera axes / 01a13816')
    s=s.replace('960 native camera axis frames for matched room mode; diagnostic only, no deployment',
        '960 native renderer camera-axis intervals; OS pixels and filter compatibility unverified, no deployment')
    s=one(s,"'Native world stays visible in every interval; static versus axis movement, no rendering optimization.',",
        "'Native world stays visible; compares requested native renderer mode. GPU may omit effects; no visual acceptance.',")
    return s


if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    code=runner_source();ast.parse(code);(HERE/'run.py').write_text(code,'utf-8')
    print('Prepared native direct/GPU mode probe with actual menu shutdown; no build or launch')
