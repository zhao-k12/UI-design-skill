# TASK-067 — Switch 固定选中态官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；双端默认字体候选、Fidelity Gate 与 Registry 准入均 `NOT_RUN`。

仅抽取 View UI Plus 1.3.24 的 `form.switch.default.enabled`：`modelValue=true`、`trueValue=true`、`falseValue=false`、`disabled=false`、`size=default`、`loading=false`，固定 open slot 文字“开”。官方 `switch.vue` 和 `switch.less` 文件哈希写入观察证据，未覆盖官方 CSS。Component IR/DOM 外框 44×22px，浏览器元素截图 44×23px，最后一行全白。选中态背景和边框为 `#2D8CF0`；白色滑块 18×18px、相对左 23px、上 1px；文字 12px、白色、左 7px。CDP 显示中文由 PingFang SC Regular 渲染。

[来源证据](../artifacts/task-067/switch-source)包含官方浏览器截图、完整 Component IR、运行环境、源码哈希、Manifest 和观察记录。`verify_artifacts(..., expected_types={"Switch"})` 无问题；Switch 来源、Component IR、Radio Gate 和浏览器提取回归通过。截图人工查看开关及“开”字完整可见。

该证据只作为候选设计的来源，不代表 Figma/Penpot 原生保真或准入。下一步建立两端默认字体原生组件，再执行独立 Fidelity Gate。
