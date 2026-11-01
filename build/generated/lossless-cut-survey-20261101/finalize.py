"""Stage only this survey, with state additions separated from existing edits."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
REPO=ROOT/'mods/ContinuousScene'
sys.path.insert(0,str(ROOT/'mods/ModLoader/tools'))
from test_registry import Registry,ACTIVE
START='<!-- lossless-cut-survey-20261101 -->'
END='<!-- /lossless-cut-survey-20261101 -->'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def git(*args,data=None):
    return subprocess.run(['git','-C',str(REPO),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)

def main():
    assert not git('diff','--cached','--name-only').strip(),'Preserve existing staging'
    summary=json.loads((HERE/'summary.json').read_text('utf-8'))
    manifest={k.replace('\\','/'):v for k,v in json.loads((HERE/'archive.json').read_text('utf-8')).items()}
    assert summary['formalUnchanged'] and summary['foreignSourceUnchanged']
    assert sha(ROOT/'pfe.swf')==summary['host']
    assert all(sha(ROOT/k)==v for k,v in summary['formalMods'].items())
    assert all(sha(REPO/k)==v for k,v in manifest.items())
    active=[r for r in Registry().status() if r['state'] in ACTIVE and '01a13816' in r['owner']]
    assert not active,active
    failures=sum(not r['ok'] for r in summary['runs'])
    intervals=summary['totalIntervals'];runs=len(summary['runs'])
    memory=f'''{START}
> 2026-11-01 无损切口普查：本轮正式文件未变，宿主仍 **9D8662F6**、CS D8A、WB FE3、RV AEA、RC6906等14模组保持；前轮显隐回归修复仍在。完成{runs}次隔离游戏运行，含{failures}次保留的预热超时，计时共{intervals}有效间隔；另有一次排队超时未启动。所有自有实例/登记已结束。
>
> 已核对地形、物体显示树/缓存、时间轴/焦点、环境查询、AI快照与调度、其它模组分配、GC和运行库。快照复用、不同中性分组及缓存、主动GC和新版运行库未取得可部署的稳定明显收益；没有新性能产物进入正式安装。各自像素/时序边界与失败见[普查报告](../knowledge/experiments/lossless-cut-survey-20261101.md)及build/generated/lossless-cut-survey-20261101/summary.json。
>
> 保持原画质、原生隐藏、追击和屏外命中。普通Box本已cacheAsBitmap；桌面cacheAsBitmapMatrix不支持，不能重复包装成新切口。120fps容量/离屏像素不能冒充正式30fps/原生Stage验收。不声称已接近原版或数学意义耗尽所有无损空间；新渲染实现仍需新的整帧收益和等价证据，不能仅换参数重跑已否定实现。他人状态/源码/报告保留。
{END}'''
    journal=f'''{START}
## 2026-11-01 — 无视觉降级切口普查与候选淘汰

- 逐项复核既有绘制、镜头、调度、分配证据，新增TDFC双快照、物体同序分组/大小/原生组缓存、GC收尾、两版AIR运行库对照。{runs}次实际运行、{intervals}有效间隔；{failures}次预热超时及一次未启动排队超时原件保留。
- 快照组件节省约0.08ms但整帧更差；中性分组方向/窗口不一致；两档GC收尾均值变化不足1%、尾部更差；新版运行库经原版恢复对照未证明稳定收益。分组/缓存终局见普查报告；不降低质量或改敌人行为换帧率。
- 未部署新性能候选，根9D8662F6与14正式模组指纹保持。全部自有测试登记结束，无玩家或他人进程操作。
- 报告knowledge/experiments/lossless-cut-survey-20261101.md；冻结源、原始结果、环境和汇总位于build/generated/lossless-cut-survey-20261101及manifest列出的本轮目录。剩余限制明确保留：尚未达到近原版，未证明所有可能的无损重构均无收益。
{END}'''
    foreign={'src/tests/SceneRenderChecks.as':sha(REPO/'src/tests/SceneRenderChecks.as')}
    for name in git('ls-files','--others','--exclude-standard','--','knowledge/experiments').decode('utf-8').splitlines():
        if name!='knowledge/experiments/lossless-cut-survey-20261101.md':foreign[name]=sha(REPO/name)
    preserved={}
    for rel,note in [('state/MEMORY.md',memory),('state/journal.md',journal)]:
        path=REPO/rel;old=path.read_bytes();assert START.encode() not in old
        def insert(raw):
            eol=b'\r\n' if b'\r\n' in raw else b'\n'
            pos=raw.index(b'\n')+1 if rel.endswith('MEMORY.md') else 0
            addition=eol+note.replace('\n',eol.decode()).encode('utf-8')+eol+eol
            return raw[:pos]+addition+raw[pos:]
        new=insert(old);path.write_bytes(new)
        preserved[rel]={'beforeSHA256':hashlib.sha256(old).hexdigest().upper(),'afterSHA256':sha(path),'preexistingBytesRetained':True}
        staged=insert(git('show','HEAD:'+rel))
        blob=git('hash-object','-w','--stdin',data=staged).decode().strip()
        git('update-index','--cacheinfo','100644,'+blob+','+rel)
    attributes=REPO/'.gitattributes';old=attributes.read_bytes()
    families=sorted(set(Path(k).parts[2] for k in manifest if k.startswith('build/generated/')))
    families.append(HERE.name)
    lines=['','# 2026-11-01 lossless survey: preserve exact diagnostic inputs.']
    lines += ['build/generated/'+name+'/** -text whitespace=cr-at-eol' for name in families]
    evidence_runs=sorted(set(Path(k).parts[3] for k in manifest if k.startswith('knowledge/experiments/evidence/')))
    lines += ['knowledge/experiments/evidence/'+name+'/** -text whitespace=cr-at-eol,-blank-at-eof' for name in evidence_runs]
    lines += ['knowledge/experiments/evidence/'+name+'/stderr.log whitespace=cr-at-eol,-blank-at-eof,-blank-at-eol' for name in evidence_runs]
    lines += ['build/generated/camera-lossless-survey-v14-20261101/candidate-src/** whitespace=cr-at-eol,-blank-at-eof,-blank-at-eol']
    lines += ['build/generated/'+name+'/compiler.log whitespace=cr-at-eol,-blank-at-eof' for name in families]
    attributes.write_bytes(old+('\n'.join(lines)+'\n').encode())
    paths=list(manifest)+['.gitattributes','knowledge/experiments/lossless-cut-survey-20261101.md']
    paths += [p.relative_to(REPO).as_posix() for p in HERE.iterdir() if p.is_file()]
    for rel,h in foreign.items():assert sha(REPO/rel)==h,rel
    git('add','-f','--',*paths)
    checked=0
    for rel,h in manifest.items():
        # Frozen data must survive Git's newline rules byte-for-byte.
        assert hashlib.sha256(git('show',':'+rel)).hexdigest().upper()==h,rel
        checked+=1
    git('diff','--cached','--check')
    receipt={'ownActiveRegistryEntries':0,'formalUnchanged':True,'foreignFiles':foreign,
             'preservedState':preserved,'frozenStagedFiles':checked,'frozenBytesExact':True,
             'diagnosticIntervals':intervals,'performanceTargetAchieved':False,
             'stagedPaths':len(git('diff','--cached','--name-only').splitlines())+1}
    write(HERE/'final-checks.json',receipt)
    git('add','-f','--',(HERE/'final-checks.json').relative_to(REPO).as_posix())
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('foreignFiles','preservedState')}))
if __name__=='__main__':main()
