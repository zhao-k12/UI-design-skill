# TASK-031 — 默认字体 Button 双平台新版本原生保真门

日期：2026-10-13。范围严格限定为官方 View UI Plus `action.button.primary.medium`、文字“查询”、60×32 的静态 Button。用户已批准平台默认字体的新版本改编与重新验收；旧版保真政策和 Registry 未修改。新政策见 `validators/visual/DEFAULT_FONT_BUTTON_POLICY.md`。

## 实际证据

- Figma `Inter Regular 400` 与 Penpot `sourcesanspro regular 400` 的主组件和实例重新独立读取，确认组件 ID、目标文件、文字、字号 14、行高 21、padding、圆角、描边和实例关联。Penpot 新验收文件 ID `57949053-620f-8001-8008-c804c8d61529`，不是已删除的旧文件。
- 两端 Button 的重复独立 PNG 与 TASK-027/028 首次 PNG **逐字节相同**。Figma SVG 导出原生文字轮廓，Penpot SVG 保留“查询”Unicode 文本和默认字体绑定。实际导出、再次读取与人工视觉复核位于 `artifacts/task-031`；提交的 Adapter Metadata 锁定其 SHA256。
- 文字区域的两字均可读、无缺字/豆腐字或裁剪。两端非文字区域除四个 5×5 圆角区外逐像素匹配官方来源；圆角差异都处于锁定蓝白颜色的抗锯齿覆盖关系内。文字轮廓允许随已批准的字体变化；没有沿用旧字体轮廓的 Fidelity PASS。
- `scripts/default_font_button_gate_v02.py` 重新核验官方来源、用户批准政策、0.2.1 活动目标输入锁、两端候选证据哈希、当前原生读取、PNG 稳定性、SVG、独立视觉复核和像素分区。输出 `artifacts/task-031/button-native-fidelity.json` 为 `gateVersion=0.2.2`、两端 `PASS`、`admissionEligible=true`。

## 边界与后续

报告同时明确 `effectiveCjkFontIdentity=UNVERIFIED`：原生 Text 的字体家族绑定不证明中文回退字体的具体名称。当前只是这个 Button 配置具备进入新 Registry 的资格；`registryAdmission=NOT_RUN`、`readyForPageGeneration=false`、`releaseReady=false`。Input、Select、Table 及其他尺寸/状态/内容仍无新版本准入。

反例测试验证错误字体、虚假视觉复核、重复导出漂移、直边改变、缺字和角区异色均不能通过。Core 检查 176 项通过，Git diff 空白检查通过。
