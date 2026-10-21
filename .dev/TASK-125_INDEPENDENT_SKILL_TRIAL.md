# TASK-125 — 旧原型、全新任务目录的 Skill 试跑

## 输入隔离

本次只从 `examples/workflow-v03-smoke-figma/prototype.txt` 复制原始原型文字到 `artifacts/task-125/source/prototype.txt`，SHA-256 为 `a112c269ea5fe956007818e52456fb86bb5ce07da14c9e11bed33d922c17b954`。新建语义观察、Page Tree、审核回执、布局意图和布局计划；未读取 TASK-122 的 Tree、计划、Core 输出、Figma 节点或 QA 回执作为本次输入。正式 V0.2.7 组件库、V0.2.2 Token 及 V0.3.2 页面规则仍作为设计约束读取。

## 本次真实结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 原型语义结构与七项内容审核 | PASS | `artifacts/task-125/structure_qa_report.json`、`page_content_tree_review.json` |
| 新布局意图与独立 Core 几何试算 | Core PASS；使用明确标记的 test-fixture 尺寸，仅用于质量门测试，不是生产测量 | `artifacts/task-125/layout_intent.json`、`layout-plan.json`、`layout_qa_report.json` |
| V0.3.2 规范化布局质量门 | FAIL：1840 px 列表内容区需要同宽 Table，正式组件仅准入 1392 px | `artifacts/task-125/staged/layout_quality_qa.json` |
| iView 资源只读预检 | FAIL：四项页面色彩 Token 不符；正式 Table `showHeader=false` | `artifacts/task-125/iview_resource_preflight.json`；此项不是完整原生 iView QA |
| 原生骨架入口 | BLOCKED；未创建本次 Figma 页面 | `artifacts/task-125/stage_gate_result.json` |

新意图已给页头、查询区和列表区各边 16 px 内边距，Table Cell 填满 1840 px 内容区；不能把 1392 px 的固定官方实例拉伸到该尺寸。`layout-qa` 对新任务产物实际返回 FAIL，原生阶段入口拒绝继续。旧问题中的零区域内边距与随意右侧留白没有进入本次候选布局。

这次是**阻断路径的独立试跑**，不是五步原生交付。尚需从锁定 View UI Plus 源取得 1840 px、带三列表头与固定三行数据的 Table，完成 Figma 默认字体改编、正式保真准入及新版本 Registry/绑定；同时迁移与 iView 对齐的页面色彩 Token。之后必须从这份原型重新运行正式 Core、独立原生骨架/默认文案页/填入页及最终校对，不得引用 TASK-122 候选页面作为本次完成证据。Penpot 继续搁置。
