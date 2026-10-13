# TASK-037 — 默认字体 Select 双平台原生保真门

日期：2026-10-13。状态：PASS（仅限固定“启用”样张）；Registry 准入未运行。

来源是 View UI Plus 1.3.24 `form.select.default.medium` 的真实浏览器静态样张：`modelValue=enabled`、文字“启用”、240×32、Ionicons U+F116 箭头。用户批准的 V0.2 改编在 Figma 用 Inter Regular 400，在新 Penpot 验收文件用 `sourcesanspro` regular 400；其他视觉仍以官方来源为准。中文实际回退字体身份未验证，记录 `UNVERIFIED`。限定政策见 `validators/visual/DEFAULT_FONT_SELECT_POLICY.md`。

`scripts/default_font_select_gate_v02.py` 串联 TASK-036 候选证据哈希、双平台原生主组件与实例、重复 PNG、原生 SVG、官方字形轮廓、两字可见性、人工视觉复核哈希和分区像素检查。两端非文字非箭头核心像素差异为 0；圆角最大调色板残差分别为 1.914、0.886（阈值 2）；箭头区绝对 RGB 误差分别为 1343、1358（阈值 1500）。Figma SVG 有默认字体文字轮廓与原生 Ionicons 箭头；Penpot SVG 有准确 Unicode 文本与默认字体绑定，箭头路径逐点吻合来源轮廓（容差 0.001）。两端原生重复 PNG 哈希各自相同。

报告保存在 `artifacts/task-037/select-native-fidelity.json`，`gateVersion=0.2.4`，两端 `PASS`、`admissionEligible=true`。两端 Adapter 的 `select-default-font-fidelity-0.2.4.json` 锁定报告、候选元数据和原生证据 SHA-256。15 项 Select、Input 回归及架构测试通过，包含错误文字及异色圆角负例。

Gate PASS 不扩大到其他选项、占位状态、尺寸或交互状态。`registryAdmission=NOT_RUN`、`readyForPageGeneration=false`、`releaseReady=false`；下一步只考虑用户已批准的固定内容范围准入独立 Registry。
