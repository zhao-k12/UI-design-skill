# TASK-058 — Checkbox 固定选中态官方来源基线

日期：2026-10-15。状态：PASS（来源提取任务）；Figma/Penpot 保真与 Registry 准入均 `NOT_RUN`。

依赖锁定的 View UI Plus `1.3.24` 源码、CSS 和真实 Chromium 运行环境。范围仅为 `form.checkbox.default.enabled`：默认尺寸、已选中、启用、非不确定态、无边框、固定文字“启用”。新增独立 Checkbox cases/harness/extractor，未修改官方包或旧来源记录；通用提取器和 Component IR Schema 仅扩展识别 `Checkbox` 类型。

来源文件 `checkbox.vue`、`checkbox.less`、checkbox mixin 的哈希记录在 [观察报告](../artifacts/task-058/checkbox-source/checkbox-observation.json)；运行清单、[Component IR](../artifacts/task-058/checkbox-source/component_ir.json)、提取报告与真实浏览器 PNG 均保存于同目录。浏览器测得外框 52×21px、选框内部 16×16px、选中底色 `rgb(45, 140, 240)`、文字 14px；Chromium 实际中文字体为 PingFang SC。截图人工查看为蓝色选中框与两字“启用”，无明显裁剪。

`verify_artifacts(..., expected_types={'Checkbox'})` 无问题；Component IR 4 项测试、原有浏览器提取 3 项测试、Core 架构检查和 Git diff 检查通过。来源报告 `fidelityGate=NOT_RUN`，不可据此登记正式 Registry；后续 Figma Inter / Penpot sourcesanspro 默认字体改编需要两端原生组件及独立 Fidelity Gate。
