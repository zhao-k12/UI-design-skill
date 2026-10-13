# TASK-039 — 默认字体 Table 的双平台原生候选

日期：2026-10-13。状态：`CANDIDATE_REVIEW`；正式 Fidelity Gate 与 Registry 准入未执行。

来源为 TASK-023 中 View UI Plus 1.3.24 的 `data.table.default` 官方浏览器截图。内容限定为无表头、无外边框、无条纹的三列三行表格，列宽各 464，数据依次为“张三/启用/管理员”、“李四/启用/编辑”、“王五/停用/访客”，总尺寸 1392×144。用户批准 V0.2 默认字体改编：Figma 为 Inter Regular 14，Penpot 新验收文件为 `sourcesanspro` Regular 14，行高 48、文字行高 21。中文实际回退字体身份仍为 `UNVERIFIED`。

Figma 候选由已验收的 V0.1 原生组件复制，仅将九个可编辑文字节点改为目标文件默认字体；Penpot 在用户指定的替代验收文件中按官方几何重建 26 个原生节点。两端均含主组件和实例。独立原生读取确认 9 个固定文本、4 条横线、1392×144 尺寸及字体属性。两次 PNG 导出分别逐字节一致；对官方截图，九个文字区域以外均为 0 差异像素。两端文字均经视觉检查，九格内容清晰、无裁切或缺字。

可重复审计见 `scripts/default_font_table_candidate_audit_v02.py`，锁定脚本见 `scripts/lock_default_font_table_candidate_v02.py`。原生捕获、图片及审计报告保存在 `artifacts/task-039`；两端候选元数据为 `adapters/{figma,penpot}/metadata/table-default-font-candidate-0.2.0.json`。2 项针对性测试通过，包含篡改非文字像素的拒绝验证。

此任务仅证明当前固定内容候选；`nativeAdmission=NOT_RUN`、`readyForPageGeneration=false`。下一步执行独立的双平台原生保真门，再决定严格限定内容范围的 V0.2 Registry 准入。
