"""Stage only this review; leave the pre-existing author edits unstaged."""
from pathlib import Path
import hashlib, json, subprocess
ROOT=Path(__file__).resolve().parents[5]
REPO=ROOT/'mods/ContinuousScene'
def git(*args, data=None):
    return subprocess.run(['git','-C',str(REPO),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
if git('diff','--cached','--name-only').strip():raise RuntimeError('Existing staged work; do not overwrite it')
memory='''
> 2026-11-01 当前迭代审核：正式仍 CA94/D8A/FE3，RV实际为AEA30314；本轮未覆盖任何正式产物。新增单位显隐在原版UnitSpectre上复现 false→true，A80阴性对照保持false，第四层不能判“零视觉影响”。4轮12684间隔：补绘稳定后横纵移动仍增加呈现成本；大窗物体层隐藏4/4变快，光照层无稳定收益；35次>100ms中32次伴随明显堆回落。12/12分配采样又指向炮塔gotoAndStop/构造子显示对象/FocusManager链及TDFC快照。旧“纯镜头基本无成本、主要是战斗”的排他结论不再沿用。详见 [迭代审查](../knowledge/experiments/camera-iteration-review-20261101.md)。调查未等于修复：优先安全撤掉无条件显隐，再验证物体呈现、缩放地形和回收尾部；不直接复活旧质量/sleep/炮塔候选。所有本轮自有实例和登记已结束；他人 SceneRenderChecks、MEMORY/journal原修改与报告均保留。

'''
journal='''## 2026-11-01 — 当前四层迭代审核与镜头归因（本会话）

- 审核实际部署 CA94 及 A80→四层配方；没有回退/部署正式文件。确认UnitSpectre原生隐藏被sceneTick覆盖，A80对照不变。
- 4轮12684有效间隔，玩家站定，关闭RV/WB/LAD，预绘稳定后仍有横纵呈现成本；小窗现有合并不启用，大窗合并启用仍有物体显示树成本。大窗光照层未见稳定贡献。
- 35次>100ms中32次伴随明显内存回落；12/12调用栈窗口有效，炮塔重建/FocusManager链与TDFC快照列为候选，不能按分配计数直接宣称收益。276/304/537ms剩余长停顿未归因。
- 纠正旧探针菜单显示层残留、阶段45计时像素哈希、30fps上限及缺少正式纵移测量等证据边界；失败准备原件保留。
- 报告：knowledge/experiments/camera-iteration-review-20261101.md；配方camera-review-v4/v5/v6-20261101。技能反馈已登记全局台账。所有自有测试/登记结束；他人工作树不纳入本提交。

'''
notes={'state/MEMORY.md':memory,'state/journal.md':journal}
preserved={}
for rel,note in notes.items():
    p=REPO/rel;before=p.read_bytes();preserved[rel]=hashlib.sha256(before).hexdigest()
    if '当前迭代审核' in before.decode('utf-8-sig') and rel.endswith('MEMORY.md'):raise RuntimeError('Review note already present')
    newline='\r\n' if b'\r\n' in before else '\n'
    def insert(raw):
        eol='\r\n' if b'\r\n' in raw else '\n'
        addition=note.replace('\n',eol).encode('utf-8')
        if rel.endswith('MEMORY.md'):
            split=raw.index(b'\n')+1
            return raw[:split]+addition+raw[split:]
        return addition+raw
    after=insert(before);p.write_bytes(after)
    staged=insert(git('show','HEAD:'+rel))
    blob=git('hash-object','-w','--stdin',data=staged).decode().strip()
    git('update-index','--cacheinfo','100644,'+blob+','+rel)
    # Removing only our exact insertion must reproduce the other author's bytes.
    add=note.replace('\n',newline).encode('utf-8')
    assert after.replace(add,b'',1)==before
paths=['knowledge/experiments/camera-iteration-review-20261101.md','knowledge/experiments/camera-review-skill-feedback-20261101.md']
for version in (4,5,6):
    base=Path('build/generated')/('camera-review-v'+str(version)+'-20261101')
    for name in ['ContinuousSceneMotionMod.as','CameraProbePlatform.as','ProbeDoc.as','FrameCostProbe.as','compiler.xml','work.py','build.json','link.xml']:
        if (REPO/base/name).is_file():paths.append((base/name).as_posix())
base=Path('build/generated/camera-review-20261101')
for name in ['analyze.py','allocation_summary.py','finalize_review.py']:paths.append((base/name).as_posix())
for run in ['camera-review-current-small-r4-20261101','camera-review-a80-small-r1-20261101','camera-review-current-large-r5-20261101','camera-review-current-small-r5-20261101','camera-review-current-alloc-r6-20261101']:
    base=Path('knowledge/experiments/evidence')/run
    for name in ['storage/result.json','review-summary.json','allocation-summary.json','inputs.json','review-inputs.json','loader-check.json','process-policy.json']:
        if (REPO/base/name).is_file():paths.append((base/name).as_posix())
git('add','-f','--',*paths)
print(json.dumps({'stagedOwnPaths':len(paths)+2,'preservedWorkingTreeBytesBefore':preserved,'stagedStatus':git('diff','--cached','--stat').decode('utf-8','replace')},ensure_ascii=False))
