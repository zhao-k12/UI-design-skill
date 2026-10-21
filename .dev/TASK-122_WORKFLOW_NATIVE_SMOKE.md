# TASK-122 — 独立原型的 V0.3 主流程实跑

> **更正（2026-10-21）**：下表只记录旧 V0.3 流程的内容与原生执行门。用户明确要求按 iView 设计规范验收后，新增的规范审计对本页给出 **FAIL**：4 项基础色彩 Token 不一致，且表头是拼接文字，不是原生带表头 Table。此前“可交付”的判断撤回；本页保留为问题复现样张，不能作为符合 iView 规范的最终页面。详见 [TASK-123](TASK-123_IVIEW_CONFORMANCE_CONFLICT.md)。

本次自写原型为[用户管理｜组件流程验证页](../examples/workflow-v03-smoke-figma/prototype.txt)，语义结构经用户批准。组件范围限定为当前已准入的 Input、Select、Button、Table 固定配置和设置图标；无范围字段、导出、交互或额外业务数据。Penpot 线按用户决定继续搁置。

| 阶段 | 结果 | 原生证据 |
| --- | --- | --- |
| 原型 → 统一内容 Tree | PASS；7 个语义项，逐项核对内容与完整性 | `artifacts/task-122/staged-r2/page_content_tree.json`、`page_content_tree_qa.json` |
| 彩色组件骨架页 | PASS；7 个语义单元的类型、颜色、位置、尺寸、标签独立读回 | [Figma 骨架页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=259-2)、`artifacts/task-122/skeleton.png` |
| 默认文案组件页 | PASS；与骨架分开保留，5 个原生实例连接主组件；8 处独立文字为“文本” | [Figma 默认组件页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=261-2)、`artifacts/task-122/default.png` |
| 填入原型文案 | PASS；8 处文字独立读回完全匹配，5 个实例连接保持完整 | `artifacts/task-122/fill-readback.json` |
| 最终原型校对 | PASS；7 个原型语义项逐项核对，全页 1920×1080 原生 PNG 哈希锁定 | [Figma 最终页面](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=261-3)、`artifacts/task-122/final-native.png` |

Core 九阶段和 Figma 预检通过；`tests/test_revised_flow.py` 的 5 项定向回归通过。这些检查不覆盖 iView 页面规范。彩色骨架当前按源语义单元标注，页头文字与设置图标位于同一个标注单元；实际默认页和最终页中的设置图标是独立的 Figma 原生组件实例。

输入包由 `scripts/prepare_workflow_v03_smoke.py` 的 `draft` 和 `finalize <review.json>` 两步创建。新原型的语义审核回执绑定分析哈希，历史冻结输入与旧页面未覆盖。独立执行和读回证据保存在本地忽略目录 `artifacts/task-122/`。
