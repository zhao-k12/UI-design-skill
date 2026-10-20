# TASK-093 — Drawer Figma 单端质量核验

日期：2026-10-20。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-091 官方右侧详情面板来源及 TASK-092 Figma 候选。独立复读 Figma 原生主组件 `226:8`、实例 `226:13`、可编辑标题与正文、颜色变量和阴影，再次导出 PNG/SVG；重复导出与候选逐字节一致。Figma 344×524px 阴影导出白底合成后裁切面板 (12,8) 的 320×500px，与官方截图比较。排除文字区后的 151,464 个像素全部一致；标题、正文分别有 278、355 个可见深色像素，均完整落在指定区域，无遮挡或脱离。

[单端报告](../artifacts/task-093/drawer-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-093/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-093/figma/`；Figma QA 元数据见 `adapters/figma/metadata/drawer-default-font-fidelity-0.2.16-figma-only.json`。测试：`python -m unittest tests.test_default_font_drawer_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Drawer 尚未进入正式 Registry。
