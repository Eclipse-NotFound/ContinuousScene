"""Write evidence summaries once; never rewrite the frozen test records."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
def main():
    runs=json.loads((HERE/'runs-review.json').read_text('utf-8'))['runs']
    explanations=[
        '进入后立即固定姿态，路线预备期间24个时间轴仍变化；只看isPlaying不足。65像素检查图释放，0纹理/0计时，恢复审计失败保留。',
        '移动固定姿态到原生预备之后，遍历遇到空显示节点。只停止/恢复1个播放者，65像素图释放，0纹理/0计时，清理通过。',
        '加入空槽核验，本轮未遇空槽，不能声称前轮空值原因已证实。遍历7444节点/1670多帧，21显式播放者停止后，24个原isPlaying=false的子轴仍变帧。7纹理、8临时图、65像素图释放，0计时；恢复失败保留。',
        '固定8间隔观察识别24个隐式播放者，47个被持有者保持稳定。候选首视角92738像素差异，604像素RGB≥3，最大112/alpha0；原生恢复精确。已查看完整PNG，发光边缘有颜色差异，非合格候选。80像素图/8临时图/7纹理释放，47个通过play恢复；隐式播放标志可能由false变true，不宣称内部状态原样恢复。0计时。',
        '归因计时前，两个bloat_bulk_896从55帧被自身帧脚本重新播放到3帧。参考源已核：frame55调用gotoAndPlay(2)，frame1随机gotoAndPlay。0计时；47个持有者中45个恢复，另2个已被外部重播，未强行覆盖。65像素图/8临时图/7纹理释放，原始恢复失败保留。',
        '加入一次固定帧脚本消化与下一间隔核验。本轮分支处理数为0，不能据此说frame55重停分支已实测。实际固定43个播放者（其中25个隐式播放者），计时无后续时间轴变化。全路线2392×1444，7纹理22,626,944字节，8临时位图/260像素检查图/7纹理释放，43个播放者恢复。'
    ]
    for row,explanation in zip(runs,explanations):
        folder=HERE.parent/row['name'].removesuffix('-r1')
        path=folder/'RESULTS.md';assert not path.exists()
        text=f"# {row['name']}\n\n{explanation}\n\n"
        text+=f"冻结源 `{row['frozenSource']}`，探针 `{row['probeSHA256']}`，自有AIR {row['pid']} 已结束。独立复核526正式文件、13运行库、86源及脚本/编译器输入保持。\n\n"
        text+=f"原始结果 ok={row['originalOK']}，完整计时间隔 {row['frames']}，清理 restored={row['cleanup']['restored']}；错误 `{row['trialErrors']}`。失败不改判。\n\n"
        if row['complete']:
            text+='| 条件 | 平均区间 ms | 中位数 | P95 | 最大 |\n|---|---:|---:|---:|---:|\n'
            for mode,value in row['arms'].items():text+=f"| {mode} | {value['mean']:.4f} | {value['median']:.1f} | {value['p95']} | {value['maximum']} |\n"
            text+='\n两组移动配对减少16.8917/18.2417ms，平均约59.2%；原生移动相对静止增加18.4292ms，GPU增加0.9667ms。全部960个连续区间保留，106/130ms长帧未去掉。计时八项原生预绘计数零变化。此为ENTER_FRAME间隔，不是物理呈现数或实玩FPS。\n\n'
            text+='**画质仍不合格**：13视角全部visualAccepted=false，RGB最大92–253、alpha0，原生恢复全部精确；18组自然基线检查通过。已查看第5视角完整原生/候选图，无明显大块地形缺失；RGB≥3约2509像素，发光线条和伤害数字附近有差异，其中28像素≥200。数字的像素位置/栅格化差异原因尚未证实，不能归为纯1/255舍入。\n\n'
            text+='**判断**：完整固定世界呈现存在显著代价上限收益，值得继续量动态更新成本；这不证明只有GPU能实现，也不能直接归为纯GPU耗时。世界visible变化可能被回调观察，原生UI与其他回调仍运行。只有固定姿态、预绘路线；实际动画、敌人AI/子弹更新、RV、OS真实混合呈现与长时生命周期都未验。没有部署，RGB2门槛不变。\n\n'
        text+='核对依据：本目录同名 evidence/storage/result.json、probe-build.json、runner-inputs.json、process-policy.json；统一独立复核见 camera-stage3d-wholeworld-settle-20261027/runs-review.json。正式宿主仍 A796，CS0.9.0仍7F1F。\n'
        path.write_text(text,'utf-8')
    print('Wrote six result summaries, preserving all original failures')
if __name__=='__main__':main()
