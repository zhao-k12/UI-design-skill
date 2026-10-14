# TASK-049 — 当前 Penpot 文件的 Remix 图标准入

日期：2026-10-14。状态：PASS（两个原生主组件及实例）；完整 V0.2 页面流水线仍 BLOCKED。架构边界见 [TASK-049_ARCHITECTURE_CONFLICT.md](TASK-049_ARCHITECTURE_CONFLICT.md)。

在当前 Penpot 文件 `57949053-620f-8001-8008-c804c8d61529` 的独立候选页 `11686d7e-2c06-8039-8008-c9829eb3f7c3`，从 SHA 锁定的官方 Remix SVG 创建 `remix.settings-3-line` 和 `remix.download-line` 两个 24×24 真实主组件，并创建各自的原生实例。主组件 ID 分别为 `11686d7e-2c06-8039-8008-c982c49f20aa`、`11686d7e-2c06-8039-8008-c982c4af394f`。原生结构、SVG 路径 Float32 编码、黑色填充和独立 PNG/SVG 导出已核验。

两次主组件导出完全一致，主组件 PNG 的 SHA-256 与旧文件中同一官方源码的已准入原生 PNG 完全相同。两次实例导出也完全一致；实例均引用新主组件。`settings-3-line` 实例与主组件在边缘有 1 个像素差异，但源图像比较的差异均位于已批准边缘带内，拓扑、墨迹范围和颜色检查通过。源 SVG 和新文件的原生证据记录于 `adapters/penpot/metadata/icons-native-v02/`，新绑定为 `adapters/penpot/metadata/icon-bindings-0.2.0.json`。旧绑定及旧验收保持原状。

Penpot V0.2.3 组件、V0.2.2 Token 和默认字体页面契约加入两个图标后，Adapter 预检 `PASS`，`nativeExecution=NOT_RUN`（该预检自身未新建页面）。24 项相关回归测试通过，图标审计加固后另有 6 项测试通过。审计会实际复验绑定证据；结合 TASK-047 几何包，`artifacts/task-049/readiness_report.json` 只保留旧输入版本锁和默认字体文字测量两个阻塞。完整原型到页面生成及最终视觉 QA 尚未执行。
