# TASK-070 — Card 固定配置官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；Figma 候选与单端质量核验均 `NOT_RUN`，双端正式 Fidelity Gate 与 Registry 准入均未执行。

按用户的最新决定，Penpot 线暂缓。本任务只抽取 View UI Plus 1.3.24 的 `content.card.default.user-info`：标题“用户信息”，默认槽内容“暂无内容”，`bordered=true`、`disHover=true`、`shadow=false`、`padding=16`。官方 `card.vue` 和 `card.less` 哈希记录在 [观察证据](../artifacts/task-070/card-source/card-observation.json)；未改写官方样式。

真实浏览器 DOM 外框 240×106px，白底、4px 圆角、`#E8EAEC` 的 1px 边框；标题区 238×51px，内容区 238×53px。样张文字与结构完整。[来源证据](../artifacts/task-070/card-source)包含 Component IR、浏览器截图、运行环境、源码哈希、Manifest 和观察记录。`verify_artifacts(..., expected_types={"Card"})` 无问题；Card 来源测试通过。

此证据仅为设计候选的官方来源，不代表 Figma 原生保真、Registry 准入或 V0.2 发布就绪。下一步建立 Figma 默认字体可编辑 Card 主组件与实例并核验。
