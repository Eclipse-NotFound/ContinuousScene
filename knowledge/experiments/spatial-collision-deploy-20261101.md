# 空间分区碰撞优化：实现、验证与部署（2026-11-01）

## 问题

`Bullet.as:503` 每颗子弹对**所有 ~130 个单位**做 AABB 碰撞（无空间分区）。12 敌人时 ~40 发子弹 × 130 单位 = ~5200 检查/帧，导致战斗帧 54-57ms（超 33ms 目标 24ms）。

## 实现

两个方法替换（均在当前宿主 9D8662F6 上）：

1. **`Grafon.sceneTick`**：每帧构建视口内（±500px）单位子列表，存于 `visual.root["sceneCU"]`
2. **`Bullet.run`**：碰撞循环优先读 `visual.root["sceneCU"]`（过滤后 ~15 个），回退到 `loc.units`

无可见性管理（避免 UnitSpectre 视觉问题），无视觉影响。

## 验证（12 敌人，v12 探针）

| 指标 | 基线 (9D86) | 碰撞-only (A9B3) | 改善 |
|---|---:|---:|---:|
| **战斗静止** | **56.8ms** | **44.5ms** | **−12.3ms (−21.7%)** |
| 战斗走动（均值） | 54.6ms | 51.4ms | −3.2ms (−5.9%) |
| 静止 | 33.4ms | 32.7ms | OK |
| 走路 | 35.4ms | 35.0ms | OK |
| 战斗静止 max | 155ms | ~131ms | −24ms |

含可见性版本（已否决，UnitSpectre 问题）：战斗静止 47.1/51.0ms（不如碰撞-only 44.5ms）。

## 部署

- 安装：2026-11-01 22:58，根 `pfe.swf` → **`A9B39CC7…`**
- 备份：`pfe_before_spatial_collision_20261101-225837.swf`
- 回执：`build/host-patch-receipt-spatial-collision-20261101.json`
- 冒烟：10 断言、1270 帧，通过
- **需重启游戏生效**
- 回退：用备份覆盖根 `pfe.swf`

## 碰撞过滤机制

```
Grafon.sceneTick（每帧）:
  视口边界 ± 500px → 过滤 loc.units（~130）→ 得到子列表（~15）
  存于 visual.root["sceneCU"]（MovieClip 动态属性，下一帧 Bullet 读取）

Bullet.run（每颗子弹每帧）:
  优先读 visual.root["sceneCU"]（~15 单位）
  找不到时回退到 loc.units（~130 单位，安全兜底）
```

子列表比全量少 ~88%，碰撞检查从 ~5200 次/帧降至 ~600 次/帧。

## 证据

- 基线：`camera-v12-e12-r1`（12 敌）
- 含可见性版本：`camera-spatial-e12-r{1,2}`（已否决）
- **碰撞-only：`camera-spatial2-e12-r1`**（部署版本）
- 安装后冒烟：`camera-spatial-deployed-verify-20261101-r1`
- 构建：`build/generated/camera-spatial-20261101/`
