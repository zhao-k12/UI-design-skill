# V0.1 Architecture Baseline

基线来源：用户 UI Design Skill — V0.1 BUILD PLAN，完整副本见 [.dev/BUILD_PLAN.md](.dev/BUILD_PLAN.md)。本次冻结职责与依赖方向，不在 TASK-001 定义 UI-IR 字段或实现后续任务。

## 依赖边界

```text
Prototype → Understanding → Page Tree → Structure QA
→ Layout Tree → Layout Skeleton → Layout QA
→ Component Mapping → Annotation → Assembly
→ Icon / Asset Resolution → Content Injection → Design Rules
→ UI-IR → Figma Adapter / Penpot Adapter → Final QA
```

AI 仅产出阶段判断；程序执行布局、解析、组装和翻译。Core 只依赖平台无关的数据契约、逻辑 Registry 和规则，不依赖平台 SDK 或 Adapter。平台原生 ID 与组件引用存放在各 Adapter 的 metadata 区域；逻辑 Registry 通过逻辑 ID 与其关联，Core 不读取平台引用。

Component Builder 从官方真实浏览器运行结果提取 Component IR，经过 Fidelity Gate 后登记。Icon Manager 同步官方 Remix Icon，维护版本、哈希、增量差异和语义索引；删除项标记 deprecated，保留历史引用。实际设计组件的建立和平台引用归 Adapter 所有，不把平台模型写进 Component IR。

## 目录职责和实施任务

| 路径 | 职责 | 任务 |
| --- | --- | --- |
| core/prototype/ | 仅理解静态原型语义，不选组件或视觉参数 | 011 |
| core/page-tree/ | Page Tree、来源映射与冻结 | 012 |
| core/layout/ | 标准 Pattern、24 Grid、确定性布局与 Skeleton | 004, 013 |
| core/component-resolver/ | 逻辑组件选择、标注、槽位组装和内容注入 | 014, 015 |
| core/icon-resolver/ | 图标语义匹配和显式 no_icon | 008, 015 |
| core/asset-resolver/ | 已有业务资产解析与 Missing | 016 |
| core/design-rules/ | Token 与已锁定规则检查 | 003, 013, 017 |
| core/pipeline/ | 阶段编排、版本锁、Checkpoint、Resume | 017 |
| schemas/ | 平台无关阶段 JSON 契约，UI-IR 从 002 开始 | 002, 011–017 |
| registries/components/ | 逻辑组件、变体、槽位、保真准入记录 | 005, 007 |
| registries/icons/ | 图标逻辑 ID、语义、来源和版本 | 008 |
| registries/assets/ | 非组件非图标业务资源 | 016 |
| registries/tokens/ | Color、Typography、Spacing 等 Token | 003 |
| component-builder/source-reader/ | 官方源码与 CSS 版本读取 | 006 |
| component-builder/runtime-renderer/ | 官方组件真实浏览器运行 | 006 |
| component-builder/style-extractor/ | Computed Style、DOM、几何信息 | 006 |
| component-builder/component-ir/ | 平台无关 Component IR | 006 |
| component-builder/fidelity-gate/ | 几何和截图差异，PASS 准入 | 007 |
| icon-manager/remix-sync/ | 官方同步、哈希和增量更新 | 008 |
| icon-manager/manifest/ | 图标版本快照 | 008 |
| icon-manager/semantic-index/ | 官方及自定义中文标签 | 008 |
| adapters/figma/ | UI-IR → Figma 原生布局和真实实例、平台 metadata | 009 |
| adapters/penpot/ | 同一 UI-IR → Penpot 原生设计、平台 metadata | 010 |
| validators/ | 初始 Core 架构静态检查 | 001 |
| validators/structure/ | 原型、Section、字段和按钮完整性 | 012 |
| validators/layout/ | span、溢出、宽度、padding、间距和嵌套 | 004, 013 |
| validators/component/ | 登记、类型、变体和实例检查 | 014, 017 |
| validators/completeness/ | 输出与原型来源对照 | 017 |
| validators/visual/ | 视觉差异、文字溢出和一致性 | 007, 017 |
| artifacts/ | 每任务版本锁、阶段产物和 QA；运行数据默认不入 Git | 017 |
| examples/ | 最小用户管理静态原型和可复用输入 | 002, 017 |
| tests/ | 可离线执行的架构与后续任务测试 | 001–017 |
| .dev/ | 基线、开发状态、验收和架构决策 | 每个任务 |

空目录的 `.gitkeep` 只保证目录可随仓库交付，不表示模块已实现。

## 阶段产物与失败策略

每个任务至少保存 prototype_analysis.json、page_tree.json、layout_tree.json、component_mapping.json、ui_ir.json、qa_report.json、manifest.json；相关阶段另存 structure_qa_report.json、layout_qa_report.json、component_fidelity_report.json、final_ui_ir.json，以及标注和检查点。具体 Schema 在相应任务定义，不在初始化阶段造示例 PASS。

确定则执行；标准规则能确定则用规则；不确定记录 Review；资源缺失记录 Missing；平台不支持记录 Unsupported。质量门成功后才保存成功 Checkpoint。恢复从受影响的 Page Tree、Layout 或 Mapping 等阶段开始，失效其依赖结果。平台支持差异由 Adapter 报告，不修改 Core UI-IR。

## 版本与验收

开发版本为 `0.1.0-dev`。TASK-001 的技术选择是 Python 3.11+ 标准库测试与静态架构检查，无第三方依赖；这是开发工具选择，不改变平台无关的数据边界。后续平台调用的具体执行载体由 Adapter 任务确定。

首次验收闭环必须是同一 UI-IR 在 Figma/Penpot 中产生基本一致的原生可编辑列表页，Button/Input/Select/Table/Icon 为真实实例。仅生成 JSON、命令计划、模拟设计或 Rectangle + Text 不满足验收。TASK-017 必须逐项执行完整 Release Gate，不能依据初始化测试宣称发布就绪。

ARCHITECTURE_CONFLICT 必须先记录到开发状态，包括当前设计、原因、影响和建议；等待明确架构决策再执行相关变更。
