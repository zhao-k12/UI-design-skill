# TASK-044 — ARCHITECTURE_CONFLICT: V0.1 冻结流水线不能直接迁移到 V0.2

日期：2026-10-14。状态：OPEN；本任务只建立可执行的迁移就绪审计，不改主链路。

## 当前设计

`scripts/run_pipeline.py` 固定加载 V0.1 Component Registry、Token、组件/图标/字体绑定和旧 Penpot 原生保真证据；`examples/acceptance-prototype` 的版本、来源几何、运行测量也绑定旧组件及字体。它是已冻结的 V0.1 闭环。V0.2.3 已准入四个固定内容组件，TASK-043 证明同一 UI-IR 的两端 Adapter 原生执行，但尚未建立从原型到该 UI-IR 的新输入锁。

## 原因与影响

将旧 `source-geometry.json` 与 V0.2.3 Registry 一起构造 `SourceGeometry`，实际抛出 `Source geometry does not match admitted Component IR`。旧样例含设置、下载图标，但 Penpot 图标绑定仍指向已删除的文件 `91396aad-60c8-808b-8008-c0885ca79899`。旧测量来源和标题字体不是新文件的默认字体；V0.2 Token 中 `size.page` 仍为 1440，而新页面目标是 1920。若仅切换 CLI 版本或复用旧 checkpoint，会绕过来源、测量及原生身份边界。

## 建议与本次边界

先以只读就绪审计明确每项阻断，并锁定目标文件、源输入和目标 Registry。后续独立任务重建 V0.2 来源几何和默认字体测量，为新 Penpot 文件完成所需图标准入或使用一份明确不含图标的新原型，再以版本化 CLI/Manifest 迁移运行器。任何视觉内容缺失均需原型来源支持；不从旧样例静默删去图标或表头。本任务不声称 V0.2 端到端 PASS。
