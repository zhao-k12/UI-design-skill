# TASK-096 — Upload Figma 单端质量核验

日期：2026-10-20。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务未更改双平台正式准入条件。

依赖 TASK-094 官方拖拽空态来源及 TASK-095 Figma 候选。独立复读 Figma 原生主组件 `229:7`、实例 `229:9`、可编辑“上传文件”文字、颜色变量和 3/2 虚线描边，再次导出 PNG/SVG；重复导出与候选逐字节一致。官方与 Figma 320×82px 截图比较，排除文字区后的 23,265 个像素中，667 个差异全部位于 5px 外边缘内，最大通道差 35，反映 CSS 与 Figma 原生虚线栅格化；框内部其余像素完全一致。文字有 235 个可见深色像素，完整落在指定区域。

[单端报告](../artifacts/task-096/upload-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-096/visual-review.json)绑定原生 PNG 哈希。读回及导出见 `artifacts/task-096/figma/`；Figma QA 元数据见 `adapters/figma/metadata/upload-default-font-fidelity-0.2.17-figma-only.json`。测试：`python -m unittest tests.test_default_font_upload_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Upload 尚未进入正式 Registry。
