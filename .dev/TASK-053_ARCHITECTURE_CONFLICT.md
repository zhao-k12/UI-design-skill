# TASK-053 — Adapter 运行时代码未进入任务版本锁

日期：2026-10-14。状态：OPEN；本任务仅审计，不修改主链路。

当前设计：`core/pipeline/runner.py` 的 `programSha256` 只覆盖 `core/`、`schemas/`、`validators/` 中的 Python/JSON 文件；Manifest 另记录 Figma/Penpot Adapter 的版本字符串 `0.1.0`，但不记录编译器或原生运行器文件字节。Adapter 计划和原生执行产物分别保存。

实际原因：TASK-052 为避免 Penpot 完整写入后布局等待超时误报，修改了 `adapters/penpot/runtime.js`。新的原生执行脚本和 TASK-051 预检计划仍使用同一 Adapter 版本字符串，TASK-051 Manifest 的 `programSha256` 也不会因该文件修改而改变。版本号与 Core 程序锁不足以证明原生执行时使用的 Adapter 字节与预检时一致。

影响：当前冻结列表页的独立原生读回和 PNG 验收仍是真实证据，但不能宣称具有完整 Adapter 代码可追溯锁；V0.2 全量 Release Gate 不得因此标为 PASS。后续若复用版本号而修改 Adapter，旧任务的恢复或发布审计可能错误复用证据。

建议：在新的 V0.2 Manifest/Adapter 执行账本中分别锁定 Figma/Penpot 编译器、运行器和实际执行脚本的 SHA-256，并定义版本迁移、预检失效和恢复行为；不得原地修补 TASK-051 的旧锁或历史 V0.1 Manifest。该方案属于版本契约变更，待单独决策和端到端回归后实施。
