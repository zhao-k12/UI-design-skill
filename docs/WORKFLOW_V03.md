# 原型生成页面主流程 V0.3.2（Figma 执行）

本流程按用户确认的阶段修订。Figma／Penpot 是执行平台的差异，不是主流程分叉；Penpot 当前搁置。旧任务的 UI-IR、Manifest、原生页面和 Release Gate 不迁移、不覆盖。

开始阶段先锁定视觉规范：组件形态采用官方 View UI Plus 1.3.24 的来源快照；页面级空间规则另见 [列表页项目规则](../registries/design-standards/list-page-layout-v0.3.2.json)，它不是 iView 官方对所有页面的固定间距。原型决定页面内容、层级与业务含义；不能从原型截图直接抄色、抄控件外观或把原型画法当作最终几何。已批准的 Figma 默认字体改编单独保留。

## 规范化布局决策

语义 Page Tree 审核后、运行 Core 布局前，模型须阅读原型和设计规则，区分四种输入：①原型明确的内容与业务关系，②官方组件／设计规范，③已登记的项目页面规则，④需要模型判断的视觉推断。模型可补规范化页面所需的容器、留白、对齐和宽度策略，不能补造业务内容；所有推断需写出依据。旧示例的布局计划与测量只可作参考，不得复制后更新哈希当作新页面设计。布局计划的每项尺寸应来自本次内容、目标容器或新准入组件，而非原型截图的偶然留白。

当前 `list-page` 的项目规则要求整页采用 `spacing.page`；页头、查询与列表区域各边采用 `spacing.md` 内边距；列表 Table 填满其区域内容宽度。模型应先决定并记录这些关系，再由 Core 的 24 Grid／Stack／Fill/Hug/Fixed 规则求坐标。若正式 Table 只准入 1392 px，而内容区要求 1840 px，质量门返回组件宽度能力不匹配：先提取官方目标宽度配置、完成 Figma 保真准入与版本迁移，不能在 Figma 中直接拉伸固定实例，也不能保留无依据空白。

布局意图由模型在 Core 前写成独立 JSON，并绑定已审核的语义 `page_tree.json` 指纹及项目规则指纹。当前列表页契约的核心字段如下；`rationale` 应写本页实际判断，而非原样复制示例文字：

```json
{
  "version": "0.3.2",
  "sourcePageTreeSha256": "<已审核 Page Tree 指纹>",
  "ruleSha256": "<list-page-layout-v0.3.2.json 指纹>",
  "pattern": "list-page",
  "geometryPolicy": "prototype-geometry-nonbinding",
  "sections": {
    "header": {"paddingToken": "spacing.md", "basis": "project-page-rule", "rationale": "<页头容器判断>"},
    "query": {"paddingToken": "spacing.md", "basis": "project-page-rule", "rationale": "<查询区容器判断>"},
    "list": {"paddingToken": "spacing.md", "basis": "project-page-rule", "rationale": "<列表区容器判断>"}
  },
  "tableSizing": {
    "user-table": {"policy": "fill-section-content", "basis": "project-page-rule", "rationale": "<表格占宽判断>"}
  }
}
```

`sections` 使用本次 Tree 的 Section ID，`tableSizing` 使用本次 Tree 的 Table 来源 ID，不要求其它原型沿用示例名称。其它页面模式没有已登记项目规则时返回 Review，不套用列表页数值。

| 阶段 | 可检查产物 | 准入条件 | QA 要点 |
| --- | --- | --- | --- |
| 1. 页面内容 Tree | `page_content_tree.json` | 原型来源和语义人工复核通过 | 原型信息、层级、文案和布局关系正确完整；必须核对源图可能漏读的内容 |
| 1a. 规范化布局决策与质量门 | `layout_intent.json`、`layout_quality_qa.json` | 语义 Tree 审核、项目布局规则和 Core 几何就绪 | 模型判断有来源；核对页面及区域内边距、起始对齐、Table 内容区占宽和正式组件尺寸能力；FAIL/Review 时停止原生阶段 |
| 1b. iView 组件规范审计 | `iview_conformance_qa.json` | Tree QA 通过 | 核对官方版本锁、页面色彩 Token、表头是否来自原生 Table；FAIL 时不允许创建骨架 |
| 2. 彩色组件骨架页 | `annotated_skeleton_page.json` 与保留的原生页面 | Tree QA、布局质量、iView 组件规范和布局/映射通过 | 组件类型选对，全部 Cell 有标签和颜色，区域内边距、边界、占宽、栅格与间距符合规则；独立读取原生页面 |
| 3. 默认文案组件页 | `default_component_page_ui_ir.json` 与另一个原生页面 | 骨架原生 QA 通过 | 使用正式组件实例及主组件默认文案，结构与骨架对应，骨架页仍存在；独立读取 |
| 4. 填入原型内容 | `prototype_content_fill.json` 与原组件页的修改回执 | 默认组件页原生 QA 通过 | 填入后的文案逐项匹配原型，固定内容组件超出准入范围时阻断；独立读取 |
| 5. 最终校对 | `final_prototype_proofread.json` 与最终原生 PNG | 填入内容 QA 通过 | 按 Tree 每项直接对照原型，并检查全页视觉、溢出、组件与间距 |

模型的布局意图必须先于 Core 布局计算；Core 可以确定性计算后续候选数据，但每个**原生页面动作**必须按表中顺序推进。预先算出数据不意味着后续阶段通过。旧的 `component_annotation.html` 仍可辅助查看，它不能代替保留的彩色骨架原生页。

任一质量门 FAIL/Review 后，暂停依赖阶段并继续诊断修复：先定位失败所指的来源、Token、组件或原生节点；修正最早受影响项；新版本或新 revision 重跑该项及所有下游 QA。正式组件缺口必须补官方来源、原生保真、Registry 和绑定；设计 Token 冲突必须迁移任务 Token 与版本锁。只有全部质量门 PASS 才交付，不能把第一次 FAIL 当作整个技能的结束。

准备独立任务目录：

```powershell
rtk proxy .venv/Scripts/python.exe scripts/prepare_revised_workflow.py --run-dir artifacts/<已验收Core运行> --source-dir examples/<原型输入> --output-dir artifacts/<新任务>/staged
rtk proxy .venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged tree-qa --review <逐项核对原型的Tree审核记录.json>
rtk proxy .venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged layout-qa --intent <Core前建立的布局意图.json> --plan <本次输入/layout-plan.json> --layout-tree <本次Core/layout_tree.json> --layout-report <本次Core/layout_qa_report.json> --tokens <任务Token Registry.json> --catalog <任务组件Catalog.json>
rtk proxy .venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged iview-qa --tokens <任务Token Registry.json> --catalog <任务组件Catalog.json>
rtk proxy .venv/Scripts/python.exe scripts/run_revised_figma_stages.py artifacts/<新任务>/staged skeleton-script --file-reference <Figma文件Key> --revision r1
```

运行 `figma-skeleton.js` 后，独立读取骨架页并保存执行回执、读取数据和逐 Cell 的选型／位置／间距／完整性复核，再运行 `skeleton-qa --execution ... --readback ... --review ...`。通过后依次使用 `component-script`、`component-qa`、`fill-script`、`fill-qa`、`proofread`。最终仅以含布局质量门和 iView 组件规范门的新版 `workflow_final_qa.json` 的 `deliverable=true` 作为交付判断。三个原生脚本分别只执行当前阶段；后阶段缺少前阶段 QA 时拒绝编译。骨架修订使用新任务目录和 revision，避免复用已通过的旧回执。当前两项规范审计仅覆盖已声明的阻断规则，不能将局部 PASS 宣称为全部 iView 规范已覆盖。

Figma 原生脚本分别在 `workflow_v03/skeleton_runtime.js`、现有 `adapters/figma/runtime.js` 和 `workflow_v03/fill_runtime.js`。新流程实现隔离在 `workflow_v03/`，不改变已锁定旧 Adapter 的源码集合。原生写入回执只能证明执行；QA 使用另一次读取的节点信息。骨架读取须提供每个 Cell 的类型、逻辑组件 ID、标签、颜色与几何；默认组件页读取须提供节点 ID、文字、真实主组件引用；文案填入读取须提供全部目标文字。最终校对须覆盖 Tree 的每个来源项，并绑定原始原型文件哈希与最终 PNG 字节哈希。

当前 V0.2.7 组件只有已准入固定内容配置。默认组件页内的官方实例保留默认文案；这一版自动填入仅修改实例之外的独立 Text 节点。组件内部需要不同原型文字时，先扩展组件准入和原生文案映射，否则报告 Unsupported，不能复制矩形或静默替换。
