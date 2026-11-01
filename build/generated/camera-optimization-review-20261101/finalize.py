"""Archive only this task; preserve the other author's unstaged edits byte for byte."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPO = ROOT / 'mods/ContinuousScene'
START = '<!-- camera-optimization-20261101 -->'
END = '<!-- /camera-optimization-20261101 -->'


def git(*args, data=None):
    return subprocess.run(['git', '-C', str(REPO), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


memory = '''<!-- camera-optimization-20261101 -->
> 2026-11-01 后继优化已实测：正式宿主 **9D8662F6**（14:58从CA94只撤掉sceneTick无条件单位显隐，前三层A2/预绘预算保留）；CS **D8A68A4C**、WB **FE3E7A84**、RV **AEA30314**、RC **69060487**等14模组组合保持。回执：build/generated/camera-object-clip-v7-20261101/visibility-fix-deployment.json。原生UnitSpectre隐藏复验通过。这是显隐回归修复，不是已证实性能提升；重启生效。下方旧安装表与迭代条目是历史记录，当前以本段为准。
>
> 9次独立游戏运行，7次时序实验15740个有效间隔；所有自有实例/登记已结束。整层裁剪、物体缓存、炮塔guard、既有地形节点缓存均无稳定收益。旧局部phase在真实0.658333缩放alpha失败；禁止凭旧2/3测试放行。屏幕像素缓存v13两窗十图合格，但小窗28.018→27.202ms仅约2.9%且长停顿更多，大窗35.190→39.166ms更慢，停止、不部署。没有新性能候选进入正式文件。炮塔goto栈可能执行全局帧脚本，不等于炮塔重建；90帧片段与GC周期错位不能当P99收益。
>
> 远处活动范围旧候选缺少内部警戒/延后攻击保护，未运行或部署；保持追击和屏外命中。性能目标尚未达到近原版。详见 [本轮报告](../knowledge/experiments/camera-optimization-followup-20261101.md) 及 generated/camera-optimization-review-20261101/summary.json。后续不重复上述已停止路线；需要新的整帧成本证据，而不是扩大预绘预算或放宽画面要求。他人的SceneRenderChecks、既有状态和13份报告保持。
<!-- /camera-optimization-20261101 -->'''

journal = '''<!-- camera-optimization-20261101 -->
## 2026-11-01 — 撤回单位显隐回归；九轮镜头候选复验

- 14:58根宿主CA94→9D8662F6，只撤无条件visible赋值，A2/预绘环/48ms预算保留；UnitSpectre真实原生隐藏验证、备份、相同字节部署及回读完成。CS D8A/WB FE3/RV AEA/RC6906等14模组未改。
- 9次私有静音游戏运行、7轮时序15740有效间隔，已全部退出并结束登记。v9像素失败保留；v11相位搜索完成但无相位达标。
- 裁剪、物体层缓存、炮塔guard、地形节点cache无稳定整帧收益；不把GC相位错位或局部观察带下降当产品提速。
- 屏幕分辨率缓存v13十视角：小窗最大RGB1/alpha0，大窗RGBA精确；但小窗仅约2.9%且尾部更差，大窗约11.3%退步，不部署。初版v12与全部负结果保留。
- 旧全类别缩活动范围方案未补内部AI保护，仅静态审查，不重新运行。追击/屏外命中/现有休眠规则保持。仍未达到近原版。
- 业务报告knowledge/experiments/camera-optimization-followup-20261101.md，汇总配方build/generated/camera-optimization-review-20261101；同任务技能反馈追加原报告，不重复登记。仅归档本轮，自有marker以外状态和他人SceneRenderChecks/报告字节保持。
<!-- /camera-optimization-20261101 -->'''


def main():
    if git('diff', '--cached', '--name-only').strip():
        raise RuntimeError('Existing staged edits: do not overwrite')
    evidence = json.loads((HERE/'summary.json').read_text('utf-8'))
    assert not evidence['missing'] and evidence['totalIntervals'] == 15740
    assert evidence['currentFormalModsMatch']
    assert sha(ROOT/'pfe.swf') == evidence['currentRootHostSHA256']
    foreign = {'src/tests/SceneRenderChecks.as': sha(REPO/'src/tests/SceneRenderChecks.as')}
    for rel in git('ls-files', '--others', '--exclude-standard', '--',
                   'knowledge/experiments').decode('utf-8').splitlines():
        if rel != 'knowledge/experiments/camera-optimization-followup-20261101.md':
            foreign[rel] = sha(REPO/rel)
    preserved = {}
    for rel, note in [('state/MEMORY.md', memory), ('state/journal.md', journal)]:
        path = REPO/rel
        old = path.read_bytes()
        assert old.count(START.encode()) == old.count(END.encode()) == 1
        a, b = old.index(START.encode()), old.index(END.encode())+len(END)
        newline = '\r\n' if b'\r\n' in old else '\n'
        replacement = note.replace('\n', newline).encode('utf-8')
        new = old[:a]+replacement+old[b:]
        assert new[:a] == old[:a] and new[a+len(replacement):] == old[b:]
        path.write_bytes(new)
        preserved[rel] = dict(before=hashlib.sha256(old).hexdigest(),
                              after=sha(path), outsideMarkerUnchanged=True)
        head = git('show', 'HEAD:'+rel)
        assert START.encode() not in head
        eol = b'\r\n' if b'\r\n' in head else b'\n'
        addition = eol+note.replace('\n', eol.decode()).encode()+eol+eol
        pos = head.index(b'\n')+1 if rel.endswith('MEMORY.md') else 0
        staged = head[:pos]+addition+head[pos:]
        blob = git('hash-object', '-w', '--stdin', data=staged).decode().strip()
        git('update-index', '--cacheinfo', '100644,'+blob+','+rel)
    paths = ['knowledge/experiments/camera-optimization-followup-20261101.md',
             'knowledge/experiments/camera-review-skill-feedback-20261101.md']
    recipes = ['camera-object-clip-v7-20261101', 'camera-object-cache-v8-20261101',
               'camera-turret-guard-r2-20261101', 'camera-scaled-fill-v9-20261101',
               'camera-terrain-cache-v10-20261101', 'camera-phase-search-v11-20261101',
               'camera-screen-cache-v12-20261101', 'camera-screen-cache-v13-20261101',
               'camera-optimization-review-20261101']
    for recipe in recipes:
        base = REPO/'build/generated'/recipe
        for path in base.iterdir():
            if path.is_file() and (path.suffix in ['.as', '.py', '.json', '.pcode']
                                  or path.name in ['compiler.xml', 'compiler.log', 'link.xml']):
                paths.append(path.relative_to(REPO).as_posix())
        if (base/'failed-compile-1').exists():
            paths.extend(p.relative_to(REPO).as_posix()
                         for p in (base/'failed-compile-1').iterdir() if p.is_file())
    for run in evidence['runs']:
        base = REPO/'knowledge/experiments/evidence'/run['name']
        for name in ['storage/result.json', 'optimization-summary.json', 'inputs.json',
                     'review-inputs.json', 'loader-check.json', 'process-policy.json']:
            if (base/name).exists():
                paths.append((base/name).relative_to(REPO).as_posix())
    for rel, expected in foreign.items():
        assert sha(REPO/rel) == expected, ('Foreign work changed', rel)
    git('add', '-f', '--', *paths)
    archived = {'preservedState': preserved, 'foreignFingerprints': foreign,
                'stagedPaths': len(paths)+2,
                'archivedBytes': sum((REPO/p).stat().st_size for p in paths)}
    (HERE/'archive.json').write_text(json.dumps(archived, ensure_ascii=False, indent=2), 'utf-8')
    git('add', '-f', '--', (HERE/'archive.json').relative_to(REPO).as_posix())
    print(json.dumps(archived, ensure_ascii=False))


if __name__ == '__main__':
    main()
