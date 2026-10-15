# TASK-064 — Radio 固定选中态双平台默认字体原生候选

日期：2026-10-15。状态：`CANDIDATE_REVIEW`；正式 Fidelity Gate 和 Registry 准入均 `NOT_RUN`。

依赖 TASK-063 的官方 View UI Plus 1.3.24 浏览器来源，仅处理 `form.radio.default.enabled`：固定文字“启用”、已选中、启用、默认尺寸、无外边框，来源外框 48×21px。Figma 目标文件 `0vGWSRoLxBiVPXiZ8xJAX9` 新建页 `190:2`、原生主组件 `190:3`、关联实例 `190:7`；Penpot 文件 `57949053-620f-8001-8008-c804c8d61529` 新建页 `0b54f3e1-c822-80b2-8008-caaf714570e5`、原生主组件 `0b54f3e1-c822-80b2-8008-caaf723c9fe4`、关联实例 `0b54f3e1-c822-80b2-8008-caaf723f745e`。

两端主组件均为 48×21px，16×16 白底蓝边圆环、10×10 蓝色圆点、固定“启用”可编辑文字。Figma 使用文件默认 Inter Regular 14px 并绑定已有来源蓝/文字色变量；Penpot 使用文件默认 `sourcesanspro` regular 14px，文件校验无问题。未复用外部 Frames X Radio：它没有锁定为本项目 View UI Plus 官方来源配置。

[候选审计](../artifacts/task-064/candidate-audit.json)和两端独立读回、原生 PNG、重复 PNG、SVG 已保存。两端重复 PNG 各自字节相同，尺寸均为 48×21px；人工查看圆形标记与两字完整可见。两端候选元数据各 7 项检查均通过，状态仍为 `CANDIDATE_REVIEW`。圆环与圆点的像素保真及默认字体字形改编须由后续正式 Gate 量化；不得据此准入 Registry。
