# TASK-047 — ARCHITECTURE_CONFLICT: 旧来源几何与 V0.2 准入 Registry

日期：2026-10-14。状态：以独立 V0.2 来源几何快照解决。

## 当前设计

V0.1 验收原型的 `source-geometry.json` 是冻结输入；`SourceGeometry` 要求每个 Component IR 哈希与当前 Registry 的准入哈希一致。V0.2.3 Registry 的 Button、Input、Select 已依据 TASK-023 重新提取并完成双端默认字体验收，旧几何的这三项哈希不再匹配；Table 的哈希仍匹配。

## 原因与影响

修改旧文件会破坏历史输入锁；仅改宽高会伪造组件来源且不能通过哈希门。完整 V0.2 输入包还需文字测量、图标和版本锁，本任务不借几何重建将其隐式视为可运行。

## 决策与实施边界

从已锁定 TASK-023 官方运行 Component IR 取 Button、Input、Select，从冻结 Table 来源取已准入 Table，按 V0.2.3 Registry 的逻辑 ID 和 SHA-256 逐项核验，生成独立 `examples/acceptance-prototype-v02/source-geometry.json` 与输入哈希记录。审计增加显式 `--geometry` 选择，默认仍读冻结 V0.1 包；选用新几何时只能解除几何一项阻塞。Core 的放置规则、历史包和正式流水线不变。
