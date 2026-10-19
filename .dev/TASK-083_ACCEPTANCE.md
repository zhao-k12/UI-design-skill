# TASK-083 — DatePicker Figma 默认字体原生候选

日期：2026-10-19。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-082 官方固定日期来源。Figma 目标文件 `V0.2 / Default-font DatePicker candidate` 页建立 211×32px 原生主组件 `218:16` 和真实关联实例 `218:17`。可编辑日期文字 `2024-01-01` 为 Inter Regular 14/21，x=8。白色背景、`#DCDEE2` 1px 边框、4px 圆角、`#515A6E` 文字和 `#808695` 图标分别绑定本候选的来源变量。右侧日历使用已同步并哈希锁定的官方 Remix `calendar-line` 原生主组件 `218:10` 和关联实例 `218:14`，记录其替代官方 Ionicons 的视觉改编。

[候选审计](../artifacts/task-083/datepicker-candidate-audit.json)9 项检查 PASS。Figma 独立读回、PNG/SVG、重复 PNG 存于 [证据目录](../artifacts/task-083/figma)，两次 PNG 逐字节一致。候选元数据在 `adapters/figma/metadata/datepicker-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_datepicker_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
