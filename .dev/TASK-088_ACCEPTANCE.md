# TASK-088 — Modal 固定通知官方运行来源锁

日期：2026-10-19。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `overlay.modal.notice.open`：可见、标题“提示”、正文“操作已完成”、宽 320px、无关闭按钮、无页脚，遮罩开启。以官方 Modal 的 `ivu-modal-content` 为组件根捕获，真实浏览器内容框 320×104px；标题区 51px，正文区 53px，白底、6px 圆角、`rgba(0,0,0,.15) 0 4px 12px` 阴影。源码 `modal.vue`、`modal.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-088/modal-source)。遮罩属于周边页面状态，不在此固定内容组件根截图中。

本任务把 `Modal` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Modal"})` 无问题；截图人工确认标题、正文与分隔线完整，来源测试通过。

当前来源证据不代表正式准入或 V0.2 发布就绪。
