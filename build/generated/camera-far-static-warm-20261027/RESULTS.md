# 延后筛选仍有多帧模型变化

证据camera-far-static-warm-20261027-r1；冻结641f180fcc72491391335f6bc47fccee，AIR65428退出。
909个远处根，筛选25ms。首视角候选和恢复逐像素精确，实际PNG已查看：场景、战斗角色及
界面均存在。第二视角在下一次写入前发现visualBloat0边界51×61变为54×55，仍在路线外。
局部位置检查通过，isPlaying=false没有保证其视觉不动。0帧计时，无性能结论。

1818次可见性赋值=909根隐藏并恢复一次；cleanup.terrainRestored=true，但边界审计仍失败，
cleanup.restored=false保留。旧失败不改判。下一变体排除所有多帧子树，不放宽边界/像素要求。
