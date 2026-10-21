# TASK-123 — iView 页面规范冲突与修正边界

用户指出 TASK-122 页面像原型复刻，没有按 iView 设计规范制作，并明确指定“iView 的设计规范”为判据。原流程仅检查语义、既有项目 Token／24 栅格、Figma 实例关系与最终截图，没有独立的 iView 页面级规范门。TASK-122 的布局计划和映射还从上一份用户管理示例复制，不能视为独立设计判断。

官方来源是项目已锁定的 [View UI Plus 1.3.24](https://github.com/view-design/ViewUIPlus) 发布包。`src/styles/custom.less` 定义主色 `#2d8cf0`、正文色 `#515a6e`、Layout 内容背景 `#f5f7f9`、表头背景 `#f8f8f9` 和 24 栅格。当前项目 Token 分别是 `#2563eb`、`#20252b`、`#f4f5f7`，与官方值不一致。用户此前批准的 Figma 平台默认字体改编继续有效，因此不把官方字体族覆盖到新页面。

更严重的组件组合冲突是：正式准入的 `data.table.default` 固定 `showHeader=false`，而 TASK-122 的三列表头由独立 Frame/Text 节点拼接。此前四类 QA 没有发现这一点，因为只核对内容、坐标和主组件关联；这不能称为完整的 iView Table。已存在的带表头 Table 源提取与 Figma 候选证据不能自动变为当前三列固定配置的正式准入。

本次先将 iView 官方变量提取为独立、带源哈希的设计规范快照，增加只读规范审计，使现有页面明确 FAIL，并更正 TASK-122 的交付表述。后续修复应在新版本输入／Registry 中完成：从官方三列表头 Table 配置重新提取与保真验收，使用真正带表头的原生实例；迁移页面颜色 Token，并从 Tree 独立生成布局计划。所有原生页面在新 revision 建立，历史任务与字节锁不原位修改。规范审计的范围应写明，不以少数数值匹配宣称覆盖整个 iView 设计系统。

## 2026-10-21 Figma 修正候选

已从锁定的官方 View UI Plus 运行源提取三列、三条记录、`showHeader=true` 的 Table，根尺寸 1392×182.875，来源逻辑 ID 为 `data.table.headed.3e8dd491df6ae69aabec87c67001c49d02533bb5a94e1e2d765f73a0bddceda8`。Figma [主组件与评审实例](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=271-45) 已创建；独立读取确认四行、12 个可编辑文字、Inter Regular／Semi Bold 样式、iView 色彩变量和真实主组件引用。原生评审截图与官方运行截图已目视对照。

为让用户直接复核修正方向，另外保留了 [彩色骨架](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=272-53)、[默认文案组件页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=272-69) 和 [原型文案页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9/?node-id=273-45)。新页面将旧拼接表头替换成带表头 Table 实例，背景改为 `#f5f7f9`，独立文字改为 `#515a6e`，三页均未覆盖 TASK-122 原件。

另一次 Figma 只读审计给出候选级 `CANDIDATE_PASS`：骨架含 7 个彩色 Cell；默认页和文案页各有 5 个主组件实例，其中 Table 均指向 `271:11`；默认页 5 处独立文字为“文本”，文案页 5 处文字逐项匹配原型，页面背景读回为 `#f5f7f9`。该读回与三页截图仅用于候选复核，不提升为 Registry 准入或完整流程 PASS。

这些 Figma 页面目前是**修正候选**，不是正式流程交付：新 Table 尚未通过版本化 Registry 的原生保真准入，新 Token／Catalog、Core UI-IR 和 Adapter 字节锁也尚未完成迁移。因此新版 `iview-qa` 仍对旧正式资源阻断，不能以候选截图替代 V0.3.1 的最终 `deliverable=true`。后续必须从新版本资源重新跑 Tree、布局、骨架和各阶段独立 QA；Penpot 按用户指示继续搁置。
