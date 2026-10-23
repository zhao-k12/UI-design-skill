# 原型 → iView HTML 页面

原型提供页面内容、层级、顺序、业务关系及组件变体所需的可见特征，不提供可直接采用的像素或视觉样式值。按 [原型观察与验收](PROTOTYPE_OBSERVATION_QA.md) 初读和独立复扫，建立 Tree；AI 提出布局，再核对 [View UI Plus 官方依据与整页组合参考](IVIEW_OFFICIAL_EVIDENCE.md)，形成彩色骨架。内部一次生成骨架、默认组件和填充内容三个审核状态；最终只交付一个可离线打开、保留真实文字节点的静态 `page.html`。

## 一次综合审查的四类结论

1. 内容 Tree：先比较两次原图扫描的逐项结果，再把来源观察清单与原型逐项比对，确认文案、字段、操作、表格列、可见记录、每项菜单箭头、状态填充与圆点、头像、徽标、下拉关系和图文顺序正确完整；纳入项须绑定 Tree，排除项须有证据，未知项保留 Review。影响主要内容的 Review 未解决前不能进入相关骨架。
2. 彩色骨架：标明组件角色及 Tree 来源，包含图标、头像、徽标、下拉等附属结构；核对区域顺序、官方 Layout/Grid、相邻区域边界和表格占宽。装饰强调线不能仅因外形相似就映射为 Divider。审核对象是可见骨架，不以文字方案代替。
3. 默认组件：实例化官方组件并保持默认文案；核对角色、变体、DOM、官方 CSS 和非文字结构。检查图标／头像—文字、树符—名称、控件—容器分隔线等相邻关系；重复结构按共同规则批量查实例，例外单列。本地 CSS 或行内样式改写 `.ivu-*` 组件外观均为失败。
4. 交付内容：只填来源绑定的原型内容，从原图逐区校对最终静态截图的文字、数据、非文字特征和溢出。页面可渲染或文字齐全不能替代原图校对。

四项是**一次综合审查的四类结论**，不是四轮浏览器运行或四次模型审核。仅关键来源歧义和组件缺口提前阻断；同一 UI-IR 在一次浏览器会话中生成三个状态并截图，集中审查。只重建失败处及受影响的下游；官方来源按锁定版本复用，新组件或组合才补查。重复实例逐个保持来源编号，但共同关系只审核一次并列出例外。

官方无定义的页面级几何要记录为规范缺口，优先使用官方组件的自然或自适应布局。需要补充规范时，应找到锁定版本的官方文档、源码或运行 CSS 并记录具体路径；不得把旧项目 Token、原型测量或主观视觉判断写成“官方值”。骨架和流程切换控件可使用必要的演示样式，但不得进入交付组件外观。页面排布需要的样式只表达布局关系，不改写官方组件内部视觉。

## 执行

### 树形列表 HTML v1 Profile

当原型包含整页侧栏分组、通知 Badge、头像及树形表格时，旧 `v0.2.9` Profile 缺少这些角色。使用独立 `html-v1.0` 目录：`registries/components/html-v1/catalog.json`、`core/pipeline/html_page_v1.py`、`adapters/html/page-v1.mjs`。先从本次原图独立准备带同一 SHA-256 的 `content-tree.json`、`source-observations.json`、`independent-scan.json`，再运行：

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 core/pipeline/html_page_v1.py --source artifacts/<任务>/prototype.png --content artifacts/<任务>/content-tree.json --observation artifacts/<任务>/source-observations.json --independent-scan artifacts/<任务>/independent-scan.json --output-dir artifacts/<任务>/core-v1-r1
```

该命令将每条纳入观察绑定到 Page Tree 和组件角色，产出布局 Tree、UI-IR、官方源码哈希和 Core QA。HTML Adapter 只从 UI-IR 取组件变体与页面内容。TASK-140 的构建、三状态浏览器截图、菜单/状态/树表检查及原图复核见 `artifacts/task-140/product-types`；此构建脚本是当前树形列表示例，其他页面模式仍需新来源和相应验收契约，不能把旧 Profile 的 PASS 借给新页面。

### 既有列表 Profile

阅读本次原型并独立编写带原型哈希的来源观察清单，再从原图复扫、解决差异，记录纳入／排除／Review、内容映射及初步布局。核查适用的官方整页组合与组件依据，运行 HTML Core，保留来源映射、布局和 UI-IR。内部审核三态一次生成；关键输入或官方资源缺失时提前阻断，其他问题在综合审查中归类并局部修复。

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_html_pipeline.py artifacts/<任务>/input --output-dir artifacts/<任务>/core
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/prepare_html_workflow.py --run-dir artifacts/<任务>/core --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/staged
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_html_checks.py --staged-dir artifacts/<任务>/staged --review artifacts/<任务>/tree-review.json --intent artifacts/<任务>/layout-intent.json --plan artifacts/<任务>/input/layout-plan.json --layout-tree artifacts/<任务>/core/layout_tree.json --layout-report artifacts/<任务>/core/layout_qa_report.json
```

`run_html_checks.py` 依次执行 Tree、布局、iView 检查；`page_content_tree_review.json` 须有与当前 Tree 指纹匹配的 PASS，后两项也须 PASS。审核材料必须针对本次原型独立编写，不直接复用旧页面的内容或决策说明。

```powershell
rtk proxy node scripts/export_html_page.mjs --core-dir artifacts/<任务>/core --staged-dir artifacts/<任务>/staged --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/html-r1
```

输出目录必须为空。导出器在同一 Chromium 会话中渲染三个内部状态，保存 `skeleton.png`、`component.png` 和最终静态 `delivery.png`，集中生成 `html_workflow_qa.json`。只有综合检查 PASS 才写最终 `page.html`；其中保留官方渲染后的 DOM、真实文字与原型指定的固定选中外观，移除运行脚本和审核切换控件，禁止鼠标触发 hover／点击效果。交付页不提供业务交互。QA 记录来源、版本、UI-IR、组件、截图和静态页面哈希，以及批量 DOM/几何/内容结果。目视校对仍须从原图到最终静态截图，自动检查不能发现两次观察共同遗漏的内容。

最后按[原型观察与内容验收](PROTOTYPE_OBSERVATION_QA.md#新任务的结构化复核门)运行 `scripts/audit_prototype_observations.py`，将原图、两次观察、逐项变体复核和三张阶段截图绑定。该门 PASS 且原图到最终截图的目视校对完成后才报告交付；旧任务的浏览器 PASS 不自动升级。

当前已在用户管理列表页实测 Input、Select、Button、带表头 Table、Remix 设置图标和静态 Text；这些控件由官方组件运行包渲染。其他现有组件虽已接入渲染映射，尚未逐类完成页面实测。原有浏览器 PASS 仅覆盖当时检查项，不自动证明新定义的官方依据与骨架视觉审核已完成。

来源支持的组件文字与 Table 行内容可随新原型变化。组件类型、Table 列结构、可用属性、设计 Token 和已定义的布局模式仍由当前正式目录与 Core 规则决定。超出这些范围的新页面需要补充相应的组件或布局契约，不能仅凭浏览器能显示就宣称已验收。当前实测了 1660px 用户管理页和同一来源内的表格行内容变体；后者是开发验证，不是新的用户审核原型。

当前 Core 的部分页面间距、文字排版和固定几何仍来自历史项目 Token 或列表页规则，不能仅因其数值与官方变量相同就称为官方规定。迁移前须逐项核对来源；无法找到官方依据的视觉决定不进入新的合规交付。样式选择器阻断只覆盖直接 `.ivu-*` 改写，不代替页面规则的来源审核。

## 复杂客户列表截图模式

历史客户管理示例使用 `source-tree.json` 记录内容，使用 `layout-intent.json` 记录布局决策。其内容抽取仍可作参考，视觉模板不再使用：`prototype-layout.css` 覆盖了官方组件样式，并写入若干没有官方依据的视觉值。导出器现在会在加载这份 CSS 时阻断输出；须先按新流程重建骨架、补齐官方依据和默认组件样式，不能拿历史截图的三状态 PASS 直接交付。缺少的业务数据或筛选选项仍不能猜填。

```powershell
rtk proxy node scripts/export_prototype_html.mjs --input-dir artifacts/<任务>/input --output-dir artifacts/<任务>/html-r1
```

旧模式的本地验收记录位于 `artifacts/task-132/customer-management/html-final-r2/qa.json`。其中三状态 PASS 只代表内容、DOM 与几何等旧检查项通过；官方组件外观未通过新规则，不能算 iView 规范交付。上述命令仅供定位旧实现，不作为当前主流程的可用交付入口。
