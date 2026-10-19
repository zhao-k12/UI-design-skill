# TASK-084 — DatePicker Figma 单端质量核验

日期：2026-10-19。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-082 官方固定日期来源及 TASK-083 Figma 候选。独立复读 Figma 原生主组件 `218:16`、实例 `218:17`、可编辑日期和 Remix 日历图标，再次导出 PNG/SVG；重复 PNG 与候选逐字节一致。白底合成后与官方 211×32px 截图比较，排除日期和图标区的 3,690 个像素中仅四角抗锯齿 41 像素有差异，最大通道差 4，其余像素完全一致。日期与图标区分别有 260、86 个可见深色像素；文字和图标无裁切或脱离。

[单端报告](../artifacts/task-084/datepicker-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-084/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-084/figma/`；Figma QA 元数据见 `adapters/figma/metadata/datepicker-default-font-fidelity-0.2.13-figma-only.json`。测试：`python -m unittest tests.test_default_font_datepicker_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；DatePicker 尚未进入正式 Registry。
