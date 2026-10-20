# TASK-108 — 独立紧凑用户管理原型的 Figma 端到端验收

日期：2026-10-20。状态：**FIGMA_INDEPENDENT_E2E_PASS / RELEASE_NOT_READY**。

用户明确选择基于既有用户管理主题制作另一份独立原型，并批准了本任务的具体语义：姓名与状态同排、查询按钮独立右对齐；保留固定三行用户表格和汇总，去掉范围字段与导出。新的 [原型](../examples/user-management-compact-search/prototype.txt)与[来源标注](../examples/user-management-compact-search/observations.json)绑定独立文档 ID 和源码哈希；[用户审核回执](../examples/user-management-compact-search/review.json)绑定语义分析哈希。结构 QA PASS，不借用旧原型的人工审核回执。

[输入构建器](../scripts/build_v02_compact_search_input.py)仅复用字面内容与固定组件完全相同的原生测量，记录旧证据字节锁；新语义、新布局和输入 Manifest 单独生成。首次组装正确拒绝旧样张遗留的“操作”标签，修正为原型中的按钮本身，并采用已准入 60×32 尺寸。布局计划新增受限的按钮行 `buttonAlignment=end`，由 Layout Engine 计算位置，无自由坐标。九阶段 Core、Figma/Penpot 静态预检均 PASS；第二次运行九阶段全部从 Checkpoint 复用且字节锁不变。新 UI-IR SHA-256 为 `6e3768d799efb28b01e7e02e80dc8bfd5b5feee2ba598bc379cf28f4f598ae65`，区别于冻结列表。

Figma 新页 `240:2` 按当前锁定脚本实际创建 1920×1080 原生可编辑稿；[完整执行回执](../artifacts/task-108/figma-execution/execution-result.json)为 PASS，37 项节点映射和执行证据。独立 [节点读回](../artifacts/task-108/figma/native-read.json)和[布局几何读回](../artifacts/task-108/figma/layout-read.json)确认 5 个真实实例（4 个组件、1 个 Remix 图标）、21 个文字节点；输入和选择框同排，查询按钮下一行且右边缘与按钮行右边缘相等。两次[原生 PNG](../artifacts/task-108/figma/native.png)完全同字节，SHA-256 为 `71afd671d755ca36569f031df262f295472ea7d4374b49c7033157efa8ffedfc`。目视复核文字、三行表格、汇总和按钮完整，无旧“范围/导出/操作”内容。[独立机器审计](../artifacts/task-108/independent-figma-qa.json) PASS，按钮几何篡改测试 FAIL 如预期。

测试：`tests.test_layout_builder`、`tests.test_v02_compact_search_figma`、`tests.test_v02_current_readiness` 共 13 项 PASS；`tests.test_pipeline` 与 `tests.test_v02_pipeline_profile` 共 11 项 PASS。新的[当前就绪汇总](../artifacts/task-108/current-release-readiness.json)记为 Figma 独立原型端到端 PASS、Penpot DEFERRED、全量发布 NOT_READY。此原型的组件/字体测量复用已锁定的同字面内容证据，没有声称独立产生新的官方组件来源；Penpot 原生执行和其余 11 类组件双端准入仍待恢复。
