# TASK-072 — Card Figma 单端质量核验

日期：2026-10-15。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。Penpot 线按用户决定暂缓，本任务不改双平台正式准入条件。

依赖 TASK-070 官方来源锁与 TASK-071 Figma 候选。Figma 独立复读原生主组件 `198:8` 和关联实例 `198:14`，再次导出 PNG/SVG；两次 PNG 与候选逐字节一致。白底合成后，与官方 240×106 截图比较：文字区域外 21,310 个像素中 99.8217% 逐像素相同，最大 RGB 通道差 3；标题与正文深色字形像素分别为 421、263，均在固定文字框内。视觉复核确认“用户信息”“暂无内容”、边框及分隔线完整。

[单端报告](../artifacts/task-072/card-figma-qa.json)六项检查 PASS；[视觉复核](../artifacts/task-072/visual-review.json)绑定 PNG 哈希。独立读回、PNG/SVG 见 `artifacts/task-072/figma/`。Figma QA 元数据存于 `adapters/figma/metadata/card-default-font-fidelity-0.2.9-figma-only.json`。测试：`python -m unittest tests.test_default_font_card_figma_gate_v02`，2 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；Card 尚未进入正式 Registry。下一步继续其他未准入组件的官方来源与 Figma 单端开发。
