# TASK-094 — Upload 固定拖拽空态官方运行来源锁

日期：2026-10-20。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `data.upload.drag.empty`：拖拽类型、空文件列表、单文件、文案“上传文件”、未禁用。使用固定 320px 容器和 80px 高的全宽居中槽内容，官方 Upload 自身提供 1px 虚线边框与 4px 圆角，真实浏览器外框为 320×82px。`action=/upload` 仅满足官方必填属性；验收不触发上传或网络请求。源码 `upload.vue`、`upload.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-094/upload-source)。

本任务把 `Upload` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Upload"})` 无问题；截图人工确认居中文字与虚线边框完整，来源测试通过。

当前来源证据不代表正式准入或 V0.2 发布就绪。
