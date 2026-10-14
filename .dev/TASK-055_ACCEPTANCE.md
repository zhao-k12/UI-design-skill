# TASK-055 — Tag 固定配置双平台默认字体原生候选

日期：2026-10-14。状态：`CANDIDATE_REVIEW`；Fidelity Gate 与 Registry 准入均 `NOT_RUN`。

依赖 TASK-054 的 View UI Plus 1.3.24 官方浏览器 Component IR 和用户批准的 V0.2 默认字体改编。范围仅为 `data.tag.default.enabled`：`size=default`、`color=default`、`closable=false`、`checkable=false`、`checked=true`、文字“启用”、42×22px。沿用已有 V0.2 组件文件组织；不改 Core、历史证据或正式 Registry。

Figma 目标文件 `0vGWSRoLxBiVPXiZ8xJAX9` 的新页面 `176:15` 建立原生 Tag 主组件 `176:16` 和实例 `176:19`，标签使用文件默认 Inter Regular 12。Penpot 当前验收文件 `57949053-620f-8001-8008-c804c8d61529` 的新页面 `f1153c87-a7fc-80d8-8008-c9a7f252803d` 建立原生主组件 `f1153c87-a7fc-80d8-8008-c9a7f325f8b1` 和实例 `f1153c87-a7fc-80d8-8008-c9a7f35cf91d`，标签使用文件默认 `sourcesanspro` regular 12。两端都保留可编辑文字、真实组件实例、`#F7F7F7` 背景、`#E8EAEC` 1px 内描边、3px 圆角和 `#515A6E` 文字。实际中文回退字体身份仍为 `UNVERIFIED`。

两端独立原生读回、PNG/SVG 以及逐字节相同的重复 PNG 位于 [TASK-055 证据目录](../artifacts/task-055/candidate-audit.json)。[候选审计程序](../scripts/default_font_tag_candidate_audit_v02.py) 核对 TASK-054 来源哈希、固定配置、组件与实例关联、字体、尺寸、SVG 语义、元数据和 PNG。扣除固定文字区后，非文字差异均只在四个圆角：Figma 24 像素、最大通道差 3；Penpot 32 像素、最大通道差 2。两字可见，无裁剪；人工视觉记录见 `artifacts/task-055/visual-review.json`。审计 `issues=[]`，状态仍是 `CANDIDATE_REVIEW`，没有将候选检查误写为保真门通过。

验证：候选审计命令成功；Core 架构检查 PASS；工作区 diff 检查 PASS。下一任务应定义 Tag 固定配置的正式双端 Fidelity Gate 和阈值，重新读取主组件与实例并复验导出；Gate PASS 后才可考虑增加带内容范围约束的独立 Registry 版本。
