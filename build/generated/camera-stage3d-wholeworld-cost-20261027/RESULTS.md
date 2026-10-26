# camera-stage3d-wholeworld-cost-20261027-r1

归因计时前，两个bloat_bulk_896从55帧被自身帧脚本重新播放到3帧。参考源已核：frame55调用gotoAndPlay(2)，frame1随机gotoAndPlay。0计时；47个持有者中45个恢复，另2个已被外部重播，未强行覆盖。65像素图/8临时图/7纹理释放，原始恢复失败保留。

冻结源 `666d6fb80e384f6081e0e49a8e7d90cd`，探针 `594406402D93ED1C9CC4E44A638C31BE779554F3CB31FB1440A2C7CCCFFF87C1`，自有AIR 30136 已结束。独立复核526正式文件、13运行库、86源及脚本/编译器输入保持。

原始结果 ok=False，完整计时间隔 0，清理 restored=False；错误 `['Fixed-picture timeline changes: 2', 'Cleanup failed']`。失败不改判。

核对依据：本目录同名 evidence/storage/result.json、probe-build.json、runner-inputs.json、process-policy.json；统一独立复核见 camera-stage3d-wholeworld-settle-20261027/runs-review.json。正式宿主仍 A796，CS0.9.0仍7F1F。
