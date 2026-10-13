# TASK-034 — 默认字体 Input 双平台原生保真门

日期：2026-10-13。状态：PASS（限固定占位样张）；Registry 准入未运行。

## 保真证据

- 范围为 View UI Plus 1.3.24 `form.input.default.medium`，空值、占位文字“请输入姓名”、240×32、默认静态状态。字体按用户要求分别改编为 Figma Inter Regular 400 和 Penpot sourcesanspro regular 400；政策见 `validators/visual/DEFAULT_FONT_INPUT_POLICY.md`。
- 两端组件和实例的再次原生读取与 TASK-033 首次读取一致，重复 PNG 各自逐字节相同。Figma SVG 原生导出包含五字的字形轮廓、白底及 `#DCDEE2` 轮廓；Penpot SVG 保留准确 Unicode 文本、sourcesanspro 400 绑定、白底、占位色 `#C5C8CE` 与内描边。
- 两端非文字区域除四个 5×5 圆角区外与官方来源截图逐像素相同。圆角白色／`#DCDEE2` 混色最大通道残差均不超过 2。五个占位字每字有可见灰色像素，视觉复核无缺字、豆腐字或裁剪。
- `scripts/default_font_input_gate_v02.py` 将官方来源、候选审计、重复原生导出、SVG、像素分区、视觉复核和 Adapter 候选 Metadata 串联核验，输出 `artifacts/task-034/input-native-fidelity.json` 为 `gateVersion=0.2.3`，两端 `PASS`、`admissionEligible=true`。两端 `input-default-font-fidelity-0.2.3.json` 锁定报告及原生证据 SHA256。

## 限制

Gate PASS 不证明其他占位文字、非空值、尺寸或交互状态的保真。Input 尚未进入新版本 Registry，`registryAdmission=NOT_RUN`、`readyForPageGeneration=false`、`releaseReady=false`。实际中文回退字体名称仍未验证，记录为 `UNVERIFIED`。下一步需沿用户批准的 V0.2 内容范围原则，单独登记这个 Input 固定配置，并对页面组装与两端 Adapter 加强约束。

测试验证错误的 Penpot SVG 文字及圆角异色均不能通过，Core 检查通过。
