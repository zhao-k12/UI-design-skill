# TASK-059 — Checkbox 固定选中态 Figma 默认字体原生候选

日期：2026-10-15。状态：`CANDIDATE_REVIEW`；Penpot 候选、正式 Fidelity Gate 和 Registry 准入尚未完成。

依赖 TASK-058 的锁定官方浏览器来源，仅处理 `form.checkbox.default.enabled`：固定文字“启用”、已选中、启用、非不确定态、默认尺寸、无外边框，来源外框 52×21px。Figma 目标文件 `0vGWSRoLxBiVPXiZ8xJAX9` 新建候选页 `182:2`、原生主组件 `182:12` 和关联实例 `182:18`。文字为可编辑的文件默认 Inter Regular 14px；勾选框 16×16px、2px 圆角、来源蓝 `#2D8CF0`，白色勾选标记为原生矢量。候选变量单独存于 `V0.2 / Source Checkbox candidate` 集合，不改已准入 Tag 等组件。

[独立读回](../artifacts/task-059/figma/independent-read.json)、[原生 PNG](../artifacts/task-059/figma/component-native.png)、原生 SVG 和第二次 PNG 导出已保存；两次 PNG 字节相同。来源截图与候选截图均为 52×21；人工查看勾选框与“启用”两字可见。候选锁与检查见 [Figma metadata](../adapters/figma/metadata/checkbox-default-font-candidate-0.2.0.json)，7 项核对均通过。字形已按 Figma 默认字体改编，白色勾选标记与官方 CSS 的像素保真仍须正式量化，不能据此准入。

本任务不更改 Registry、Core 或旧证据；下一步建立 Penpot 原生候选，再定义双端独立 Fidelity Gate。
