# TASK-105 — Adapter 字节锁逐端失效与当前 Figma 证据

日期：2026-10-20。状态：**FIGMA_PLATFORM_LOCK_PASS / RELEASE_NOT_READY**。本任务修正 TASK-102 实现与已批准逐端失效方案之间的偏差：执行脚本验证只复算所选平台的源码与计划锁，共享执行文件仍参与两端。Figma 校验不读取 Penpot 计划；Penpot 源码或锁变化不会使已锁定的 Figma 执行意图失效，反之亦然。新 V0.2 生产预检仍同时生成两端锁，旧任务目录的锁不能被新代码原地升级。

`tests.test_v02_pipeline_profile` 的 3 项测试 PASS，覆盖仅改动 Penpot `runtime.js` 哈希时 Figma 脚本可验证、Penpot 自身拒绝，以及同字节恢复、Figma 锁漂移和执行脚本篡改拒绝。旧 TASK-102/104 的锁绑定旧代码字节，按迁移规则保留为历史快照，不拿旧回执冒充新锁验收。

以相同冻结列表输入在新目录生成 [当前字节锁](../artifacts/task-105/run/adapter-execution-lock.json)，Figma 执行意图绑定新页 `237:2`。实际原生执行返回 `PASS`，并保存 [完整回执](../artifacts/task-105/figma-execution/execution-result.json)：根节点 `237:3`、49 个 UI-IR 映射/执行证据。独立 [原生读回](../artifacts/task-105/figma/native-read.json)核对 1920×1080、6 个真实实例、25 个文字节点；两次 PNG 的 SHA-256 都是 `d8319e83cacb017a154dcb49138aa324639b31115a368fe645b3e59347b6b3cd`，与先前冻结样张字节相同。 [机器审计](../artifacts/task-105/figma-native-qa.json)返回 `PASS`、`executionReceiptPersisted=true`、`releaseReady=false`。

此处只闭合冻结列表样张的 Figma 逐端锁。Penpot 原生线按用户决定暂缓；11 类候选组件仍未双端正式准入，独立新原型和全量 Release Gate 尚未完成。
