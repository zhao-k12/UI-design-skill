# TASK-063 — Radio 固定选中态官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；双端默认字体候选、Fidelity Gate 与 Registry 准入均 `NOT_RUN`。

依赖 View UI Plus 1.3.24 已锁定源码与浏览器运行器。仅抽取 `form.radio.default.enabled`：`modelValue=true`、`trueValue=true`、`falseValue=false`、`disabled=false`、`size=default`、`border=false`，固定文字“启用”。官方 `radio.vue` 和 `radio.less` 文件哈希写入观察证据，禁止自定义 CSS 覆盖。Component IR/DOM 外框为 48×21px；由于根节点的分数坐标，浏览器元素截图实际为 48×22px，额外包含顶部 1 行空白。原生圆形控件为 16×16px，蓝色边框 `#2D8CF0`、白底，`::after` 为 10×10px 蓝色圆点；控件相对根节点顶部 2.375px，文字起点 x=20px。CDP 观察到中文由 PingFang SC Regular 渲染。

[来源证据](../artifacts/task-063/radio-source)包含官方浏览器截图、完整 Component IR、运行环境、源码哈希、Manifest 和观察记录。`verify_artifacts(..., expected_types={"Radio"})` 无问题；Component IR/架构 12 项与运行提取 3 项回归通过。截图人工查看标记和两字完整可见。

该证据只作为候选设计的来源，不代表 Figma/Penpot 原生保真或准入。下一步建立两端默认字体原生组件，再执行独立 Fidelity Gate。
