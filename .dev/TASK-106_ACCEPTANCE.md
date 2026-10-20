# TASK-106 — 锁漂移后的 Core 恢复与当前 Figma 原生回执

日期：2026-10-20。状态：**FIGMA_PLATFORM_LOCK_PASS / RELEASE_NOT_READY**。

本任务限定修复 V0.2 Adapter 字节锁漂移时的失败范围。旧行为经外层异常处理会清空已通过的 Core `final_ui_ir.json`；现在写入 `MIGRATION_REQUIRED`、`readyForAdapter=false` 和锁漂移原因，返回失败码，同时保留九阶段 Checkpoint 与最终 UI-IR。锁内源码、计划和执行脚本的字节校验未放宽。原生审计补核执行回执中的 Tokens、Components、Icons 三项哈希。`tests.test_v02_pipeline_profile` 三项测试 PASS，包括漂移后 Core 产物保留。

代码字节更新后，新任务目录生成 [Adapter 执行锁](../artifacts/task-106/run/adapter-execution-lock.json)，不能迁移复用 TASK-105 的旧锁。Figma 新页 `238:2` 依据锁定脚本实际执行，完整 [执行回执](../artifacts/task-106/figma-execution/execution-result.json) 为 PASS，含 49 个节点映射和 49 条执行证据。独立 [原生读回](../artifacts/task-106/figma/native-read.json)确认根节点 `238:3` 为 1920×1080，6 个真实实例、25 个文字节点；两次 PNG SHA-256 均为 `d8319e83cacb017a154dcb49138aa324639b31115a368fe645b3e59347b6b3cd`。[机器审计](../artifacts/task-106/figma-native-qa.json) PASS，`releaseReady=false`。

本任务仅闭合冻结列表样张的 Figma 当前字节锁与故障恢复行为。Penpot 原生线按用户决定暂缓；11 类组件未双端正式准入，独立新原型与全量 Release Gate 未完成。
