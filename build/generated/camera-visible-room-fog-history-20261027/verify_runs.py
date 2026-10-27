"""Read-only input/clock verification; write a new receipt, never alter raw runs."""
from pathlib import Path
import argparse,collections,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fog_history_verifier',HERE.parent/'camera-visible-room-scout-20261027/verify_batch.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def fog_stats(state):
    cells=state['localCells']
    return dict(positive=sum(c['visi']>0 for c in cells),sumVisibility=sum(c['visi'] for c in cells),
        pixels=collections.Counter(str(c['mask']) for c in cells),player=state['player'],relightTicks=state['relightTicks'])

def compare_cells(normal,scene):
    assert len(normal)==len(scene)==1200
    counts=collections.Counter();interior=collections.Counter();examples=[]
    for a,b in zip(normal,scene):
        assert (a['x'],a['y'])==(b['x'],b['y'])
        for k in ['visi','target','opacity','mask','water']:
            if a[k]!=b[k]:
                counts[k]+=1
                if 0<a['x']<47 and 0<a['y']<24:interior[k]+=1
                if len(examples)<12:examples.append(dict(x=a['x'],y=a['y'],field=k,normal=a[k],scene=b[k]))
    return dict(differentCellsByField=counts,interiorDifferentByField=interior,examples=examples)

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);p.add_argument('--normal');p.add_argument('--out',required=True,type=Path);args=p.parse_args()
    assert not args.out.exists()
    out=dict(runs=[],deployed=False,performanceAcceptance=False,preflightFailures=[]);raws={}
    for mode,name in [('scene',args.scene),('normal',args.normal)]:
        if not name:continue
        rec,raw=base.verify(name,HERE);out['runs'].append(rec);raws[mode]=raw
        t=raw['cameraRaster'];rec['fogStats']={k:fog_stats(t[k]) for k in ['fogTimingStart','fogTimingEnd']}
        rec['localFogEndpointsEqual']=t['fogTimingStart']['localCells']==t['fogTimingEnd']['localCells']
        rec['longIntervalsOver100ms']=sum(dt>100 for dt in t['framesMs'])
        rec['maxIntervalMs']=max(t['framesMs'])
    for name in [HERE.name+'-scene-r1',HERE.name+'-normal-r1',HERE.name+'-normal-r2']:
        folder=base.E/name
        if not (folder/'runner-failure.json').exists():continue
        f=base.read(folder/'runner-failure.json')
        assert not f['complete'] and not f['deployed'] and not (folder/'storage/result.json').exists() and not (folder/'process-policy.json').exists()
        out['preflightFailures'].append(dict(name=name,error=f['error'],sha256=base.sha(folder/'runner-failure.json'),airStarted=False))
    if len(raws)==2:
        a=raws['normal']['cameraRaster'];b=raws['scene']['cameraRaster']
        assert out['runs'][0]['probeSHA256']==out['runs'][1]['probeSHA256']
        assert a['referenceSite']['tileHash']==b['referenceSite']['tileHash']==3026506315
        for x,y in zip(a['windows'],b['windows']):
            assert x['condition']==y['condition'] and len(x['vx'])==len(y['vx'])==120
            assert [v-5760 for v in y['cameraX']]==x['cameraX'] and [v-3000 for v in y['cameraY']]==x['cameraY']
            assert [v+5760 for v in y['vx']]==x['vx'] and [v+3000 for v in y['vy']]==x['vy']
        out['comparison']=dict(offset=[5760,3000],all960CameraCoordinates=True,
            timingStart=compare_cells(a['fogTimingStart']['localCells'],b['fogTimingStart']['localCells']),
            timingEnd=compare_cells(a['fogTimingEnd']['localCells'],b['fogTimingEnd']['localCells']),
            views=[compare_cells(x['fog']['localCells'],y['fog']['localCells']) for x,y in zip(a['pixels'],b['pixels'])])
    out['limit']='Endpoint equality does not prove no intervening bitmap writes. Random decoration and off-room world differ. Private-desktop ENTER_FRAME data is not physical-display FPS; spikes are retained.'
    args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(runs=len(out['runs']),sha256=base.sha(args.out),comparison=out.get('comparison')),ensure_ascii=False))
if __name__=='__main__':main()
