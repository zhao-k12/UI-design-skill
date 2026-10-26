# 常见页面的5分钟目标

新任务只用这份说明和SKILL入口即可开始。节点与Table槽位有疑问时再读[组合契约](HTML_COMPOSITION.md)，首次官方能力再查其源码；不要每页重读历史开发记录。5分钟包含理解、工具等待、视觉校对及修正，不是硬超时或已达成的性能保证。

## 一个入口，两份短输入

尽早记录任务起点（使用新的任务目录）。随后独立读原型，写`job.json`，不写本页prepare/scan程序：

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

`props.data`逐行显式列出，即使原型各行内容相同也不使用`$repeat`。逐项保留实际文字、业务编号、选中／禁用状态及行操作，不生成虚构编号。观察材料仍可按共同特征分组；这不缩写内容Tree或行数据。

`scan.groups`单独填写独立看见的`id/prefix/count/region/traits/visual`及例外，不复制完整初读文字，也不能让程序代替原图复扫。两份数量/特征不同会在Core被拒绝。Tree节点用`sourceGroups:["records"]`绑定整组；关系也可用sourceGroups。执行器展开真实逐项证据，旧完整性门继续核对，不让模型重复书写上百份记录。

## 完整 Tree

所有节点显式填写完整字段与稳定编号，直接表达父子归属，不再使用作者层简写：

```json
{"root":{"id":"toolbar","kind":"container","layout":{"direction":"horizontal","gap":"xs"},"children":[
  {"id":"name-input","kind":"component","component":"Input","props":{"placeholder":"请输入姓名"},"sourceIds":["name-filter"]},
  {"id":"query-button","kind":"component","component":"Button","props":{"type":"primary","disabled":false},"sourceIds":["query-action"],"children":[{"id":"query-label","kind":"text","value":"查询"}]}
]}}
```

节点必须有`id`与`kind`，组件、属性、布局、文字分别使用`component/props/layout/value`等完整字段。`use/p/text/from/stack/default`简写、`definitions/ref`片段引用、隐式文字节点和缺省编号均拒绝输入。数据仍可用明确的`{"bind":"row.xxx"}`绑定标准组件重复模板，实际行集合必须完整列出。

`content-tree.json`保存完整树。检查不仅包含每条文案、编号、true/false状态和变体，还包含品牌、侧栏、顶栏、主内容的父子归属；不能因为文字齐全而随意移动区域。初读、独立复扫与一次综合复核保持原职责，不增加额外审核阶段。历史简写job须人工按来源核对后改为完整树才能重跑，既有HTML不改写。

## 一次看三态，简记结论

render返回`runId`、原图哈希、`reviewSheet`及三张原始截图路径，状态为`REVIEW_REQUIRED`。先取回`review-sheet.png`，对照原图做同一次综合校对；文字、间距或小图标看不清时放大原始截图，不能因缩略图不清而确认。运行PASS不代表已目视通过。

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

finalize运行原有综合来源/视觉门；通过后才把`page.html`与`delivery.png`发布到任务根目录，写交付回执。计划、三态原图、合并图或页面被修改均使当前复核失效。

## 局部修正与失效

只修改有问题的配置，不重新写整份Tree。写嵌套对象补丁`patch.json`，然后：

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/html_fast_workflow.py revise --task-dir artifacts/<任务> --input artifacts/<任务>/patch.json
```

`revise`从当前run保存的job递归合并对象，数组明确整体替换（可先读当前数组仅改需要的成员）；false/null作为真实数据保留，不解释为删除。生成新的run和复核清单，旧run不改动。未改区域配置完整保留；当前仍整体进行轻量渲染，以检测共享表格宽度和相邻布局的影响，不宣称已实现局部DOM编译。

只有同一原图、上次已通过并封存、运行代码与官方CSS／图标不变，且组的来源、绑定子树、三态语义DOM、computed样式、区域像素与全局节点几何均一致时，才列入`reusableGroups`。变化、新增、移动、失去绑定或无法证明未受影响的组重新检查；含排除项的组额外要求整张三态截图相同。新原型一律重新来源校对。每次仍重新确认全局四类结论和全部关系。复用仅省去已证实不变细节的重复审阅，不依据旧runId或旧PASS直接放行。

## 预检与计时

首次截图前的Table排版预检依据实际官方computed font、单元格padding、文字、Avatar及Button自然宽度计算列最小空间，记录在`qa.json.layoutSizing`。通过官方width/minWidth属性解决内容挤压，不修改官方CSS；要求保留特定列宽/换行时可设置该列`fitContent:false`，仍需视觉复核。复杂分组表头等未覆盖路径不宣称已自动排版验收。

`timing.json`记录任务起点、每次输入准备/Core/机器渲染耗时、工具和复核等待及总耗时。漏掉start时只报告渲染起计，`targetMet`为null，不能宣称收到原型起5分钟达标。正式速度目标还需真实新原型的完整实测；开发配置测试只验证入口和计时机制。
