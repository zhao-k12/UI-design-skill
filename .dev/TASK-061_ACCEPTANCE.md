# TASK-061 — Checkbox 固定配置双平台默认字体保真门

日期：2026-10-15。状态：PASS（Fidelity Gate）；Registry 准入 `NOT_RUN`，V0.2 仍 `NOT_READY`。

依赖 TASK-058 的锁定 View UI Plus 1.3.24 Checkbox 浏览器来源、TASK-059/060 的双端默认字体候选，以及用户批准的 V0.2 字体改编。范围仅限 `form.checkbox.default.enabled` 的固定文字“启用”、选中且启用、非不确定态、默认尺寸、无外边框、52×21px。正式规则见 [DEFAULT_FONT_CHECKBOX_POLICY.md](../validators/visual/DEFAULT_FONT_CHECKBOX_POLICY.md)。

首次像素对照发现两端原生候选的勾选标记偏低，蓝色方框顶部与底部偏半像素。按官方 CSS 的 4×8px、2px 白色右/下边框及 45 度旋转，修正两端原生矢量；方框在设计画布中以 2px 顶部位置对齐浏览器截图，保留并记录与 DOM 几何 2.375px 的 0.375px 栅格差异。没有改动历史候选证据，修正后的原生独立读回、双次 PNG 和 SVG 单独保存在 [TASK-061 证据](../artifacts/task-061)。

修正后两端方框直边与内部颜色一致，非标记区域差异仅限四角抗锯齿，最大 RGB 通道差 Figma 17、Penpot 39（规则上限 40）。标记高亮区域的 14 个官方像素全部保留，各端多 2 个像素，交并比 0.875；两次原生 PNG 各自逐字节相同。原生主组件、实例、可编辑默认字体文字、白色矢量、SVG 语义和 Penpot 文件校验通过。绑定 PNG 哈希的视觉复核显示“启用”完整可读且无裁剪；中文实际回退字体身份 `UNVERIFIED`。

[正式报告](../artifacts/task-061/checkbox-native-fidelity.json) 为 `gateVersion=0.2.6`、双平台 PASS、`admissionEligible=true`、`registryAdmission=NOT_RUN`。两端 Adapter 的 `checkbox-default-font-fidelity-0.2.6.json` 锁定门槛报告、候选元数据和新原生证据哈希。3 项 Checkbox 测试通过（包括标记像素缺失与错误文字拒绝），Core 架构 8 项检查通过。

下一步仅按上述固定内容范围设计独立 Registry 准入和两端 Adapter 绑定，不得把本次 Gate 扩大为任意 Checkbox 内容或 V0.2 发布就绪。
