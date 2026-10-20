# TASK-090 — Modal Figma 单端质量核验

日期：2026-10-20。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-088 官方通知框来源及 TASK-089 Figma 候选。独立复读 Figma 原生主组件 `222:13`、实例 `222:14`、可编辑标题与正文、颜色变量和阴影，再次导出 PNG/SVG；重复导出与候选逐字节一致。Figma 344×128px 阴影导出白底合成后裁切内容框 (12,8) 的 320×104px，与官方截图比较。排除文字区后 24,744 个像素中仅四角 56 像素有差异；其余 24,688 个像素完全一致。四角最大通道差 120，反映官方裁切截图与 Figma 阴影边缘合成方式的区别；原生 6px 圆角与阴影另经结构读回和视觉复核。标题、正文分别有 253、360 个可见深色像素，均完整落在指定区域，无遮挡或脱离。

[单端报告](../artifacts/task-090/modal-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-090/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-090/figma/`；Figma QA 元数据见 `adapters/figma/metadata/modal-default-font-fidelity-0.2.15-figma-only.json`。测试：`python -m unittest tests.test_default_font_modal_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Modal 尚未进入正式 Registry。
