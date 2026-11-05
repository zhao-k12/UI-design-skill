# 常见页面的5分钟目标

新任务先读SKILL入口，本说明按需定位命令和契约，不必全文重读。节点与Table槽位有疑问时再读[组合契约](HTML_COMPOSITION.md)，首次官方能力再查其源码；不要每页重读历史开发记录。5分钟包含理解、工具等待、视觉校对及修正，不是硬超时或已达成的性能保证。

新原型直接从当前输入编写完整Tree；不以历史页面或旧任务的Tree、配置、截图和复核作为内容来源，也不因相似而先查旧页面。复用通用规则、官方组件用法及通用执行器。用户明确要求继续、修改、对比或复用某个旧页面时，按请求读取该页面并保留来源区别。

## 一个入口，两份短输入

尽早记录任务起点（使用新的任务目录）。随后独立读原型，写`job.json`，不写本页prepare/scan程序：

可并行启动计时、读取必要说明与核验当前原图等彼此独立的准备工作；依赖准备结果的Tree编写、渲染、视觉复核和发布仍依次进行。将原型识别直接记入本次Tree和来源材料，独立复扫仍需再次对照原图，不从Tree或初读生成复扫结论。

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py start --task-dir artifacts/<任务>
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py render --task-dir artifacts/<任务> --input artifacts/<任务>/job.json
```

`job.json`含`source`（相对job文件的原图路径）、`viewport`（可选宽高）、`content`（现有内容Tree）、`observation`、`scan`。后三者均显式绑定原图`sourceSha256`。内容Tree描述共同组件与实际行数据；两份观察分别来自初读与独立复扫，共同特征按组记，例外单列。

观察仍支持既有`items`，重复区域可用`groups`：

```json
{
  "id": "records", "prefix": "record-", "count": 13,
  "region": "table", "decision": "include", "treeRef": "records",
  "sourceEvidence": "13条记录，头像/在线圆点/四个行操作；行文字见来源绑定的Table数据",
  "traits": {"leading":"avatar", "trailing":"four-icon-actions", "surface":"plain", "shape":"rect", "role":"employee-record"},
  "exceptions": {}
}
```

也可用`ids`显式列编号代替prefix/count。`exceptions`按实例id改写该实例的观察；不同状态、图标或操作数量必须作为例外，不能平均化。行文字仍逐条保存在Tree数据中，不因分组丢失。

`props.data`逐行显式列出，即使各行相同也不使用`$repeat`。来源行的文字、编号、空值和状态原样保留；按[10条展示政策](PROTOTYPE_OBSERVATION_QA.md#列表条数空值与裁切)补充的演示行内部注明行号及依据，不能冒充来源记录。超过10条只保留前10条，裁切片段不直接制作残缺行。初读/scan仍记录原图真实条数，不从输出10条反向改写观察；不另建补充报告或审核阶段。

`scan.groups`单独填写独立看见的`id/prefix/count/region/traits/visual`及例外，不复制完整初读文字，也不能让程序代替原图复扫。两份数量/特征不同会在Core被拒绝。Tree节点用`sourceGroups:["records"]`绑定整组；关系也可用sourceGroups。执行器展开真实逐项证据，旧完整性门继续核对，不让模型重复书写上百份记录。

## 完整 Tree

### 新任务的程序预检与布局检测

`start` 为新任务记录 `sourceEvidencePolicy: complete-traits-v1` 和 `layoutQualityPolicy: form-and-modules-v1`。渲染前检查初读与复扫的五项非空 traits、来源节点绑定以及每个 MenuItem/Submenu 的实例来源；明确图标特征缺少对应图标时拒绝编译。旧计时文件未声明策略时保留兼容。这只能证明提交材料完整，不能证明模型独立看过原图。

新策略还会测量输入值/占位提示可用宽度、横向标签换行及显式通用模块的边距、间距和关闭图标几何；冻结静态页后复查，并在不大于 1100×700 的较小视口滚动到底，检查截断与底栏遮挡。结果在 `qa.json` 的 `layoutQuality`、`responsiveQuality`，截图为 `small-viewport.png`；发布和文件核验同时核对这张截图的哈希。检测失败不会发布为任务根目录成品。

横向 FormItem 确有来源或明确要求允许换行时，可在该节点填写 `allowLabelWrap: true`，并在来源记录解释依据；顶部标签布局自动排除单行检查。不得仅为消除报警启用例外。字段空间不足时优先用已支持官方布局或已确认的 `form_section(columns='auto')`；官方四列默认保持不变。机器检测仍不覆盖所有间距关系、业务语义或美学判断。

布局前先选[已核实的官方区域组合](IVIEW_COMPOSITION_PATTERNS.md)，在编写Tree的同一批次确定页面壳/官方主题、主次层级、分区、字段宽度、表格列策略和整体密度，适用理由简记在现有证据中，不另写方案。宽度按内容与任务分配，不机械等分字段；官方内容宽度预检只是下限保护。骨架直接显示这些设计选择，不照搬偶然空白或截图裁切。组合可混用，不从例页复制业务内容；10条及默认分页按用户展示政策执行。新用法才补查，后续两态沿用同一结构。

同一批次按[项目设计共同经验](LEARNED_PAGE_COMPOSITION.md)识别所属模块、控件作用对象、静态状态和数据语义；普通列表、分类矩阵、时序数据和汇总行分别判断，图表保留系列及坐标关系。仅在实际任务涉及图表、抽屉或特殊表格时读取对应段落；采用本地未实现的能力前先查官方与Adapter，缺口如实记录。既有综合审查覆盖这些关系，不新增审核阶段。

主题先按[项目默认组合](IVIEW_COMPOSITION_PATTERNS.md#项目默认主题与表单)选择：有侧栏通常浅色顶栏配深/浅侧栏，不默认双深；无侧栏顶栏深浅均可。不能逐组件照用默认背景或复制上页主题。桌面筛选/表单默认标签左、控件右，通过官方Form标签属性及栅格配置；空间不足优先整项换行，top只用于有理由的特殊情况。整列背景、标签方向及对比度在原来一次综合审查内核对，不加阶段。

查询动作默认“查询 → 重置 → 收起/展开”，仅在筛选确有折叠时展示相应状态；页面主动配置的图标使用Remix Icon，具体Tree写法和官方组件内部指示图形的边界见[图标与查询操作](HTML_COMPOSITION.md#图标与查询操作)。本次用户明确要求优先，静态页只保留固定状态。

所有节点显式填写完整字段与稳定编号，直接表达父子归属，不再使用作者层简写：

```json
{"root":{"id":"toolbar","kind":"container","layout":{"direction":"horizontal","gap":"xs"},"children":[
  {"id":"name-input","kind":"component","component":"Input","props":{"placeholder":"请输入姓名"},"sourceIds":["name-filter"]},
  {"id":"query-button","kind":"component","component":"Button","props":{"type":"primary","disabled":false},"sourceIds":["query-action"],"children":[{"id":"query-label","kind":"text","value":"查询"}]}
]}}
```

节点必须有`id`与`kind`，组件、属性、布局、文字分别使用`component/props/layout/value`等完整字段。`use/p/text/from/stack/default`简写、`definitions/ref`片段引用、隐式文字节点和缺省编号均拒绝输入。数据仍可用明确的`{"bind":"row.xxx"}`绑定标准组件重复模板，实际行集合必须完整列出。

## 完整 Tree 辅助编写

优先用共用的`scripts/html_tree_editor.py`，在一个Python执行批次中直接操作完整Tree，代替逐字书写重复JSON。Windows调用Python使用`-X utf8`，避免中文标准输入被系统编码误读。只调用工具，不为每张页面保存一份prepare/生成器程序。没有新的输入语言或简写转换：编辑器内部持有的就是标准Tree，`write_job`直接写现有job格式。

```python
from html_tree_editor import FullTreeEditor

editor = FullTreeEditor(source_sha256, title, {
    "id": "page", "kind": "container", "layout": {"direction": "horizontal"}
})
sidebar = editor.add("page", "container", id="sidebar", layout={"direction": "vertical"})
main = editor.add("page", "container", id="main", layout={"direction": "vertical"})
# 区域归属来自模型对本次原型的判断，工具不做决定。
brand = editor.add(sidebar, "component", component="Avatar",
                   props={"shape": "square"}, sourceIds=["brand"])
header = editor.add(main, "component", component="Card", props={"padding": 16})
editor.add(header, "text", value="本次原型标题", sourceIds=["page-title"])
editor.write_job(job_path, source=prototype_path, observation=observation, scan=scan)
```

以上是工具API用法，不是固定页面模板；本次区域由原型决定。`add`需要明确父节点、kind及适用的完整字段，支持一次附带完整children、slots和Table列cell。可传`slot`或`index`明确位置；模型不必手写机械编号，工具在内存中生成唯一编号后作为真实`id`保存，手工输入的完整Tree仍不得缺id。动态图标允许在构造时传明确的`icons`名单，不自动选择图标。

`set_properties(node_id, {...})`只填写指定组件属性；`set_rows(table_id, [逐条完整数据])`保留原文、相同业务编号、false/null和所有状态，不根据数量扩写记录；`move(node_id, parent_id, index=...)`只执行模型明确指定的移动，保留节点内容和来源，不自行合并区域。`content()`可直接取得完整结果用于检查。编号、括号、连接和格式交给工具；布局含义与内容准确性仍由模型负责。

写入后按原有一次集中复核检查完整树及页面；不另加一轮人工确认或串行QA。编辑工具不生成独立复扫材料或视觉PASS，不代替Core结构、官方属性及来源完整性检查。

同批次检查节点编号、来源绑定、表头顺序和图标名称；逐行状态与例外保留。写入前将本次输入保存在当前运行会话内存或任务文件；若写入工具失败，优先从仍可用的本次输入重试，不重复识图或重写已确认内容。若内存不可用则从已保存的本次文件恢复，无法恢复时如实重建；不读取历史页面配置替代。

`content-tree.json`保存完整树。检查不仅包含每条文案、编号、true/false状态和变体，还包含品牌、侧栏、顶栏、主内容的父子归属；不能因为文字齐全而随意移动区域。初读、独立复扫与一次综合复核保持原职责，不增加额外审核阶段。历史简写job须人工按来源核对后改为完整树才能重跑，既有HTML不改写。

## 布局关系检查

完整Tree顶层`layoutRelations`描述实际节点关系，随Core保存到UI-IR，由同一浏览器三态导出时测量。可用编辑工具`set_layout_relations([...])`记录，模型明确关系，工具不选择布局：

```json
[
  {"id":"sidebar-fill","kind":"surface-cover","surface":"sidebar-surface","extent":"main-region","axis":"vertical","sourceEvidence":"侧栏背景应延伸至主内容区底部"},
  {"id":"nav-start","kind":"edge-align","first":"top-navigation-region","second":"sidebar-region","firstEdge":"left","secondEdge":"right","sourceEvidence":"顶部导航从侧栏右边界开始"},
  {"id":"brand-boundary","kind":"edge-align","first":"brand-region","second":"sidebar-region","firstEdge":"right","secondEdge":"right","sourceEvidence":"品牌区和侧栏共享列边界"},
  {"id":"header-center","kind":"vertical-center","first":"top-navigation-region","second":"header-region","sourceEvidence":"顶部导航在顶栏中垂直居中"}
]
```

`surface`是实际拥有不透明背景的区域节点；透明占位容器不算背景证据。`extent`指应延续到的布局区域，不能为通过检查改成菜单自身；`axis:vertical`只比较上下覆盖，可引用相邻主区；省略axis时比较完整矩形覆盖。`edge-align`比较指定左右边界，`vertical-center`可指定first/second检查其它图文组合。引用完整区域框，不用品牌文字的自然宽度代替品牌列。原型决定关系，官方规则决定布局实现；不读取原型像素或重新限制页面尺寸。

相邻区域有明确最小间距时，可声明 `{"id":"toolbar-gap","kind":"minimum-gap","first":"toolbar","second":"table","axis":"vertical","minimum":"xs","sourceEvidence":"操作区和表头应有间距"}`；按实际顺序测量，`horizontal` 测右边到左边，`vertical` 测下边到上边；`minimum` 使用现有 `none/xs/sm/md/lg` token，不自动改变布局。它只验证声明的最小距离，不验证语义、居中、头像组内距离是否过大或边距是否合理；这些仍需视觉复核。只在页面确有相应区域且token适用时声明。

Header加横向Menu和纵向Menu的组合缺少背景或边界契约会在Core拒绝；不再根据组件名强制要求居中契约。其它组合按实际关系声明，不要求侧栏或统一壳模板。浏览器自动检查每个实际Card的extra按钮/选择器是否跨越头部/底部分隔线或超出宽度；不再把所有extra强制居中。确有官方组合依据才显式声明`vertical-center`；顶对齐或基线关系在现有关系复核中核对，不假称机器已测。1 CSS px只容纳已声明几何关系的舍入，不是设计间距来源。

结果在三态`qa.json.stages.<stage>.layoutRelations`，保留具体矩形、偏差和问题编号；静态快照后再确认最终交付结果。失败不能靠手填PASS绕过。复核原图与截图后，在同一review中填写`checkedLayoutRelations`，覆盖`review-plan.json.layoutRelationIds`列出的全部编号，卡片编号自动生成，不必逐项重复写PASS说明。数量/文字正确不代表这些关系通过。现有综合验收负责这一并确认，不增加关卡；机器只验证已声明的几何/背景及原生Card工具栏，不能自动发现所有错误的语义归属、遮挡或光学问题。

## 一次看三态，简记结论

render返回`runId`、原图哈希、`reviewSheet`及三张原始截图路径，状态为`REVIEW_REQUIRED`。先取回`review-sheet.png`，对照原图做同一次综合校对；文字、间距或小图标看不清时放大原始截图，不能因缩略图不清而确认。运行PASS不代表已目视通过。

预览仅用于内部复核，不是结束节点。发现任何尚未解决的内容或视觉问题时，记录差异，修正受影响配置及依赖，重新渲染并查看新截图，复核受影响项和全局关系；重复此过程，直到综合验收实际通过并执行 finalize。审核发现的问题清单即是下一轮工作：先处理仍可自行修复和核实的内容；组件属性不生效时检查锁定版官方实现及适配能力，再选择可用的官方组合或按真实能力缺口处理。生成失败先读取错误并修复可解决的问题后重试。不要把预览链接或“尚未通过验收”作为结束，也不因超时、发现问题或等待用户点评而停止。用户明确要求过程稿可展示并标注未验收，随后继续工作。遇到确实无法自行解决的必要输入或能力缺口，说明具体阻碍、已尝试的修复及未完成项，保留未完成状态；不可用主观猜测或手填 PASS 绕过。

每轮先完成整页检查：对照原图及已有设计规则，检查内容和状态、导航归属、区域布局、控件及间距，将发现的所有差异简记在现有复核材料中；不要发现一个问题就立即改动并重渲染。检查相关依赖后，一次修正所有已明确且可同时解决的差异，再重新渲染。复看全部修改项、受影响区域和全局关系；如果发现新问题或连带影响，再汇总并进行下一轮。若技术故障使其余区域无法检查，可先修复阻碍后继续整页检查；不得为了减少轮次而把未确认项记为通过，也不新增报告或人工确认步骤。

默认使用差异式输入，不再重复抄写已经记录的共同特征。`review-plan.json`是程序生成的预期清单，**不是已审核证据**。实际核对当前原图与截图，包括组内每个实例和例外后，写：

```json
{
  "reviewMode":"delta-v1", "runId":"当前runId", "sourceSha256":"当前原图哈希",
  "checkedStages":["tree","skeleton","component","delivery"],
  "confirmedGroups":["records"], "issues":[], "relationChecks":[]
}
```

`confirmedGroups`表示实际匹配预期的组，未检查不能填写；非分组items用`item:<来源id>`。`issues`记实际差异，有未解决问题不能finalize。程序按明确确认展开原有审核材料，不自动把生成预期改成PASS。无变化的细节无需重新描述；有关系记录时`relationChecks`仍填写对应id、status、officialEvidence、renderedEvidence，随四类结论一次确认，不增加新验收阶段。旧版格式继续兼容：

复核后写`review.json`：`runId`、`sourceSha256`、`reviewMode:"batched-v2"`、四项`stageChecks`、官方`variantRules`、`relationChecks`，以及单项`items`或共同复核`groups`。共同复核格式：

```json
{
  "sourceGroups": ["records"], "status": "PASS", "variantRef": "record-components",
  "renderedTraits": {"leading":"avatar", "trailing":"four-icon-actions", "surface":"plain", "shape":"rect", "role":"employee-record"},
  "renderedEvidence": "已对照原图和当前三态截图检查全部13行、实际文字及共同图形；例外另列"
}
```

只有实际核对后才写PASS。排除项也须显式复核，可分组填写`exclusionStatus:"PASS"`。工具自动补截图哈希和逐项材料，但不会推断视觉PASS；遗漏复核、重复编号、特征不符、旧runId、截图或页面变动均拒绝。

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py finalize --task-dir artifacts/<任务> --input artifacts/<任务>/review.json
```

finalize运行原有综合来源/视觉门；通过后才把`page.html`与`delivery.png`发布到任务根目录，写交付回执。只有真实复核通过且 finalize 成功，才能将该页面作为正式结果交付。finalize失败须根据具体问题修正并重新渲染、复核、再次 finalize；计划、三态原图、合并图或页面被修改均使当前复核失效。

交付前运行 `rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py verify --task-dir artifacts/<任务>`。该命令检查当前回执、原型副本、完整 Tree、审阅与截图证据及发布页的哈希；直接写入的页面、缺少回执或发布后被修改的页面不能通过。它不替代实际视觉复核，也不能防止其他程序直接写文件。核验失败时先恢复到正确的 `render` → 复核 → `finalize` 路径；禁止将手写页面或中间结果冒充 Skill 正式交付。

实际视觉复核完成后，可将写入真实`review.json`与顺序执行`finalize`安排在一次工具调用中，减少额外启动等待；不要在复核前生成PASS，也不要让写入和发布并行。现有`render`已在一次调用中完成准备、编译和三态导出；不要声称它已跨调用复用进程或浏览器。仅在当前运行环境明确支持并实测有效时复用会话；否则维持现有流程并如实记录等待。

## 局部修正与失效

每次 `render`/`revise` 在 `latest-attempt.json` 记录本次尝试。成功渲染后的 `ready` 仅表示等待真实审核，不表示交付通过；失败时记录 `failed`、错误类型与原因，并保留运行目录中的 `failure.json`、可读取的原始输入 `submitted-job.json` 和已产生的中间文件。输入快照无法保存时，记录 `inputSnapshotError`，不掩盖原错误。

最新尝试失败或仍在运行时，`finalize`/`verify` 拒绝用旧运行记录宣称当前任务完成。先前发布文件保留，但不能替代本次结果。恢复须成功生成新运行，再完成绑定该运行的实际审核和发布。历史任务尚无尝试记录时保持兼容；该机制不是防止人为删除或篡改本地文件的安全边界。

先完成本轮整页检查并汇总已知问题，再一次修改所有受影响的配置及依赖，不重新写整份Tree。写嵌套对象补丁`patch.json`，然后：

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py revise --task-dir artifacts/<任务> --input artifacts/<任务>/patch.json
```

`revise`从当前run保存的job递归合并对象，数组明确整体替换（可先读当前数组仅改需要的成员）；false/null作为真实数据保留，不解释为删除。生成新的run和复核清单，旧run不改动。未改区域配置完整保留；当前仍整体进行轻量渲染，以检测共享表格宽度和相邻布局的影响，不宣称已实现局部DOM编译。

只有同一原图、上次已通过并封存、运行代码与官方CSS／图标不变，且组的来源、绑定子树、三态语义DOM、computed样式、区域像素与全局节点几何均一致时，才列入`reusableGroups`。变化、新增、移动、失去绑定或无法证明未受影响的组重新检查；含排除项的组额外要求整张三态截图相同。新原型一律重新来源校对。每次仍重新确认全局四类结论和全部关系。复用仅省去已证实不变细节的重复审阅，不依据旧runId或旧PASS直接放行。

## 预检与计时

首次截图前的Table排版预检依据实际官方computed font、单元格padding、文字、Avatar及Button自然宽度计算列最小空间，记录在`qa.json.layoutSizing`。通过官方width/minWidth属性解决内容挤压，不修改官方CSS；要求保留特定列宽/换行时可设置该列`fitContent:false`，仍需视觉复核。复杂分组表头等未覆盖路径不宣称已自动排版验收。

`timing.json`记录计时器启动时间、每次输入准备/Core/机器渲染耗时及复核等待；计时器不能验证用户请求真正开始的时间，因此启动至发布的时间仅为耗时下限，包含的范围以实际记录为准。未验证请求起点时，低于目标的下限不能证明达标（`targetMet: null`）；下限已超过目标则可标记未达标。旧记录即使标记为 `request-start`，也不能据此证明请求起点。已有工具合并记录的时段不能声称已精确拆分；若需分析输入编写、工具等待、截图校对及修正耗时，在原计时记录中追加真实事件时间，不新增计时报告或为每个动作调用一次工具。5分钟仍是端到端目标，尚不能保证；不以机器秒数替代总耗时。整页设计并入原步骤、已核实用法复用、一次集中校对及局部配置修正用于减少返工，不扩大步骤数量。

用户要求阶段耗时或定位瓶颈时，记录可核实的准备/识图、Tree与复扫、各次生成调用起止、检查与修正、复核和发布调用起止，以及写入失败重试的时间点；与现有操作合批记录，必要时间点可用可用时钟记录并持久化。调用总墙钟时间与工具内部已测处理时间分别报告；二者差额只称未拆分开销，除非有更多证据，不归因于某一种进程或工具。并行阶段有重叠，不将其简单相加；未测细项标明未知。真实请求起点不明时，总耗时仍是首次可核实时间起的下限。

需要拆分阶段时，可在对应工作**实际完成后**显式记录事件（不要求每个动作都调用）：

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py event --task-dir artifacts/<任务> --event-name "Tree完成"
```

事件追加到已有 `timing.json.events`，仅记录调用时的 UTC 时间和调用者填写的名称；命令不推断观察、复扫或审阅是否完成，也不会自动计算这些阶段的用时。必须先启动计时，未记录的阶段保持未知。涉及工具等待的区间只能据已记录时间如实说明，不将其全部归因于模型或浏览器。
