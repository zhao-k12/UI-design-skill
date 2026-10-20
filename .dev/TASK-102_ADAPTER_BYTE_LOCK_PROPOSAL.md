# TASK-102 — V0.2 Adapter 字节锁迁移方案（待决策）

日期：2026-10-20。状态：**PROPOSED / NOT_IMPLEMENTED**。依据 [TASK-053 架构冲突](TASK-053_ARCHITECTURE_CONFLICT.md)；本记录不改变 V0.1 Manifest、现有 V0.2 输入、Adapter、Checkpoint 或历史原生证据。

## 现状与风险

`core/pipeline/runner.py` 的 `programSha256` 只覆盖 `core/`、`schemas/`、`validators/`。`scripts/run_pipeline.py` 只检查两端 `adapterVersion` 字符串；`scripts/finalize_pipeline.py` 复核 Core 程序与证据，但未证明预检和原生执行使用同一套 Adapter 源码字节。同版本字符串下改动 `adapters/penpot/runtime.js` 已在 TASK-052 实际发生。因此发布门不能仅凭当前 Manifest 判定 Adapter 可重放。

## 推荐决策

为**新任务目录**启用 `adapterExecutionLock` 契约版本 `0.2.0`。保持 Core `programSha256` 和旧 Manifest 原样；每个平台独立记录如下内容：

1. `adapterVersion`、`compilerFiles`、`runtimeFiles`：列出本次实际编译/执行读取的仓库相对路径及**原始字节** SHA-256。包含 Figma `compiler.py`/`runtime.js` 或所选 `content_compiler.py`，Penpot `compiler.py`/`runtime.js`/`content_runtime.js`，以及该执行路径实际加载的 helper、host 拼接文件。禁止只锁一个入口文件而漏掉其依赖。
2. `planSha256`、`executionScriptSha256`：分别锁预检计划的规范序列化字节和实际提交给平台运行的完整脚本字节。执行回执记录这两项、目标文件引用、UI-IR 哈希与原生节点账本哈希；独立复验必须逐项核对。
3. `lockSchemaVersion` 和 `migrationFrom`：显式区分新锁与旧任务。旧 TASK-051/052 不补写新字段，也不把既有 PASS 自动升级；新锁缺失或哈希变化时状态为 `MIGRATION_REQUIRED`，不得复用原生 PASS。
4. 失效粒度：Core 输入与 Core 代码未变时可复用 Core 阶段；Figma 字节变化仅使 Figma 预检及后续原生执行/QA 失效，Penpot 同理；共享 UI-IR 或 Registry 变化使两端失效。保存失效原因及新旧哈希，执行到一半保留 `PARTIAL` 证据以便审查。

## 实施验收

先给出代码依赖清单和两端最小样张，证明源文件、计划、运行脚本、回执可闭环核对；再做同字节恢复、仅一端 Adapter 改动、Core 改动、执行脚本篡改、缺失旧锁和跨目标文件重放等负例。Figma 与 Penpot 分别需要实际原生执行和独立读回才能宣称该端发布锁 PASS；当前 Penpot 暂缓时最多完成 Figma 端与离线契约测试，整体 V0.2 仍 `NOT_READY`。

## 待明确选择

推荐采用上述**版本化、逐端原始字节锁**，并在用户明确架构决策后实施。若选择维持现状，则 TASK-053 风险保持开放，V0.2 全量 Release Gate 继续阻塞。其他方案须先补充其覆盖的执行依赖、迁移和恢复语义。
