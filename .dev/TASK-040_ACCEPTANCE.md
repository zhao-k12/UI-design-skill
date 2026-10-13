# TASK-040 — 默认字体 Table 双平台原生保真门

日期：2026-10-13。状态：PASS（仅限固定三列三行样张）；Registry 准入未运行。

来源为 View UI Plus 1.3.24 `data.table.default` 的真实浏览器静态截图。用户批准的 V0.2 字体改编在 Figma 使用 Inter Regular 400，在替代 Penpot 验收文件中使用 `sourcesanspro` regular 400；中文实际回退字体身份仍记录为 `UNVERIFIED`。限定政策见 `validators/visual/DEFAULT_FONT_TABLE_POLICY.md`。

`scripts/default_font_table_gate_v02.py` 将 TASK-039 候选元数据哈希、原生主组件及实例、26 节点层级、固定九格数据、重复 PNG、原生 SVG、逐字可见性、人工视觉复核哈希和分区像素检查串联为一个门。Figma SVG 含九条 `#515A6E` 原生文字轮廓；Penpot SVG 含九个准确 Unicode 文本及默认字体声明。19 个字在两端的像素窗口内均有可见墨迹；九处文字区域以外对官方截图的差异均为 0。两端重复 PNG 导出各自逐字节一致。

报告保存在 `artifacts/task-040/table-native-fidelity.json`，`gateVersion=0.2.5`，两端 `PASS`、`admissionEligible=true`。Adapter 的 `table-default-font-fidelity-0.2.5.json` 锁定报告、候选元数据及原生 SVG/PNG 哈希。Table 候选与保真门 4 项测试通过，包含篡改文字和非文字像素的拒绝验证。

Gate PASS 不扩展到其他行数据、列、表头、尺寸或交互状态。`registryAdmission=NOT_RUN`、`readyForPageGeneration=false`、`releaseReady=false`；下一步按固定内容范围考虑独立 V0.2 Registry 准入。
