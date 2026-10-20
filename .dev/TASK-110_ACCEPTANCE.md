# TASK-110 — 七组件生产 Profile 与紧凑查询原型迁移

日期：2026-10-20。状态：**FIGMA_SCOPED_PASS / V0.2_NOT_READY**。

生产 CLI 新增显式 `--profile v0.2.6`，引用已正式准入的七组件 Registry 与对应双端绑定。迁移脚本 `scripts/migrate_compact_search_v026.py` 从已审核的紧凑查询输入创建独立的 `examples/user-management-compact-search-v026`：逐文件验证旧输入锁及人工审核，通过后仅更新 Registry 决策、映射哈希与组件库版本。原型文字 SHA-256 仍为 `389221d44730b662f4c53041d564304c536633a6ce4df019eb51182c9b8724c1`。旧输入被新 Profile 明确拒绝，未原地覆盖历史证据。

新输入的九阶段 Core、Figma/Penpot 静态 Adapter 预检 PASS，重复运行九阶段均复用 Checkpoint；最终 UI-IR SHA-256 为 `6e3768d799efb28b01e7e02e80dc8bfd5b5feee2ba598bc379cf28f4f598ae65`，新执行锁 SHA-256 为 `eef592515923da51b8ecaf1776a287e98c1e8b93503ed1229afbe04445922555`。Figma 新页 `243:2` 的受锁原生执行保存 37 项节点映射和完整回执。独立读回核对 1920×1080 根节点、5 个真实实例、21 个文字节点；两次原生 PNG 的 SHA-256 均为 `71afd671d755ca36569f031df262f295472ea7d4374b49c7033157efa8ffedfc`。[原生 QA](../artifacts/task-110/figma-native-qa.json)、[独立原型 QA](../artifacts/task-110/independent-figma-qa.json)、[视觉复核](../artifacts/task-110/visual-review.json)与[九项 Figma 发布门](../artifacts/task-110/figma-release-gates.json)均 PASS。

定向测试：`9 passed`，覆盖七组件双端绑定、旧输入拒绝、新输入流水线、Figma 原生证据及就绪审计。该页面实际使用 Button、Input、Select、Table 四类；Tag、Checkbox、Radio 在 Profile 中可用，但没有被此页行使。[当前就绪汇总](../artifacts/task-110/current-release-readiness.json)为 `evidenceValid=true`、`releaseReady=false`。用户已决定暂缓 Penpot 原生线；11 类组件双端正式准入、跨平台视觉对比及全量发布门继续待办。
