# TASK-029 — 替代 Penpot 文件的输入锁迁移

日期：2026-10-13。用户确认原 Penpot 验收文件已删除，授权“新建文件 1”为新的验收文件。TASK-026 的 0.2.0 输入锁保留原样作为历史证据；新增 0.2.1 清单明确记录旧文件、新文件与两端 Button 候选。

`scripts/font_adaptation_manifest_v021.py` 核验 TASK-026 锁定的政策、来源、字体 profile 和目标元数据哈希；核验两端候选的原生 ID、证据哈希与待验收状态；将活动 Penpot 文件绑定为 `57949053-620f-8001-8008-c804c8d61529`。产物为 `artifacts/task-029/font-adaptation-manifest.json`，状态 `TARGET_REPLACED_BUTTON_CANDIDATES_PENDING_ADMISSION`。Button 测量状态为 `CANDIDATE_REVIEW`，Input、Select、Table 仍为 `NOT_RUN`；所有组件的原生准入仍为 `NOT_RUN`，`releaseReady=false`。

反例测试验证旧文件不能继续作为活动目标、缺失证据和虚假准入会被拒绝。本次迁移不复用历史 Penpot 原生组件或字体样张的通过状态；新文件的默认字体由 TASK-028 原生创建时重新观测。

Core 检查 168 项通过；Git diff 空白检查通过。
