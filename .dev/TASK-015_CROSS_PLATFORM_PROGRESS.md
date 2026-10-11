# TASK-015 双平台内容与布局槽位进展

2026-10-09，仍为 IN_PROGRESS，不作为整个任务通过凭据。

## 已实际验收

- Figma：占位文字、选中内容、按钮文字、独立表头、静态内容五项修改。独立完整 PNG 和节点读回通过，70 个其他节点完全不变。
- Penpot：相同五项修改的独立原生证据通过，72 个其他节点完全不变。
- Penpot：已有关联 Input 实例原位换为来源 Select。保持实例 ID、逻辑名称、位置与来源尺寸，74 个其他节点不变；实例区域 PNG 与现有来源 Select 实例像素一致。首次 SDK 自动改名导致拒绝的回执保留。

原始回执、失败回执、完整原生图片及子任务 QA 分别保存于 adapters/figma/metadata/section-content-acceptance、adapters/penpot/metadata/primitive-content-acceptance、adapters/penpot/metadata/section-swap-acceptance。三个 proof-manifest 绑定现有证据文件字节，不代表完整 TASK-015 通过。Figma 原始执行脚本未单独落盘，不将现有运行时文件冒充当时完整工具调用脚本。

## 本次新增

- Core 的 cellSlots 将来源绑定标签、控件、图标、内容、动作组合为现有 Cell 内的角色 Frame；主映射组件自动保留，不允许用伴随槽位覆盖主角色。
- 组件保持正式 Component IR 的来源尺寸；图标绑定正式 SVG 字节和 viewBox；拒绝不存在于语义证据的文字、超出 Cell 的内容、未知令牌、重复 ID 和拉伸组件。
- 修改槽位只产生相关 Section 操作，未变 Section 保持相同检查点。保持已有 Cell ID 和尺寸。
- Penpot 新入口仅填充执行账本中已有的空角色 Frame；文件、页面、根、完整快照、字体、真实来源组件与原生溢出均有预检或读回约束。原生六类槽位已在双平台独立验收通过。

## 验证

本轮完整 Python 回归 356 项通过；此后新增 Penpot 五类内容证据反例测试 2 项通过。完整 Node 回归 100 项通过；此后新增原生槽位 API 契约测试 2 项通过。Core 架构检查通过。新增测试不冒充真实平台执行。

## 尚未完成

全任务收口、检查点说明和最终回归。双平台六类槽位证据位于各自 metadata/cell-slots-acceptance：Figma 保留8个容器、新增12个节点，Penpot保留8个容器、新增16个节点，来源关联和完整PNG均通过。实际执行脚本单独落盘。TASK-016、TASK-017 尚未启动。

首次端到端原型已按用户决定冻结为“姓名／状态／角色”，见 ACCEPTANCE_PROTOTYPE_DECISION.md；操作验收中的文字修改不改变该冻结原型。
