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

原型数据完全重复时，`props.data`也可紧凑写为`{"$repeat":{"count":13,"value":{"name":"李小明","online":"在线"},"exceptions":{"12":{"name":"赵六"}}}}`。程序展开成13条真实数据，第13条仅改姓名，其余字段保留。只有原图确实相同才能复用value，不把独立记录猜成重复；不同业务编号等字段必须依原图写例外或显式数据，不生成虚构编号。越界例外被拒绝，不静默丢弃。

`scan.groups`单独填写独立看见的`id/prefix/count/region/traits/visual`及例外，不复制完整初读文字，也不能让程序代替原图复扫。两份数量/特征不同会在Core被拒绝。Tree节点用`sourceGroups:["records"]`绑定整组；关系也可用sourceGroups。执行器展开真实逐项证据，旧完整性门继续核对，不让模型重复书写上百份记录。

## 一次看三态，简记结论

render返回`runId`、原图哈希和三张截图路径，状态为`REVIEW_REQUIRED`。把三态截图一并取回，对照原图做同一次综合校对。运行PASS不代表已目视通过。

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

finalize运行原有综合来源/视觉门；通过后才把`page.html`与`delivery.png`发布到任务根目录，写交付回执。有问题只改相关Tree或通用能力再render，不复制旧run的复核结论。

## 预检与计时

首次截图前的Table排版预检依据实际官方computed font、单元格padding、文字、Avatar及Button自然宽度计算列最小空间，记录在`qa.json.layoutSizing`。通过官方width/minWidth属性解决内容挤压，不修改官方CSS；要求保留特定列宽/换行时可设置该列`fitContent:false`，仍需视觉复核。复杂分组表头等未覆盖路径不宣称已自动排版验收。

`timing.json`记录任务起点、每次输入准备/Core/机器渲染耗时、工具和复核等待及总耗时。漏掉start时只报告渲染起计，`targetMet`为null，不能宣称收到原型起5分钟达标。正式速度目标还需真实新原型的完整实测；开发配置测试只验证入口和计时机制。
