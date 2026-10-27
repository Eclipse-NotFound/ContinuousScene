"""Verify actual camera/actor travel rather than treating input requests as motion."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def audit(name):
    p=MOD/'knowledge/experiments/evidence'/name/'storage/result.json';r=json.loads(p.read_text('utf-8-sig'))
    assert len(r['samples'])==20
    rows=[]
    for i,s in enumerate(r['samples']):
        motion=s['nativeInputMotion'];states=s['farParking']
        assert motion['samples']==len(states)==60 and motion['movingSamples']>0
        xs=[v['vx'] for v in states];ys=[v['vy'] for v in states]
        assert max(xs)>min(xs) and motion['maxX']>motion['minX']
        rows.append(dict(index=i,cameraXRange=[min(xs),max(xs)],cameraYRange=[min(ys),max(ys)],
            actorXRange=[motion['minX'],motion['maxX']],actorYRange=[motion['minY'],motion['maxY']],
            movingActorSamples=motion['movingSamples'],playerShots=s['playerShotFrames'],enemyShots=s['enemyShotFrames']))
    return dict(name=name,resultSHA256=sha(p),rawOK=r['ok'],error=r['error'],viewport=r['viewport'],
        actualHorizontalCameraMotion=True,allWindowsVerticalCameraStatic=all(x['cameraYRange'][0]==x['cameraYRange'][1] for x in rows),
        movingActorSamples=sum(x['movingActorSamples'] for x in rows),playerShots=sum(x['playerShots'] for x in rows),enemyShots=sum(x['enemyShots'] for x in rows),
        windows=rows,notVerticalJumpAcceptance=True,deployed=False)
if __name__=='__main__':
    for name in sys.argv[1:]:
        result=audit(name);out=HERE/(name+'-movement.json');assert not out.exists()
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='windows'},ensure_ascii=False))
