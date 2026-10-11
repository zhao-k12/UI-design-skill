# UI Design Skill — V0.1 BUILD PLAN

## 0. 项目目标

开发一个平台无关的 UI Design Skill。

用户输入静态页面原型后，系统按照固定流水线：

```text
Prototype
↓
Prototype Understanding
↓
Page Tree
↓
Structure QA
↓
Layout Tree
↓
Layout Skeleton
↓
Layout QA
↓
Component Mapping
↓
Component Annotation
↓
Component Assembly
↓
Icon / Asset Resolution
↓
Content Injection
↓
Design Rules
↓
UI-IR
↓
┌───────────────┬───────────────┐
│ Figma Adapter │ Penpot Adapter│
↓               ↓
Figma Design    Penpot Design
↓               ↓
Final QA
```

最终输出：

- 原生可编辑静态设计稿
- 使用真实组件实例
- 使用真实图标组件
- 页面结构可追溯
- 中间阶段可检查
- 中间阶段可回退
- Figma / Penpot 共用同一套核心逻辑

---

# 1. 核心原则

## 1.1 AI 不直接画 UI

禁止：

```text
Prototype
→ AI
→ 直接生成最终设计页面
```

必须经过：

```text
理解
→ 结构
→ 布局
→ 组件映射
→ UI-IR
→ Adapter
```

AI负责判断。

程序负责执行。

---

## 1.2 一个 Skill，多个 Adapter

核心系统禁止依赖：

```text
Figma Node Model
Penpot Object Model
```

核心系统只允许依赖：

```text
UI-IR
```

最终由：

```text
adapters/figma/
adapters/penpot/
```

负责转换。

未来允许增加：

```text
adapters/mastergo/
```

而无需修改核心推理流程。

---

## 1.3 官方组件不是由 AI 复刻

禁止：

```text
官方文档
→ AI理解
→ AI重新画组件
```

必须：

```text
官方源码
+
官方 CSS
+
真实浏览器运行结果
↓
Component IR
↓
Design Component
↓
Fidelity Gate
↓
Component Registry
```

官方真实运行结果是组件视觉唯一真值。

---

## 1.4 AI 不创建未登记组件

组件调用优先级：

```text
现有区块组件
↓
现有组合组件
↓
现有基础组件
↓
由已有组件组合
↓
Missing Component
```

禁止 AI 临时画一个“类似组件”。

---

## 1.5 图标统一使用 Remix Icon

流程：

```text
Remix Icon Official Source
↓
Icon Sync
↓
Icon Component Library
↓
Icon Registry
↓
Semantic Resolver
↓
Component Slot
```

AI禁止自行绘制系统功能图标。

---

## 1.6 每个阶段必须有确定性产物

至少保存：

```text
prototype_analysis.json
page_tree.json
layout_tree.json
component_mapping.json
ui_ir.json
qa_report.json
manifest.json
```

禁止只把中间状态保存在 LLM 上下文。

---

# 2. 第一阶段成功标准

V0.1 不追求复杂 Design Brain。

先证明最小闭环：

```text
简单静态原型
↓
Page Tree
↓
Layout Tree
↓
Input / Select / Button / Table 映射
↓
UI-IR
↓
Figma
+
Penpot
```

要求：

同一份 `ui_ir.json` 可以被两个 Adapter 消费。

最终产生结构基本一致的：

```text
Figma 可编辑设计稿
Penpot 可编辑设计稿
```

并且：

- Button 是组件实例
- Input 是组件实例
- Select 是组件实例
- Table 是组件实例
- Icon 是图标组件实例
- 不是 Rectangle + Text 的伪组件

这是 V0.1 第一核心验收条件。

---

# 3. 推荐目录结构

```text
ui-design-skill/
│
├─ SKILL.md
├─ README.md
├─ VERSION
│
├─ core/
│  ├─ prototype/
│  ├─ page-tree/
│  ├─ layout/
│  ├─ component-resolver/
│  ├─ icon-resolver/
│  ├─ asset-resolver/
│  ├─ design-rules/
│  └─ pipeline/
│
├─ schemas/
│  ├─ prototype-analysis.schema.json
│  ├─ page-tree.schema.json
│  ├─ layout-tree.schema.json
│  ├─ component-mapping.schema.json
│  ├─ ui-ir.schema.json
│  └─ qa-report.schema.json
│
├─ registries/
│  ├─ components/
│  ├─ icons/
│  ├─ assets/
│  └─ tokens/
│
├─ component-builder/
│  ├─ source-reader/
│  ├─ runtime-renderer/
│  ├─ style-extractor/
│  ├─ component-ir/
│  └─ fidelity-gate/
│
├─ icon-manager/
│  ├─ remix-sync/
│  ├─ manifest/
│  └─ semantic-index/
│
├─ adapters/
│  ├─ figma/
│  └─ penpot/
│
├─ validators/
│  ├─ structure/
│  ├─ layout/
│  ├─ component/
│  ├─ completeness/
│  └─ visual/
│
├─ artifacts/
│
├─ examples/
│
└─ tests/
```

---

# 4. Task DAG

```text
TASK-001
   ↓
TASK-002
   ↓
TASK-003
   ↓
TASK-004
   ↓
TASK-005 ─────┐
   ↓          │
TASK-006      │
   ↓          │
TASK-007      │
   ↓          │
TASK-008      │
   ↓          │
TASK-009      │
   ↓          │
TASK-010      │
   ↓          │
TASK-011      │
   ↓          │
TASK-012      │
   ↓          │
TASK-013      │
   ↓          │
TASK-014      │
   ↓          │
TASK-015 ◄────┘
   ↓
TASK-016
   ↓
TASK-017
```

---

# TASK-001 — 初始化项目与架构边界

## 目标

建立项目骨架并锁死 V0.1 架构原则。

## 输出

```text
README.md
ARCHITECTURE.md
CONSTRAINTS.md
VERSION
目录结构
基础测试框架
```

## 必须写入 CONSTRAINTS

```text
1. AI不得直接生成最终UI。
2. Core不得直接依赖Figma/Penpot API。
3. 所有平台输出必须经过UI-IR。
4. 官方组件禁止AI视觉复刻。
5. 未登记组件禁止临时创建。
6. 所有阶段必须保存结构化产物。
7. 当前项目只处理静态页面。
```

## 验收

项目可以启动测试。

目录职责明确。

Core 不存在任何 Figma/Penpot 强依赖。

## Commit

```text
feat: initialize ui design skill architecture
```

---

# TASK-002 — 定义 UI-IR V0.1

## 目标

建立平台无关设计语言。

## 最低支持

```text
Page
Frame
Section
Grid
Row
Column
VerticalStack
HorizontalStack
Text
ComponentInstance
IconInstance
Image
Divider
```

布局属性至少支持：

```text
width
height
fill
hug
padding
gap
alignment
direction
wrap
gridColumns
span
```

视觉基础属性：

```text
fill
stroke
radius
opacity
typographyToken
colorToken
spacingToken
```

## 要求

不得出现：

```text
figmaNodeId
penpotShapeId
```

这种平台字段进入 Core UI-IR。

平台 ID 必须位于 Adapter Metadata。

## 验收

使用纯 JSON 可以完整描述一个：

```text
Header
+
四列查询区
+
Toolbar
+
Table
```

页面。

## Commit

```text
feat: define platform independent ui-ir schema
```

---

# TASK-003 — 建立 Design Tokens

## 目标

禁止 AI 在组件以外区域随意生成视觉参数。

建立：

```text
Color
Typography
Spacing
Radius
Border
Shadow
Page Padding
Section Gap
```

Registry。

UI-IR 优先引用 Token：

```text
spacing.md
color.primary
radius.sm
```

而不是直接写：

```text
17px
#2878ff
```

## 验收

UI-IR Schema 支持 Token Reference。

不存在 Token 时能够明确产生：

```text
missing_token
```

## Commit

```text
feat: add design token registry
```

---

# TASK-004 — Layout Engine V0.1

## 目标

建立确定性布局引擎。

支持：

```text
24 Grid
Vertical Stack
Horizontal Stack
Space Between
Wrap
Fill
Hug
Fixed
```

建立第一批 Layout Pattern：

```text
List Page
Detail Page
Form Page
Dashboard Basic
Sidebar + Content
```

## 核心原则

AI只决定：

```text
页面模式
区块模式
span
方向
优先级
```

Layout Engine 决定实际排列。

## Validator

检查：

```text
span是否超过24
字段是否过窄
是否溢出
padding是否合法
section间距是否统一
不必要嵌套
```

## 验收

给定固定 Layout Tree，多次运行输出必须一致。

## Commit

```text
feat: implement deterministic layout engine
```

---

# TASK-005 — Component Registry V0.1

## 目标

建立跨平台逻辑组件 Registry。

第一阶段只支持：

```text
Button
Input
Select
DatePicker
Table
FormItem
Pagination
Card
Tabs
```

使用逻辑 ID：

```text
form.input.default.medium
form.select.default.medium
action.button.primary.medium
data.table.default
```

Registry 映射：

```text
logical_component_id

→ Figma Component Reference
→ Penpot Component Reference
```

## 要求

AI只能认识逻辑 ID。

Core 不直接认识设计软件 Component ID。

## 验收

同一 Logical Component 可以分别定位 Figma 与 Penpot 实际组件。

## Commit

```text
feat: add cross-platform component registry
```

---

# TASK-006 — 官方组件 Runtime Extractor

## 目标

替代 AI 复刻组件。

输入：

```text
官方源码
官方 CSS
官方组件 Props
```

通过真实运行环境得到：

```text
Computed Style
Bounding Box
DOM Structure
Typography
Padding
Gap
Border
Radius
Color
Icon Metrics
```

生成：

```text
Component IR
```

## 禁止

禁止 Codex：

```text
读取文档后手工写死组件视觉参数
```

## 验收

至少完成：

```text
Button
Input
Select
```

真实运行参数提取。

## Commit

```text
feat: extract component metrics from official runtime
```

---

# TASK-007 — Component Fidelity Gate

## 目标

验证生成的设计组件是否与官方真实组件一致。

检查：

```text
width
height
padding
gap
border
radius
background
text size
line height
alignment
```

并支持视觉截图差异。

## 规则

几何参数要求严格。

允许浏览器与设计软件文字抗锯齿产生轻微 Pixel Diff。

## 输出

```text
component_fidelity_report.json
```

结果：

```text
PASS
FAIL
WARNING
```

只有 PASS 才允许进入正式 Registry。

## Commit

```text
feat: add component fidelity gate
```

---

# TASK-008 — Remix Icon Manager

## 目标

建立可更新的图标组件体系。

实现：

```text
Version Checker
Remix Icon Fetcher
Manifest
SVG Hash
Incremental Diff
Semantic Index
Icon Registry
```

更新规则：

```text
同名未变化 → 不处理
同名有变化 → 原位更新
新增 → 创建
删除 → Deprecated
```

禁止删除仍可能被历史页面引用的组件。

## Semantic Registry

支持：

```text
official tags
+
custom Chinese semantic tags
```

## 验收

可以根据：

```text
搜索
删除
新增
导出
设置
```

找到合理的 Remix Icon。

低置信度允许：

```text
no_icon
```

## Commit

```text
feat: add remix icon synchronization and semantic registry
```

---

# TASK-009 — Figma Adapter V0.1

## 目标

实现：

```text
UI-IR
→
Figma Native Design
```

至少支持：

```text
Page/Frame
Auto Layout
Text
Grid-like layout translation
Component Instance
Icon Instance
Fill/Hug/Fixed
Gap/Padding
```

## 禁止

Adapter 不得进行 AI 设计决策。

例如禁止：

```text
如果看起来不好看就把gap从16改成20
```

Adapter 只负责翻译 UI-IR。

## 验收

固定 UI-IR 可以生成一个真实可编辑 B 端列表页骨架。

组件必须为真实实例。

## Commit

```text
feat: implement figma ui-ir adapter
```

---

# TASK-010 — Penpot Adapter V0.1

## 目标

使用与 TASK-009 完全相同的 UI-IR。

实现：

```text
UI-IR
→
Penpot Native Design
```

## 验收

不得为了 Penpot 修改 Core UI-IR。

同一 UI-IR 可以生成：

```text
Figma页面
Penpot页面
```

结构一致。

## Commit

```text
feat: implement penpot ui-ir adapter
```

---

# TASK-011 — Prototype Semantic Parser

## 目标

AI只理解原型，不开始设计。

输出：

```text
页面是什么
页面主要任务
功能区块
字段
按钮
数据展示区域
静态内容
```

第一版不处理完整交互。

## 明确禁止

本阶段禁止：

```text
选组件
决定颜色
决定间距
决定Grid span
创建最终设计
```

## 输出

```text
prototype_analysis.json
```

## Commit

```text
feat: add prototype semantic parser
```

---

# TASK-012 — Page Tree Builder + Structure QA

## 目标

把 Prototype Analysis 转成 Page Tree。

例如：

```text
CustomerList
├─ Header
├─ SearchSection
├─ Toolbar
├─ TableSection
└─ Pagination
```

Structure QA 检查：

```text
页面是否遗漏
Section是否遗漏
字段是否遗漏
按钮是否遗漏
层级是否异常
```

## 输出

```text
page_tree.json
structure_qa_report.json
```

## 规则

QA 未通过禁止继续 Layout 阶段。

## Commit

```text
feat: build page tree with structure quality gate
```

---

# TASK-013 — Layout Tree Builder

## 目标

根据：

```text
原始原型
+
已冻结Page Tree
+
Layout Pattern
+
Design Rules
```

生成 Layout Tree。

必须优先使用标准 Pattern。

不得直接生成自由坐标。

## 输出示例

```text
SearchSection
└─ Grid 24
   ├─ Col 6
   ├─ Col 6
   ├─ Col 6
   └─ Col 6
```

局部布局：

```text
ButtonGroup
→ HorizontalStack
→ gap token
```

## 输出

```text
layout_tree.json
layout_qa_report.json
```

## Commit

```text
feat: generate validated layout tree
```

---

# TASK-014 — Component Resolver + Annotation View

## 目标

识别每个 Layout Cell 应使用什么组件。

判断依据：

```text
字段语义
+
数据结构
+
原型表现
+
上下文
```

例如：

```text
状态
→ Select

所属部门
→ TreeSelect

省市区
→ Cascader

起止日期
→ DateRangePicker
```

输出：

```text
component_mapping.json
```

同时生成 Component Annotation View：

```text
每个栅格区域
→ 标注 Component Type
→ 使用不同标识色辅助检查
```

颜色只用于人工检查。

系统内部仍使用 Component ID。

## Unknown 策略

```text
高置信度 → 自动匹配

中置信度 → 标准组件fallback

低置信度 → Review / Missing Component
```

禁止 AI 猜造组件。

## Commit

```text
feat: resolve components and generate annotation view
```

---

# TASK-015 — Component Assembly + Content Injection

## 目标

在现有 Layout Skeleton 上进行组件替换。

禁止重新创建整个页面。

流程：

```text
Layout Cell
↓
Logical Component
↓
Registry
↓
Design Component Instance
↓
Slot Filling
```

然后填入：

```text
Label
Placeholder
Button Text
Table Header
Static Content
```

## Slot

至少支持：

```text
leading-icon
trailing-icon
label
control
content
actions
```

## 验收

修改 Component Mapping 后，可以只重新生成相关 Section。

不得要求整个页面重做。

## Commit

```text
feat: assemble components and inject prototype content
```

---

# TASK-016 — Asset Registry + Missing Resource Strategy

## 目标

处理非组件、非图标资源：

```text
Logo
Avatar
Photo
Banner
Illustration
Background
Empty State
```

优先：

```text
原型已有资源
→ Asset Registry
→ Missing Asset
```

禁止 AI 未经明确规则自行生成业务图片替代。

UI-IR 必须支持：

```text
missing_component
missing_icon
missing_asset
unsupported_component
```

## Commit

```text
feat: add asset registry and missing resource handling
```

---

# TASK-017 — End-to-End Pipeline + QA

## 目标

把所有阶段串成完整 Skill。

最终 Pipeline：

```text
Upload Prototype
↓
Prototype Completeness Check
↓
Semantic Parse
↓
Page Tree
↓
Structure QA
↓
Layout Tree
↓
Layout QA
↓
Component Resolve
↓
Component Annotation
↓
Component QA
↓
Component Assembly
↓
Icon / Asset Resolve
↓
Content Injection
↓
Design Rules
↓
UI-IR
↓
Figma / Penpot Adapter
↓
Completeness QA
↓
Visual QA
↓
Final Static Design
```

## Final QA

至少检查：

```text
是否漏字段
是否漏按钮
是否漏Section
组件类型是否正确
Component Variant是否合法
Icon是否来自Registry
布局是否违反Grid
Spacing是否合法
文本是否溢出
组件是否超出容器
同类Section是否保持一致
```

## 输出

```text
qa_report.json
final_ui_ir.json
```

## Commit

```text
feat: complete end-to-end ui design skill pipeline
```

---

# 5. Version Lock

每个设计任务开始时生成：

```text
manifest.json
```

必须记录：

```text
skill_version
ui_ir_version
component_library_version
component_source_version
remix_icon_version
design_token_version
design_rule_version
figma_adapter_version
penpot_adapter_version
```

任务开始后禁止自动切换版本。

新版本只能应用于新任务或明确执行 Migration。

---

# 6. Checkpoint / Resume

每个阶段成功后保存 Checkpoint。

允许：

```text
Page Tree错误
→ 从Page Tree重新执行

Layout错误
→ 从Layout重新执行

组件错误
→ 从Component Mapping重新执行
```

禁止默认：

```text
任何小错误
→ 整个Pipeline从头重新运行
```

---

# 7. Failure Policy

整个系统必须遵守：

```text
确定
→ 执行

可以由标准规则确定
→ 使用标准规则

不确定
→ 标记Review

资源不存在
→ Missing

平台暂不支持
→ Unsupported
```

禁止：

```text
猜一个差不多的
临时创造组件
临时创造图标
偷偷改变页面结构
```

---

# 8. V0.1 不开发内容

以下内容禁止提前开发：

```text
完整Design Brain
长期设计习惯学习
复杂历史页面RAG
自动修改设计规范
交互原型
动画
真实业务逻辑
代码生成
完整响应式系统
所有ViewUI组件
所有Remix Icon人工中文标注
```

这些进入后续版本。

V0.1 的唯一目标：

> 证明架构正确，并跑通静态 UI 自动组装闭环。

---

# 9. V0.1 最小测试原型

准备一个简单 B 端列表页：

```text
页面标题：用户管理

查询区：
姓名
所属部门
状态
创建日期
查询
重置

操作区：
新增用户
导出

数据区：
用户Table

底部：
Pagination
```

覆盖：

```text
Input
Select
DatePicker
Button
Icon
Table
Pagination
FormItem
Card
```

同一原型必须分别生成：

```text
Figma Version
Penpot Version
```

---

# 10. V0.1 Release Gate

只有以下全部通过才能标记 V0.1 Ready：

```text
[ ] Page Tree 无遗漏

[ ] Layout Tree 可重复生成

[ ] Layout 不依赖自由坐标

[ ] UI-IR 与平台无关

[ ] Figma Adapter 可消费 UI-IR

[ ] Penpot Adapter 可消费同一 UI-IR

[ ] 基础UI组件为真实Component Instance

[ ] Icon为真实Icon Component Instance

[ ] AI不会自行创建未登记组件

[ ] 官方组件经过Runtime Extraction

[ ] 官方组件经过Fidelity Gate

[ ] Remix Icon支持Registry和版本Manifest

[ ] 中间JSON均可保存

[ ] Pipeline可从Checkpoint恢复

[ ] Missing Resource不会被AI偷偷替换

[ ] QA可以发现原型内容遗漏

[ ] 最终页面保持原生可编辑
```

---

# 11. Codex 工作纪律

Codex 每执行一个 Task 必须：

```text
读取：
ARCHITECTURE.md
CONSTRAINTS.md
当前Development State

↓

确认依赖Task已完成

↓

仅完成当前Task范围

↓

运行测试

↓

执行Task验收

↓

记录结果

↓

更新Development State

↓

Commit
```

不得跨 Task 大规模提前开发。

不得因为“实现更方便”绕过 UI-IR。

不得把平台 API 泄漏进 Core。

不得把临时 Demo 当正式实现。

不得跳过 Validator。

---

# 12. 开发状态文件

建立：

```text
.dev/DEVELOPMENT_STATE.md
```

记录：

```text
Current Version
Current Task
Completed Tasks
Blocked Tasks
Known Issues
Architecture Decisions
Validation Result
Last Commit
Next Task
```

这样 Codex / Trae / 其他 Agent 中断以后可以继续。

---

# 13. 最终架构原则

整个项目最后必须始终满足：

```text
AI负责理解与选择
程序负责布局与执行

官方组件负责视觉真值
Registry负责资源定位
UI-IR负责平台解耦
Adapter负责设计软件落地
QA负责阻止错误继续传播
```

一句话定义：

> UI Design Skill 不是“AI画UI”，而是“AI读取静态原型后，通过标准布局、真实组件、真实图标和确定性规则，在Figma或Penpot中自动组装原生可编辑设计稿”。

---

# 14. Codex 首轮执行指令

开始开发时不要尝试一次完成整个 BUILD PLAN。

从：

```text
TASK-001
```

开始。

完成当前 Task 后：

```text
1. 执行测试
2. 按验收标准逐项自检
3. 更新 .dev/DEVELOPMENT_STATE.md
4. Commit
5. 再进入下一个 Task
```

如果实现过程中发现架构问题：

不得自行修改 V0.1 Architecture Baseline。

必须先记录：

```text
ARCHITECTURE_CONFLICT
```

并说明：

```text
当前设计
冲突原因
影响范围
建议方案
```

在架构决策明确前不得私自重构主链路。