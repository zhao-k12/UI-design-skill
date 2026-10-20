# TASK-097 — Cascader 固定地区选中态官方运行来源锁

日期：2026-10-20。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `form.cascader.region.selected`：浙江→杭州两级数据、值 `zhejiang/hangzhou`、展示“浙江 / 杭州”、下拉关闭、不可清空、未禁用。真实浏览器输入框 240×32px，白底、1px `#DCDEE2` 实线、4px 圆角，右侧 14×14px 官方箭头。源码 `cascader.vue`、`cascader.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-097/cascader-source)。

本任务把 `Cascader` 加入 Component IR 的允许类型；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Cascader"})` 无问题；截图人工确认两级展示文字与箭头完整，来源测试通过。

当前来源证据不代表正式准入或 V0.2 发布就绪。
