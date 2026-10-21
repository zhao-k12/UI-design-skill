# 原型生成页面主流程 V0.3.1（Figma 执行）

本流程按用户确认的阶段修订。Figma／Penpot 是执行平台的差异，不是主流程分叉；Penpot 当前搁置。旧任务的 UI-IR、Manifest、原生页面和 Release Gate 不迁移、不覆盖。

开始阶段先锁定视觉规范：目前采用官方 View UI Plus 1.3.24 的来源快照。原型决定页面内容、层级与业务含义；颜色、组件形态和布局间距由规范与已准入组件决定。不能从原型截图直接抄色、抄控件外观，或把原型页面当作最终视觉稿。已批准的 Figma 默认字体改编单独保留。

| 阶段 | 可检查产物 | 准入条件 | QA 要点 |
| --- | --- | --- | --- |
| 1. 页面内容 Tree | `page_content_tree.json` | 原型来源和语义人工复核通过 | 原型信息、层级、文案和布局关系正确完整；必须核对源图可能漏读的内容 |
| 1a. iView 规范审计 | `iview_conformance_qa.json` | Tree QA 通过 | 核对官方版本锁、页面色彩 Token、表头是否来自原生 Table；FAIL 时不允许创建骨架 |
| 2. 彩色组件骨架页 | `annotated_skeleton_page.json` 与保留的原生页面 | Tree QA、iView 规范审计和布局/映射通过 | 组件类型选对，全部 Cell 有标签和颜色，位置、栅格、间距符合规则；独立读取原生页面 |
| 3. 默认文案组件页 | `default_component_page_ui_ir.json` 与另一个原生页面 | 骨架原生 QA 通过 | 使用正式组件实例及主组件默认文案，结构与骨架对应，骨架页仍存在；独立读取 |
| 4. 填入原型内容 | `prototype_content_fill.json` 与原组件页的修改回执 | 默认组件页原生 QA 通过 | 填入后的文案逐项匹配原型，固定内容组件超出准入范围时阻断；独立读取 |
| 5. 最终校对 | `final_prototype_proofread.json` 与最终原生 PNG | 填入内容 QA 通过 | 按 Tree 每项直接对照原型，并检查全页视觉、溢出、组件与间距 |

Core 可以先确定性计算全部候选数据，但每个**原生页面动作**必须按表中顺序推进；预先算出数据不意味着后续阶段通过。旧的 `component_annotation.html` 仍可辅助查看，它不能代替保留的彩色骨架原生页。

准备独立任务目录：

```powershell
.venv/Scripts/python.exe scripts/prepare_revised_workflow.py --run-dir artifacts/<已验收Core运行> --source-dir examples/<原型输入> --output-dir artifacts/<新任务>/staged
.venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged tree-qa --review <逐项核对原型的Tree审核记录.json>
.venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged iview-qa --tokens <任务Token Registry.json> --catalog <任务组件Catalog.json>
.venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged skeleton-script --file-reference <Figma文件Key> --revision r1
```

运行 `figma-skeleton.js` 后，独立读取骨架页并保存执行回执、读取数据和逐 Cell 的选型／位置／间距／完整性复核，再运行 `skeleton-qa --execution ... --readback ... --review ...`。通过后依次使用 `component-script`、`component-qa`、`fill-script`、`fill-qa`、`proofread`。最终仅以含 iView 规范门的新版 `workflow_final_qa.json` 的 `deliverable=true` 作为交付判断。三个脚本分别只执行当前阶段；后阶段缺少前阶段 QA 时拒绝编译。骨架修订使用新任务目录和 revision，避免复用已通过的旧回执。此规范审计目前只覆盖官方来源身份、基础色彩和 Table 表头的明确阻断规则；其他 iView 页面用法仍需持续扩充，不能将局部 PASS 宣称为全部 iView 规范已覆盖。

Figma 原生脚本分别在 `workflow_v03/skeleton_runtime.js`、现有 `adapters/figma/runtime.js` 和 `workflow_v03/fill_runtime.js`。新流程实现隔离在 `workflow_v03/`，不改变已锁定旧 Adapter 的源码集合。原生写入回执只能证明执行；QA 使用另一次读取的节点信息。骨架读取须提供每个 Cell 的类型、逻辑组件 ID、标签、颜色与几何；默认组件页读取须提供节点 ID、文字、真实主组件引用；文案填入读取须提供全部目标文字。最终校对须覆盖 Tree 的每个来源项，并绑定原始原型文件哈希与最终 PNG 字节哈希。

当前 V0.2.7 组件只有已准入固定内容配置。默认组件页内的官方实例保留默认文案；这一版自动填入仅修改实例之外的独立 Text 节点。组件内部需要不同原型文字时，先扩展组件准入和原生文案映射，否则报告 Unsupported，不能复制矩形或静默替换。
