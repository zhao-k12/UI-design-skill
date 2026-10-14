# UI Design Skill V0.2 — Autonomous Development Plan

状态：IN PROGRESS（限定范围，未发布）。本文仍是完整目标计划，不表示各阶段均已实现，也不授权启动后台任务。当前已实现范围由 README、正式 Registry、[开发状态](../.dev/DEVELOPMENT_STATE.md) 和 [发布就绪审计](V02_RELEASE_READINESS.md) 限定。

## 项目目标

输入静态页面原型，结合AI语义理解、设计系统约束、正式组件库和布局模式，通过确定性生成输出1920宽B端静态设计稿。Figma和Penpot均支持原生可编辑稿、真实组件/图标实例、结构追溯、中间产物检查和断点恢复。一次生成使用用户选定的平台。

画布草案为默认1920×1080、高度至少1080。长内容采用增高还是静态滚动展示仍须明确。

## 架构原则

2026-10-12 字体选择已明确：新设计使用 Figma 和 Penpot 各自的原生默认字体，不要求本机安装或上传苹方。实际默认字体在目标会话解析与测量；详见 [字体政策](FONT_POLICY.md)。涉及已有组件字体改变的配置在新版本重新验收。

1. 原型必须经过Analysis、Page Tree、Skeleton、Component Mapping、UI-IR和Adapter；AI不直接画最终UI。
2. Core保持平台无关，SDK和真实节点引用只在Adapter。
3. 规范组件提前建设；页面生成只消费已准入Registry，不临时复刻控件。
4. 官方源码、CSS、真实运行结果生成Component IR，Fidelity Validation通过后准入。
5. Skeleton先生成并通过布局检查，再组装组件；布局不得由组件任意反向决定。
6. “无自由坐标”禁止AI随意指定坐标；布局程序计算、Adapter写入坐标仍是必要步骤。
7. 只处理静态设计；规则修正不得擅自增加业务字段、操作、页面或交互。
8. 未执行检查不算PASS，模拟结果不替代真实实例、独立读取或原生PNG。

## 统一阶段与完成条件

原草案总流程和章节编号不一致，以下将模式与布局合并为C，保留H为端到端验收。实施前须确认这项阶段整理。

| 阶段 | 开发范围 | 完成条件 |
|---|---|---|
| A 基础架构 | UI-IR、Design Manifest、Development State、版本锁和恢复 | 契约、校验与恢复可执行；既有能力先核对复用，新增字段不等于原生能力已实现 |
| B 设计资产 | 官方组件提取、Component IR、保真、Registry；Remix同步与索引 | 覆盖矩阵内各配置真实准入，来源、限制与两平台证据完整 |
| C 模式与布局 | 页面/Section/Table模式、Canvas政策、24栅格、Skeleton和Layout QA | 支持模式可确定性组合，间距、宽度、裁剪、密度与溢出检查通过 |
| D 原型理解 | 图片原型分析、页面类型、区域、字段、操作、数据区域和假设层 | 来源明确，设计默认与业务缺失区分，已有内容不被替换 |
| E 页面生成 | Analysis→Page Tree→Skeleton→Mapping→Assembly→Content Injection | 仅使用正式组件，结构与内容完整，UI-IR有效 |
| F 规则与质量 | 间距、密度、对齐、层级、色彩、信息结构与规则修正 | 有规则来源、变更账本和复验，不擅改业务语义，不扩大像素容差 |
| G 平台输出 | 用户选择Figma或Penpot，Adapter消费共同UI-IR契约 | 原生可编辑、真实实例、完整创建/修改账本、独立读取与PNG通过 |
| H 端到端验收 | 从新原型到最终目标文件的全链路，两平台分别验证 | 全部Release Gate实际通过，产物、版本、文档完整后发布V0.2 |

## A：基础结构

UI-IR目标支持Page、Frame、Section、Grid、Row、Column、Stack、Text、Component Instance、Icon Instance、Image。扩展前核对现有Schema与执行能力；原生Image等未准入能力须有真实Adapter验收。

Design Manifest记录Skill、UI-IR、Component、Token、Layout/Rule、Icon和Adapter版本，以及输入/程序/产物指纹。Development State记录阶段、已完成模块、检查状态、依赖、下一动作和暂停/冲突状态。

## B：设计资产

18类目标组件：Button、Input、Select、DatePicker、Checkbox、Radio、Switch、Tag、Table、Pagination、Card、Tabs、Form、Modal、Drawer、Upload、Tree、Cascader。

每项记录组件ID、Variants、States、Props、Usage Rules、禁止场景、支持尺寸、源码/CSS/运行环境版本、字体/图标依赖和两平台准入状态。

“完整组件库”以覆盖矩阵定义，不代表全部Props的笛卡尔积。首版状态、尺寸、配置和嵌套范围仍需确认；已有正式准入资源先核对复用，未支持组合继续Missing/Unsupported。

Remix图标系统包含自动同步、版本管理、语义匹配、哈希与增量差异；同步不得自动升级旧任务版本锁或覆盖原生实例。

## C：模式和Canvas

- Layout Pattern：List Page、Detail Page、Form Page、Dashboard、Workspace、Sidebar Layout。
- Section Pattern：Search Panel、Filter Bar、Toolbar、Table Section、Detail Card、Statistics Card、Form Section。
- Table Pattern：Standard、Wide、Tree、Expandable、Report Table。
- 默认草案：Header64px、Sidebar200px、Content Padding24px、Grid24列。
- 布局流程：Prototype→Page Structure→Layout Pattern→Layout Skeleton→Layout Validation→Component Assembly。

新默认值属于新版本政策，不覆盖旧任务冻结Token。树表、展开表、横向滚动与固定列需要明确静态状态，不自动扩展为业务交互。

## D：Design Assumption Layer

| 内容情况 | 处理方式 |
|---|---|
| 原型/用户已给内容 | 精确保留并记录来源 |
| 影响页面任务的业务缺失 | 询问必要信息，不猜造业务含义 |
| 设计缺失 | 在已批准规则与Token范围自动补齐，记录依据 |
| 数据缺失 | 生成明确标记的模拟数据，不伪称真实记录 |
| 静态稿无接口 | 不询问数据接口，不建设后台业务系统 |
| 只显示10行而未给分页总量 | 按统一演示政策处理，不推断真实总条数 |

假设记录字段、值、分类、来源规则、适用范围和覆盖条件。页码、pageSize、总量和日期的确定性演示政策仍需确认；明确给出的值始终优先。

## E–F：生成与视觉修正

缺失数据可以生成编号、名称、状态、时间，但须满足组件可配置契约及语义要求。不能借自动填充修改已有内容。

宽表可以按已批准规则选择静态横向滚动区域或固定列配置。Detail View属于新增结构，应先记录建议或取得相应授权。缺失规则记录missing_rule并进入规则补充，不用自由设计填补。

## 自动开发与恢复

开发获授权后，每次启动读取Development State、ARCHITECTURE.md、CONSTRAINTS.md和本计划，核对当前阶段、依赖、版本锁与暂停状态。

在授权范围内执行未完成部分，检查通过后保存产物、QA、状态和Commit，再进入下一阶段。每个完成记录含版本、输入指纹、实际检查命令、结果、产物位置和下一动作。

架构冲突记录ARCHITECTURE_CONFLICT，包含当前设计、原因、影响和建议；暂停依赖变更，独立工作可继续。缺少组件记录missing_component并返回B；缺少规则记录missing_rule并返回对应规则建设。

Checkpoint绑定输入、代码、配置和产物字节。变化仅失效受影响阶段及下游；保留Section边界。导出失败保留PARTIAL。恢复既有画布先独立核对账本和状态，不重复创建。

用户暂停即停止开发并保存状态，恢复需要明确指示。自主推进指获授权的执行期间自动衔接阶段，不默认设置定时任务、后台服务或对话之外的持续运行。

## 迁移与Release Gate

V0.2采用新计划、版本锁和验收目录，不自动重写V0.1历史批准、源码、组件、Token、布局或Adapter锁。新默认值与自动假设政策明确版本及迁移范围。

最终验收包含：原型来源与分析、结构/假设完整性、确定性布局、正式组件/图标、内容完整性、可编辑性、真实主组件关联、合法字体、无溢出、完整原生PNG、独立读取、实际视觉复核、断点恢复和版本追溯。

日常生成只输出所选平台；V0.2发布分别验证两个Adapter。代码测试、JSON、预检或批准提案本身均不等于原生最终验收。

## 实施前待决策

1. 统一A–H阶段划分。
2. 长页增高/静态滚动展示政策及选择条件。
3. 18类组件首版变体、状态、尺寸和配置覆盖矩阵。
4. 分页、模拟数据与时间的确定性默认值。
5. 图片识别能力与低置信度复核机制。
6. 新自动假设/语义处理与现有人工批准门的迁移边界。
7. 视觉优化增加Detail View等结构的授权边界。

本次仅整理和公开计划，待决策项不视为已获实施批准。
