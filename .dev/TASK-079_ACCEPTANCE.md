# TASK-079 — Tree 固定展开结构官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

锁定 View UI Plus 1.3.24 `navigation.tree.expanded.departments`：展开父节点“部门”，子节点“研发部”“设计部”，无复选框、未选中。真实浏览器根框 240×79px；三行标题相对 y=0、29、58，子节点缩进。父节点展开箭头由官方 `ivu-icon-ios-arrow-forward` 图标字体旋转显示，两个叶节点没有可见箭头。源码 `tree.vue`、`node.vue`、`tree.less` 哈希、浏览器截图、DOM、Component IR、运行环境和 Manifest 存于 [来源证据](../artifacts/task-079/tree-source)。

本任务把 `Tree` 加入 Component IR 的允许类型，解决来源证据原先因契约缺项无法验证的问题；不改 Core 或正式 Registry。`verify_artifacts(..., expected_types={"Tree"})` 无问题；截图人工确认三行文字及展开箭头完整，来源测试通过。

后续 Figma 候选的功能箭头须使用仓库已同步的真实 Remix Icon 组件，并明示与官方图标字体的视觉改编。当前来源证据不代表正式准入或 V0.2 发布就绪。
