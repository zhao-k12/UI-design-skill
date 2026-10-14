# TASK-045 — V0.2.1 画布宽度 Token 与布局预检

日期：2026-10-14。状态：PASS（1920 宽度与 Adapter 预检）；完整 Canvas/Layout 政策仍未通过。版本冲突与边界见 [TASK-045_ARCHITECTURE_CONFLICT.md](TASK-045_ARCHITECTURE_CONFLICT.md)。

新增 `registries/tokens/v0.2.1/default.json` 和独立 Schema。相对 V0.2.0，Token 映射仅将 `size.page` 从 1440 改为 1920；标题和正文仍是平台无关的 `platform-default` Regular 400。V0.1 与 V0.2.0 原快照不变。Figma/Penpot Adapter CLI 可显式选择 `--token-library-version 0.2.1`，默认仍为 V0.1。

Layout Engine 对 `list-page` 模式实际返回 `status=PASS`、Page skeleton 宽 1920。相同 TASK-043 UI-IR 在两个 Adapter 上使用新 Token 版本预检，均 `status=PASS`、0 issues、`nativeExecution=NOT_RUN`；新报告和脚本保存到 `artifacts/task-045/{figma,penpot}`。7 项定向测试通过，覆盖版本隔离、Token 唯一差异、默认字体保留、布局宽度、错误版本拒绝和迁移审计确定性。

新审计报告在 `artifacts/task-045/readiness_report.json`。旧的 `canvas_width_policy_unresolved` 已解除，但 Layout Pattern 的 Page 高度仍为 `hug`，空列表测试高度仅 144，不能保证目标最小 1080；报告明确保留 `canvas_min_height_unresolved`。其余旧输入版本锁、来源几何、Penpot 图标、CLI 路由和默认字体测量阻断仍在。此任务不重写 TASK-043 原生页，也不宣称完整页面或发布验收通过。
