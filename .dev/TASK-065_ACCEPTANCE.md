# TASK-065 — Radio 固定配置双平台默认字体保真门

日期：2026-10-15。状态：PASS（Fidelity Gate）；Registry 准入 `NOT_RUN`，V0.2 仍 `NOT_READY`。

范围仅限 `form.radio.default.enabled` 的固定文字“启用”、选中且启用、默认尺寸、无外边框、48×21px。依赖 TASK-063 的官方浏览器来源、TASK-064 的双端原生候选，以及用户批准的 V0.2 默认字体改编。验收规则见 [DEFAULT_FONT_RADIO_POLICY.md](../validators/visual/DEFAULT_FONT_RADIO_POLICY.md)。

官方浏览器元素截图为 48×22px，因 DOM 顶边位于分数像素 y=24.875，顶部多出一行纯白。验收程序确认该行为空白后仅裁去该行，再与双端 48×21px 原生导出比较。Figma/Penpot 圆形控件最大 RGB 通道差分别为 22/39（上限 40），选中点中心 6×6px 逐像素一致；蓝色像素交并比分别为 0.9714/1.0。两字各有至少 20 个深色像素，不触及文字外框。

两端原生主组件、真实关联实例、固定文字与平台默认字体、来源颜色及尺寸经独立读回；重复 PNG 与候选逐字节一致。SVG 保留颜色和可见字形；Penpot 仅导出描边分组 UUID 变化，经限定规范化后与候选一致。视觉复核与原生 PNG 哈希绑定。中文实际回退字体身份记为 `UNVERIFIED`。

[正式报告](../artifacts/task-065/radio-native-fidelity.json) 为 `gateVersion=0.2.7`、双平台 PASS、`admissionEligible=true`、`registryAdmission=NOT_RUN`。两端 Adapter 的 `radio-default-font-fidelity-0.2.7.json` 锁定正式报告、候选元数据和新原生证据哈希。4 项 Radio 测试通过，包括中心像素缺失、错误文字和 SVG 语义变更拒绝。

下一步仅按上述固定内容范围设计独立 Registry 准入和两端 Adapter 绑定，不得把本次 Gate 扩大为任意 Radio 内容或 V0.2 发布就绪。
