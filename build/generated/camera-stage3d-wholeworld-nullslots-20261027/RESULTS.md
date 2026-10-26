# camera-stage3d-wholeworld-nullslots-20261027-r1

加入空槽核验，本轮未遇空槽，不能声称前轮空值原因已证实。遍历7444节点/1670多帧，21显式播放者停止后，24个原isPlaying=false的子轴仍变帧。7纹理、8临时图、65像素图释放，0计时；恢复失败保留。

冻结源 `f22d6e664ec7453da03325150385233b`，探针 `AE8F4533AC87F51ABD2C1E1E37A892B581FDE8C12935C4248D18A0997A4DEED5`，自有AIR 64972 已结束。独立复核526正式文件、13运行库、86源及脚本/编译器输入保持。

原始结果 ok=False，完整计时间隔 0，清理 restored=False；错误 `['Fixed-picture timeline changes: 24', 'Cleanup failed']`。失败不改判。

核对依据：本目录同名 evidence/storage/result.json、probe-build.json、runner-inputs.json、process-policy.json；统一独立复核见 camera-stage3d-wholeworld-settle-20261027/runs-review.json。正式宿主仍 A796，CS0.9.0仍7F1F。
