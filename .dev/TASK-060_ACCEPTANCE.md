# TASK-060 — Checkbox 固定选中态 Penpot 默认字体原生候选

日期：2026-10-15。状态：`CANDIDATE_REVIEW`；正式双端 Fidelity Gate 和 Registry 准入尚未完成。

依赖 TASK-058 的官方浏览器来源及 TASK-059 的 Figma 候选，仅处理 `form.checkbox.default.enabled`：固定文字“启用”、已选中、启用、非不确定态、默认尺寸、无外边框，来源外框 52×21px。Penpot 目标文件 `57949053-620f-8001-8008-c804c8d61529` 新建候选页 `0b54f3e1-c822-80b2-8008-caa7ac12b701`、原生主组件 `0b54f3e1-c822-80b2-8008-caa7c1f9e5d8` 和关联实例 `0b54f3e1-c822-80b2-8008-caa7c204ac97`。文字为可编辑的文件默认 sourcesanspro regular 14px；勾选框 16×16px、2px 圆角、来源蓝 `#2D8CF0`，白色勾选标记为原生路径。文件校验无问题。

[独立读回](../artifacts/task-060/penpot/independent-read.json)、[原生 PNG](../artifacts/task-060/penpot/component-native.png)、原生 SVG 和第二次 PNG 导出已保存；两次 PNG 字节相同。来源截图与候选截图均为 52×21；人工查看勾选框与“启用”两字可见。候选锁与检查见 [Penpot metadata](../adapters/penpot/metadata/checkbox-default-font-candidate-0.2.0.json)，7 项核对均通过。字形已按 Penpot 默认字体改编，白色勾选标记与官方 CSS 的像素保真仍须正式量化，不能据此准入。

本任务不更改 Registry、Core 或旧证据；下一步执行双端独立 Fidelity Gate。
