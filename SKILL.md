---
name: ui-design-skill
description: Assemble editable static UI designs from prototypes through source-bound semantic review, deterministic layouts, admitted components, platform-neutral UI-IR, and Figma or Penpot adapters. Use for this static design pipeline and its development.
---

# UI Design Skill

读取 [开发状态](.dev/DEVELOPMENT_STATE.md)、[架构](ARCHITECTURE.md) 和 [约束](CONSTRAINTS.md)。V0.1 的具体验收范围及命令见 [流水线使用说明](core/pipeline/README.md)。AI 负责理解和选择，程序负责布局与执行，官方组件负责视觉真值。公开环境与证据边界见 [发布说明](docs/PUBLICATION.md)。

## 生成静态设计

1. 阅读原型，按 [观察流程](core/prototype/README.md) 保存有实际文字来源、引用及精确位置的 observations；只提取页面任务、Section、字段、按钮、数据与静态内容。截图先准备并核对转录，当前无自动 OCR。不在语义阶段选择视觉样式或组件。
2. 运行分析和 Page Tree 检查，提供具体语义复核稿。只在用户批准该稿且当前来源、分析及 review 指纹重新通过后冻结结构；已有对应批准可复用，内容改变则重新复核。未知项保持 Review，不替用户批准。
3. 提供标准 Pattern 映射、来源绑定的实际测量、显式组件决策和内容契约；运行 `scripts/run_pipeline.py`。前一门失败时停止依赖阶段。它保存中间 JSON、标注、manifest、checkpoint、最终 UI-IR 和两平台预检计划。
4. 通过实际可用的 Adapter 主机执行 UI-IR：保存完整实际创建／修改节点账本，保持官方组件和图标为真实关联实例。随后用独立读取及原生导出验证，不能将执行时的自报结果充作独立证据。Figma 主机操作前读取对应能力指南；Penpot 使用公开插件 SDK。
5. 检查内容遗漏、组件类型／Variant、图标来源、栅格、间距、文字与组件溢出、真实可编辑性和完整截图，进行实际视觉复核。按使用说明运行最终证据检查。只有全部 Release Gate 通过才报告 V0.1 Ready。

只使用正式准入 Registry 和锁定的 Token／Remix 版本。静态文字与布局原语可按显式契约组合；不得用它们模拟缺失官方控件。缺失记录 Missing，不确定记录 Review，不支持记录 Unsupported；不得偷偷替换原型内容、图片、字体、图标或组件。组件保持来源尺寸，不为填满 Cell 拉伸。当前原生 Image 未准入。

Core 不接触平台 API 或节点 ID，平台引用只留在 Adapter Metadata 和实际证据中。不得绕过 UI-IR、Validator 或原生保真门。当前正式组件及示例目标文件已列在流水线说明；其他文件的真实引用须重新预检，不能照搬示例 ID。

每个任务锁定版本并保存 checkpoint；输入或映射变化从受影响阶段恢复，组装保留 Cell ID／box，只声明受影响 Section。版本／程序迁移使用新任务目录，不能自动升级已有锁。原生导出失败保存 PARTIAL，只有同 revision、同实际节点状态允许复用成功格式。实际截图仍须原生 PNG。

已批准的 AD-017 允许有完整几何、样式、字体、轮廓、基线、独立向量及边缘证据的栅格差异；两份 Remix 图标另使用已批准的精确 Float32 路径规则。适用范围以 [.dev/TASK-009_FIDELITY_DECISION.md](.dev/TASK-009_FIDELITY_DECISION.md) 和 TASK-010 决策文件为准。不能引入宽泛容差、覆盖历史失败或把批准本身当作验收。

## 继续开发

新未完成开发内容见 [V0.2自主持续开发计划](docs/DEVELOPMENT_PLAN_V0.2.md)，状态为PLANNED。用户明确授权开发后按阶段依赖推进，先核对复用已有能力。历史 [.dev/BUILD_PLAN.md](.dev/BUILD_PLAN.md) 是V0.1架构来源，不是新版本未完成队列。运行检查和实际验收，保存产物、状态和Commit后进入下一阶段。发现冻结架构冲突，记录当前设计、原因、影响和提案；在决策明确前停止依赖变更。能力变更重新说明范围并实际验证，不以临时Demo或模拟平台输出宣称完成。尊重暂停，不因读取计划而启动后台任务。
