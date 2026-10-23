# 原型 → iView HTML 页面

原型提供页面内容、层级、顺序、业务关系和选组件变体所需的可见呈现类别，不提供可直接采用的像素、精确色值、间距或字体。先按 [原型观察与验收](PROTOTYPE_OBSERVATION_QA.md) 逐项记录文字、图标、菜单箭头、状态标签的填充／描边等特征，独立从原图复扫一次，解决差异后判定纳入、排除或 Review，再建立 Tree。AI 据此提出初步布局；先查证本页所需的 [View UI Plus 官方依据与整页组合参考](IVIEW_OFFICIAL_EVIDENCE.md)，再把修订后的设计判断直接做成可审核的彩色组件骨架。页面只输出一个可离线打开的 `page.html`：同一页面依次进入彩色骨架、默认文案组件和原型内容交付三个状态，页面顶部可切换查看。每个状态单独保存截图与 QA。

## 四个独立验收点

1. 内容 Tree：先比较两次原图扫描的逐项结果，再把来源观察清单与原型逐项比对，确认文案、字段、操作、表格列、可见记录、每项菜单箭头、状态填充与圆点、头像、徽标、下拉关系和图文顺序正确完整；纳入项须绑定 Tree，排除项须有证据，未知项保留 Review。影响主要内容的 Review 未解决前不能进入相关骨架。
2. 彩色骨架：在骨架上标明每块使用的官方组件及 Tree 来源，包含图标槽位、头像、徽标、下拉等附属结构；检查组件选型、区域顺序、官方 Layout/Grid、对齐、内边距、间距和表格填满可用容器。必须看整页截图：核对侧栏品牌区与顶栏等相邻区域的边界和高度是否协调，背景是否按选定的官方组合形成清楚的层级；不能只数彩色块或查 DOM。记录参考示例及其适用性、发现的问题和修订结果。审核对象是可见骨架，不以一段设计方案文字代替。失败则修改骨架并重验。
3. 默认组件：按通过的骨架实例化官方组件，保持默认文案；检查组件 DOM、官方 API 配置、官方 CSS 运行效果、骨架位置及非文字结构。将原型的角色、填充／描边、形状、圆点和图标与实际官方变体逐项对照；不能把带箭头的菜单变成普通项，或只因 `.ivu-tag` 存在就放过错误的 Tag 变体。任何本地 CSS 或行内样式改写 `.ivu-*` 组件外观均为失败。独立 QA 通过后才能填原型内容。
4. 交付内容：只填入来源绑定的原型内容，从原图重新逐区检查最终截图，逐项校对文字、数据、所有重复项的非文字特征与控件关系，再检查遗漏、溢出与整体呈现。不能以页面可渲染、文字齐全或旧的三状态浏览器 PASS 代替上述验收。

官方无定义的页面级几何要记录为规范缺口，优先使用官方组件的自然或自适应布局。需要补充规范时，应找到锁定版本的官方文档、源码或运行 CSS 并记录具体路径；不得把旧项目 Token、原型测量或主观视觉判断写成“官方值”。骨架和流程切换控件可使用必要的演示样式，但不得进入交付组件外观。页面排布需要的样式只表达布局关系，不改写官方组件内部视觉。

## 执行

### 树形列表 HTML v1 Profile

当原型包含整页侧栏分组、通知 Badge、头像及树形表格时，旧 `v0.2.9` Profile 缺少这些角色。使用独立 `html-v1.0` 目录：`registries/components/html-v1/catalog.json`、`core/pipeline/html_page_v1.py`、`adapters/html/page-v1.mjs`。先从本次原图独立准备带同一 SHA-256 的 `content-tree.json`、`source-observations.json`、`independent-scan.json`，再运行：

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 core/pipeline/html_page_v1.py --source artifacts/<任务>/prototype.png --content artifacts/<任务>/content-tree.json --observation artifacts/<任务>/source-observations.json --independent-scan artifacts/<任务>/independent-scan.json --output-dir artifacts/<任务>/core-v1-r1
```

该命令将每条纳入观察绑定到 Page Tree 和组件角色，产出布局 Tree、UI-IR、官方源码哈希和 Core QA。HTML Adapter 只从 UI-IR 取组件变体与页面内容。TASK-140 的构建、三状态浏览器截图、菜单/状态/树表检查及原图复核见 `artifacts/task-140/product-types`；此构建脚本是当前树形列表示例，其他页面模式仍需新来源和相应验收契约，不能把旧 Profile 的 PASS 借给新页面。

### 既有列表 Profile

阅读本次原型并独立编写带原型哈希的来源观察清单，再不看初稿从原图重新扫描各区域和重复实例，解决两份观察的数量与特征差异。之后写纳入／排除／Review 决定、内容映射和 AI 初步布局意图。排除理由与待确认问题须保留在审核材料中，不能通过删掉观察项制造完整性 PASS。核查官方整页组合参考，记录“采用／不适用／未找到”及原因，再为实际组件和布局判断补齐官方依据。运行 HTML Core，逐条核对来源证据、组件映射、布局和 UI-IR。准备分阶段数据，保存骨架整页截图并完成 Tree 与骨架的独立审核；布局质量、iView 来源、整页组合审查和样式覆盖检查未 PASS 时不得进入默认组件状态，也不能沿用旧原型的审核指纹。

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_html_pipeline.py artifacts/<任务>/input --output-dir artifacts/<任务>/core
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/prepare_html_workflow.py --run-dir artifacts/<任务>/core --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/staged
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_html_checks.py --staged-dir artifacts/<任务>/staged --review artifacts/<任务>/tree-review.json --intent artifacts/<任务>/layout-intent.json --plan artifacts/<任务>/input/layout-plan.json --layout-tree artifacts/<任务>/core/layout_tree.json --layout-report artifacts/<任务>/core/layout_qa_report.json
```

`run_html_checks.py` 依次执行 Tree、布局、iView 检查；`page_content_tree_review.json` 须有与当前 Tree 指纹匹配的 PASS，后两项也须 PASS。审核材料必须针对本次原型独立编写，不直接复用旧页面的内容或决策说明。

```powershell
rtk proxy node scripts/export_html_page.mjs --core-dir artifacts/<任务>/core --staged-dir artifacts/<任务>/staged --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/html-r1
```

输出目录必须为空。程序只写入一次 `page.html`，在同一个 Chromium 标签页中按骨架 → 默认组件 → 交付内容的顺序切换并验收；每一步 PASS 后才进入下一步。直接打开文件默认显示交付内容，顶部按钮可查看之前两个状态。`skeleton.png`、`component.png`、`delivery.png` 与 `html_workflow_qa.json` 保存逐阶段证据，出现问题可从对应状态重新生成。QA 记录官方源码版本和 CSS 哈希、Tree/UI-IR/组件目录哈希、单页文件与截图哈希、实际组件 DOM、来源项覆盖、逐 Cell 几何、表格占宽、最终文案与溢出检查。另存与原型哈希绑定的两次来源观察、逐项变体依据和原图到交付截图的视觉复核；菜单、状态、表格等重复项须逐项点数，不能以一条汇总替代。自动检查只能证明其明确检查过的性质；尤其当前自动 Tree 检查只核对已进入 Tree 的内容，不能发现最初漏观察的箭头或错误变体。须另存骨架官方依据审核和最终原型校对结论，才能宣称规范交付。

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
