# TASK-091 — Drawer 固定详情官方运行来源锁

日期：2026-10-20。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `overlay.drawer.detail.open`：右侧打开、标题“详情”、正文“抽屉内容”、宽 320px、无关闭按钮、遮罩开启。以官方 Drawer 的 `.ivu-drawer` 为组件根捕获，真实浏览器面板 320×500px；标题区 51px，正文区 449px，白底及 `rgba(0,0,0,.15) 0 4px 12px` 阴影。因组件将面板传送到页面根部，采集时仅把逻辑 ID 绑定到真实面板 DOM，不改官方样式。源码 `drawer.vue`、`drawer.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-091/drawer-source)。遮罩属于周边页面状态，不在固定面板截图中。

本任务把 `Drawer` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Drawer"})` 无问题；截图人工确认标题、正文与分隔线完整，来源测试通过。

当前来源证据不代表正式准入或 V0.2 发布就绪。
