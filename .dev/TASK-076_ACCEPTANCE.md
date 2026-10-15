# TASK-076 — Tabs 固定双标签配置官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `navigation.tabs.line.overview`：`type=line`、默认尺寸、无动画、不可关闭，两个标签“概览”“详情”，选中概览，内容为“概览内容”。真实浏览器外框 320×73px，标签栏 320×36px；两个标签各 60×37px，左端分别 x=0、76；选中蓝色下划线 x=0、y=34、60×2px；内容从 y=52 开始。未选中“详情内容”节点实际宽高为零，不应在静态设计中露出。官方颜色、文字和样张均保存于 [来源证据](../artifacts/task-076/tabs-source)。

来源证据含 Component IR、浏览器截图、运行环境、官方 `tabs.vue`、`pane.vue` 与 `tabs.less` 哈希、Manifest、观察记录。`verify_artifacts(..., expected_types={"Tabs"})` 无问题；截图人工确认标签、下划线和内容完整，来源测试通过。

本任务只锁定来源，未证明 Figma 原生保真、Registry 准入或 V0.2 发布就绪。下一步以默认 Inter 建立 Figma 双标签原生候选。
