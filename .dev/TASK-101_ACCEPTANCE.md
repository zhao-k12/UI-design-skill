# TASK-101 — Figma 覆盖证据字节复核

日期：2026-10-20。状态：**PASS / RELEASE_NOT_READY**。本任务只强化 TASK-100 的只读证据审计，不修改 Core、正式 Registry、Adapter 写入或 Penpot 资产。

审计现在对 11 类 Figma 单端 QA 的原生读回 JSON、首次 PNG、重复 PNG、SVG 逐项复算 SHA-256，并要求两份 PNG 哈希一致。它同时拒绝空检查清单、非布尔通过值，以及 QA/Adapter metadata 中误写的页面生成或双端准入状态。篡改 Cascader 重复导出时，审计必须返回 `INVALID_EVIDENCE`。

验证：`python -m unittest tests.test_v02_component_coverage_figma -q`，3 项 PASS；`python -m scripts.audit_v02_component_coverage_figma --output artifacts/task-100/coverage-audit.json` 返回 `FIGMA_EVIDENCE_COMPLETE`、`evidenceValid=true`、`releaseReady=false`。全量回归另行记录实际结果。

剩余门槛：11 类双端 Fidelity Gate 与正式 Registry 准入、版本化 Adapter 字节锁的架构决策、独立新原型及全量 Release Gate。Penpot 按用户决定暂缓，因此不能将当前证据声明为 V0.2 发布完成。
