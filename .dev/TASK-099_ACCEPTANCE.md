# TASK-099 — Cascader Figma 单端质量核验

日期：2026-10-20。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-097 官方两级地区选中态来源及 TASK-098 Figma 候选。独立复读 Figma 原生主组件 `231:13`、实例 `231:19`、可编辑“浙江 / 杭州”、官方 Ionicons 下箭头和颜色变量，再次导出 PNG/SVG；重复导出与候选逐字节一致。官方与 Figma 240×32px 截图比较，排除文字和箭头区后的 3,910 个像素中仅四角 41 像素有抗锯齿差异，最大通道差 4，其余像素完全一致。文字和箭头区分别有 310、16 个可见像素，均完整落在指定范围。

[单端报告](../artifacts/task-099/cascader-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-099/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-099/figma/`；Figma QA 元数据见 `adapters/figma/metadata/cascader-default-font-fidelity-0.2.18-figma-only.json`。测试：`python -m unittest tests.test_default_font_cascader_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Cascader 尚未进入正式 Registry。
