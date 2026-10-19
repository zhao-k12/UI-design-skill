# TASK-081 — Tree Figma 单端质量核验

日期：2026-10-19。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-079 官方展开树来源及 TASK-080 Figma 候选。独立复读 Figma 原生主组件 `210:6`、实例 `210:15`、三个可编辑标签和官方 Remix 展开箭头，再次导出 PNG/SVG；重复 PNG 与候选逐字节一致。白底合成后与官方 240×79px 截图比较，排除标签与箭头区域的 11,862 个像素**全部逐像素一致**，最大 RGB 通道差 0。三个文字区分别有 155、246、210 个可见深色像素，箭头区 18 个；视觉复核确认无裁切、脱离或额外子节点图标。

[单端报告](../artifacts/task-081/tree-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-081/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-081/figma/`；Figma QA 元数据见 `adapters/figma/metadata/tree-default-font-fidelity-0.2.12-figma-only.json`。测试：`python -m unittest tests.test_default_font_tree_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Tree 尚未进入正式 Registry。
