# TASK-054 — Tag 默认静态配置官方来源基线

日期：2026-10-14。状态：PASS（来源提取任务）；组件准入：**未执行**。

依赖：TASK-053 的 V0.2 发布审计与既有 View UI Plus `1.3.24` 来源锁。范围仅为一个固定候选：`Tag` 默认尺寸、默认颜色、不可关闭、不可勾选、已选中，文字固定为“启用”。不变更旧组件 Registry、Core、Adapter、Figma/Penpot 原生文件或已冻结的 V0.1/V0.2 证据。

官方源码 `src/components/tag/tag.vue` 与 `src/styles/components/tag.less` 的 SHA-256 写入 [tag-observation.json](../artifacts/task-054/tag-source/tag-observation.json)。`tag-cases.json`、`tag-harness.js` 经现有来源锁浏览器提取器执行，输出 [Component IR](../artifacts/task-054/tag-source/component_ir.json)、[提取报告](../artifacts/task-054/tag-source/extraction_report.json)、[运行清单](../artifacts/task-054/tag-source/runtime_manifest.json) 和 [原生浏览器截图](../artifacts/task-054/tag-source/data.tag.default.enabled.png)。候选根尺寸 42×22 px，两个 DOM 节点，无图标；默认边框 1 px、圆角 3 px、左右内边距 8 px，字体 12 px。Chromium 实际中文字形字体为 PingFang SC。这是官方浏览器基线；后续 Figma Inter / Penpot sourcesanspro 默认字体改编须重新测量和做双端保真验收。

验收：`verify_artifacts(..., expected_types={'Tag'})` PASS、`tests.test_component_ir` 4 项 PASS、`tests/runtime-extraction.test.mjs` 3 项 PASS、`git diff --check` PASS。提取报告的 `fidelityGate` 为 `NOT_RUN`，因此该候选**不得写入正式 Registry**，也不提高 TASK-053 的 V0.2 发布就绪结论。下一步构建双端原生候选并执行限定内容范围的 Fidelity Gate。
