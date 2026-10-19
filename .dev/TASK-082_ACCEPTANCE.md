# TASK-082 — DatePicker 固定日期官方运行来源锁

日期：2026-10-19。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `form.datepicker.date.selected`：日期类型、固定值 `2024-01-01`、`yyyy-MM-dd`、默认尺寸、不可清除、只读且面板关闭。真实浏览器根框 211×32px；输入文字 `#515A6E`，白底、`#DCDEE2` 1px 边框、4px 圆角；右侧日历轮廓图标来自官方 Ionicons，Figma 候选须以仓库已同步的真实 Remix Icon 组件进行明确视觉改编。源码 `picker.vue`、`date-picker.js`、`date-picker.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-082/datepicker-source)。

本任务把 `DatePicker` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"DatePicker"})` 无问题；截图人工确认固定日期和日历图标完整，来源测试通过。

当前来源证据不代表正式准入或 V0.2 发布就绪。
