# TASK-015 验收

## 范围与证据

Core 已在冻结 Cell 内装配来源文字、真实登记组件与六类角色槽位。SourceGeometry 绑定正式 Component IR 和准入 SHA，保持实例原尺寸；materialize 保留 Layout Tree 容器并重新检查 Skeleton、状态和 UI-IR。局部差异测试证明修改内容或角色组合仅输出相关 Section。静态 Text 为显式开启的来源原语，不创建伪组件目录项。

Penpot 原位 Input → Select 替换保留原实例 ID、名称、位置，74 个其他节点不变，区域 PNG 与现有关联 Select 像素相同。首次 SDK 自动改名的失败及恢复证据保留。

双平台五类文字实际更新通过，Figma 70、Penpot 72 个其他节点不变，完整原生 PNG 带外差异为零。表头是原 UI-IR 声明的独立可编辑文字，没有向只含 Body 的来源 Table 伪造内部表头。

双平台六类槽位均先建立空布局，再仅填充既有 role Frame，8 个原容器的 ID、位置、尺寸不变。Figma 新建12节点、Penpot新建16节点；四个组件/图标关联真实来源主组件，两段文字可编辑。1440×80完整原生PNG目视无重叠裁剪，槽位范围外像素差异为零。

完整回执、图片、实际脚本、视觉审查、QA 和哈希见各平台 metadata/cell-slots-acceptance。内容证据见 metadata/section-content-acceptance、Penpot metadata/primitive-content-acceptance；类型替换见 Penpot metadata/section-swap-acceptance。各子报告 fullTask015Acceptance=false 保持原义，本文件负责整体范围说明。

## 边界

原位操作要求实际账本、精确文件/页面/根、当前完整快照或哈希与明确目标。过期、跨文件、来源改变、尺寸溢出、无来源文字或缺字体拒绝。写入后失败保留 PARTIAL 及真实节点账本，不能盲目重试。

源尺寸模式下，无明确内部 envelope 的嵌套组件仍拒绝；外部 cellSlots 使用布局 Frame。Input 真实值、Select 未验收空占位、Table Body 内部 headers 属性继续 Unsupported，不改为近似状态。

首次端到端原型已按用户决定冻结为姓名／状态／角色；局部修改示例不改变冻结原型。完整端到端流水线及 V0.1 Release Gate 属于后续任务，本验收不替代它们。

## 验证

最终全项目回归在 DEVELOPMENT_STATE.md 记录。通过后才加入 Completed Tasks 并进入 TASK-016。
