# TASK-056 — Tag 固定配置双平台默认字体保真门

日期：2026-10-15。状态：PASS（Fidelity Gate）；Registry 准入 `NOT_RUN`，V0.2 仍 `NOT_READY`。

依赖 TASK-054 的锁定 View UI Plus 1.3.24 Tag 浏览器来源、TASK-055 的 Figma/Penpot 默认字体原生候选，以及用户批准的 V0.2 字体改编。范围仅限 `data.tag.default.enabled` 的固定文字“启用”、默认尺寸/颜色、不可关闭、不可勾选、已选中、42×22px。正式规则见 [DEFAULT_FONT_TAG_POLICY.md](../validators/visual/DEFAULT_FONT_TAG_POLICY.md)。

重新从两端原生文件独立读回主组件、文字、实例与样式，并再次导出 PNG/SVG。Figma 与 Penpot 的新 PNG 各自重复导出逐字节相同，且与 TASK-055 候选 PNG SHA-256 相同；SVG 保留原生结构、颜色与文字。Penpot SVG 唯一的字节变化是每次导出新生成的描边分组 UUID，门槛只规范化该 `strokes-<UUID>-<主组件 ID>` 属性后比较完整 XML；其他属性或图形改变仍失败。

白底对齐后，固定字形区外的差异仅在四角抗锯齿：Figma 24 像素、最大通道差 3；Penpot 32 像素、最大通道差 2。直边与非文字内部逐像素一致。两字可见深色像素分别为 Figma 66/66、Penpot 54/51，外框边缘无字形像素；绑定 PNG 哈希的视觉复核无缺字或裁剪。中文实际回退字体身份仍为 `UNVERIFIED`。

[正式报告](../artifacts/task-056/tag-native-fidelity.json) 为 `gateVersion=0.2.5`、双平台 `PASS`、`admissionEligible=true`、`registryAdmission=NOT_RUN`。两端 Adapter 的 `tag-default-font-fidelity-0.2.5.json` 锁定门槛报告、候选元数据和新原生证据哈希。`scripts/default_font_tag_gate_v02.py` 重跑来源、候选、独立结构、PNG/SVG、像素和视觉检查；4 项 Tag 测试通过（包括错误文字与 SVG 语义变更拒绝），Core 架构检查通过。

下一步仅可按上述固定内容范围设计独立 Registry 准入和两端 Adapter 绑定，不得把本次 Gate 扩大为任意 Tag 内容或 V0.2 发布就绪。
