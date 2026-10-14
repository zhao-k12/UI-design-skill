# TASK-051 — V0.2 独立输入锁与双端 Adapter 预检

日期：2026-10-14。状态：Core 与 Figma/Penpot Adapter 预检 PASS；原生完整页面与最终视觉 QA 尚未执行。架构兼容记录见 [TASK-051_ARCHITECTURE_CONFLICT.md](TASK-051_ARCHITECTURE_CONFLICT.md)。

`scripts/build_v02_acceptance_input.py` 从冻结 V0.1 原型语义和容器几何、TASK-047 准入的 V0.2.3 官方组件尺寸、TASK-049 两个 Remix 图标绑定、TASK-050 双端默认字体文字包络，生成独立的 `examples/acceptance-prototype-v02/` 输入。每个合成测量节点标记来源种类，源文件与输出文件各有 SHA-256 锁；旧包保持原状。组合规则复算字段高度 62/52、导出操作 60×24、表头加 Table Body 1392×192；动态布局在 1920 宽页面中将四列扩为每列 448，固定组件仍使用其已准入尺寸。

完整流水线首次暴露固定 Table Body 先检验空 `props`、后提取独立表头的顺序问题；修正后仍保留三个来源表头并保持原生 Table 实例空 `props`。V0.2 Figma 改走基础 Adapter，双端版本锁为 `0.1.0`；V0.1 仍走原有内容 Adapter 路径。

来源迁移审计 `READY_FOR_PREFLIGHT`、无阻塞。独立新目录的生产 CLI `--profile v0.2` 通过全部 Core 阶段与双端 Adapter 预检：9 个语义项、4 个组件实例、2 个图标，生成 Page 为 1920×1080；详情见 `artifacts/task-051/preflight-summary.json` 和其锁定的预检产物。`nativeExecution=NOT_RUN`，`finalVisualQa=NOT_RUN`，所以这一步没有宣称最终页面通过。

相关回归：V0.2 Profile 3 项、组件装配 6 项、旧流水线 8 项、迁移就绪 3 项、来源几何 2 项均通过。下一步将同一最终 UI-IR 和已锁定计划实际写入两端设计文件，再做独立读回、截图及双端视觉验收。
