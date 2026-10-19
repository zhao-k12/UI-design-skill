# TASK-085 — Form 单字段官方运行来源锁

日期：2026-10-19。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `form.single.name.empty`：单行 FormItem 标签“姓名”，labelWidth 80、右对齐；Input 空值、占位“请输入姓名”、不可清除。真实浏览器根框 320×34px，标签宽 80px，输入宽 240×32px，位于根框相对 x=80。源码 `form.vue`、`form-item.vue`、`form.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-085/form-source)。

本任务把 `Form` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Form"})` 无问题；截图人工确认标签与占位完整，来源测试通过。后续 Figma 候选应复用已经准入的固定“请输入姓名” Input 原生组件实例。

当前来源证据不代表正式准入或 V0.2 发布就绪。
