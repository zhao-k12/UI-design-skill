# TASK-016 验收

Asset Registry 覆盖 logo/avatar/photo/banner/illustration/background/empty-state 七类现有业务资源。每项绑定逻辑 ID、来源引用、声明根内的相对文件、完整字节 SHA、静态媒体类型及原尺寸；每次解析重新读文件。不增加任何业务图片，正式目录保持空。

顺序为原型资源 → 登记资源 → missing_asset。原型提供的同 ID 文件若损坏、字节/尺寸不符或越界，直接 FAIL，不静默退回其他图。当前支持 PNG/JPEG/WebP 静态文件，SVG 与动画不在此解码范围。资源通过不代表历史适配器具备 Image 原生执行能力。

UI-IR 增加封闭 resourceIssues，可表示 missing_component、missing_icon、missing_asset、unsupported_component。结构 Schema 接受诊断；validate_document 返回原有问题码，因此双平台 compiler 在任何写入前拒绝这些输入。没有 Missing 图形占位或伪 Logo。

实际 CLI 对已冻结的列表 UI-IR 输出 resource-resolution.json：PASS、resolvedAssets 为空，因为该列表没有图片需求。七项测试验证优先级、输入隔离、七类别、哈希/尺寸/媒体/路径篡改、重复 ID、Missing/Unsupported 传播、过期成功输出失效及输入保护。测试小图片明确为本地合成测试资源，不登记为正式业务资源。

使用说明见 core/asset-resolver/README.md。最终完整回归与架构检查见 DEVELOPMENT_STATE.md；通过后提交 TASK-016 并进入端到端流程。
