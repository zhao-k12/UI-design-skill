# TASK-078 — Tabs Figma 单端质量核验

日期：2026-10-15。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-076 官方双标签来源及 TASK-077 Figma 候选。独立复读 Figma 原生主组件 `207:3`、实例 `207:14`、可编辑标签、底线、选中线和可见内容，再次导出 PNG/SVG；重复 PNG 与候选逐字节一致。白底合成后与官方 320×73px 截图比较，排除三个文字区域的 20,332 个像素**全部逐像素一致**，最大 RGB 通道差 0。三个文字区各有 187、137、346 个可见深色像素，均在固定范围内；未选中“详情内容”未出现在画布。

[单端报告](../artifacts/task-078/tabs-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-078/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-078/figma/`；Figma QA 元数据见 `adapters/figma/metadata/tabs-default-font-fidelity-0.2.11-figma-only.json`。测试：`python -m unittest tests.test_default_font_tabs_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Tabs 尚未进入正式 Registry。
