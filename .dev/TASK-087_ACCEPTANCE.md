# TASK-087 — Form Figma 单端质量核验

日期：2026-10-19。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-085 官方单字段来源及 TASK-086 Figma 候选。独立复读 Figma 原生主组件 `220:9`、实例 `220:10`、可编辑“姓名”标签和已准入 Input 实例 `220:6`，再次导出 PNG/SVG；重复 PNG 与候选逐字节一致。白底合成后与官方 320×34px 截图比较，排除标签及占位文字区的 7,458 个像素中仅输入框四角抗锯齿 41 像素有差异，最大通道差 4，其余像素完全一致。标签与占位区分别有 148、226 个可见文字像素；视觉复核确认无遮挡或裁切。

[单端报告](../artifacts/task-087/form-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-087/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-087/figma/`；Figma QA 元数据见 `adapters/figma/metadata/form-default-font-fidelity-0.2.14-figma-only.json`。测试：`python -m unittest tests.test_default_font_form_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Form 尚未进入正式 Registry。
