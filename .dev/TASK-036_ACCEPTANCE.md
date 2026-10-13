# TASK-036 — 默认字体 Select 的双平台原生候选

日期：2026-10-13。状态：`CANDIDATE_REVIEW`；正式 Fidelity Gate 与 Registry 准入未执行。

以 TASK-023 的 View UI Plus 1.3.24 实际浏览器组件为来源：固定 `modelValue=enabled`，显示文字“启用”，240×32，Ionicons 下拉箭头 U+F116。用户批准 V0.2 字体改编后，Figma 候选使用目标文件默认的 Inter Regular 14，Penpot 新验收文件候选使用默认的 `sourcesanspro` Regular 14。中文实际回退字体身份仍为 `UNVERIFIED`。

Figma 在原已验收 Select 组件上仅改所选文字字体；箭头保留 Ionicons 原生文字节点。Penpot 新验收文件没有 Ionicons 字体，故将旧版已证明与官方字形一致的 U+F116 轮廓从 Figma 原生组件导出并导入为可编辑矢量路径。候选审计核对完整箭头路径的每个坐标（导出浮点误差不超过 0.001），并保留历史字形证明哈希；没有手绘或换成其他图标。

两端主组件均有对应原生实例。独立重复 PNG 导出的 SHA-256 相同；对官方截图，文字区与箭头区分开统计，非文字非箭头核心像素差异为 0。圆角差异分别为 45/48 像素，源箭头区域绝对通道误差分别为 1343/1358，均在本次候选审计阈值内。审计报告与原生 PNG/SVG、读取记录保存在 `artifacts/task-036`；正式候选元数据在两端 Adapter 的 `select-default-font-candidate-0.2.0.json`。

`scripts/default_font_select_candidate_audit_v02.py` 与锁定脚本通过；Select 候选、Input 回归和架构共 12 项测试通过。此步只建立来源可追溯候选，`nativeAdmission=NOT_RUN`、`readyForPageGeneration=false`。下一步分别执行双平台原生保真门，合格后才可按固定“启用”内容范围考虑独立 V0.2 Registry 准入。
