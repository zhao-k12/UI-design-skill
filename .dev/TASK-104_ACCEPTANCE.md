# TASK-104 — Figma 字节锁执行回执持久化

日期：2026-10-20。状态：**FIGMA_SAMPLE_RECEIPT_PASS / RELEASE_NOT_READY**。本任务复用 TASK-102 的冻结列表输入、UI-IR 与版本化 Adapter 锁，不修改 Core、正式 Registry、Adapter 执行代码或 Penpot 原生文件。

在用户提供的 Figma 文件中创建独立验证页 `236:2`，按新 [执行意图](../artifacts/task-104/figma-execution/execution-intent.json)提交原生脚本，并保存完整 [执行回执](../artifacts/task-104/figma-execution/execution-result.json)。Figma 返回 `PASS`、根节点 `236:3`、49 个 UI-IR 节点映射和 49 条原生执行证据。再次通过独立 Figma 调用读取页面：1920×1080、6 个真实组件/图标实例、25 个文字节点；两次原生全尺寸 PNG 逐字节相同，SHA-256 均为 `d8319e83cacb017a154dcb49138aa324639b31115a368fe645b3e59347b6b3cd`，且与 TASK-102 的同一锁定页面完全一致。

[机器审计](../artifacts/task-104/figma-native-qa.json)核对当前 Adapter 源码锁、预检计划、提交脚本、执行意图、返回节点映射、独立读回、主组件关联与 PNG，结果 `PASS`、`executionReceiptPersisted=true`、`releaseReady=false`。在临时副本中改动回执的 `nodeMap` 后返回 `FAIL/native_execution_receipt_mismatch`。完整回执及像素已保存；原生内容视觉与 TASK-102 已目视通过的 PNG 字节一致。

该验证只覆盖冻结列表样张的 Figma 执行回执。11 类 Figma 单端组件仍未正式双端准入；Penpot 原生线按用户决定暂缓，独立新原型与全量 Release Gate 尚未执行。故不能标记 V0.2 发布完成。
