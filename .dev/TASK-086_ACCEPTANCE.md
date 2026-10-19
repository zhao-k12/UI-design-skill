# TASK-086 — Form Figma 默认字体原生候选

日期：2026-10-19。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-085 官方固定单字段来源。Figma 目标文件 `V0.2 / Default-font Form candidate` 页建立 320×34px 原生主组件 `220:9` 和真实关联实例 `220:10`。标签“姓名”为 Inter Regular 14/14 可编辑文字，80px 右对齐标签槽，文字绑定 `#515A6E` 来源变量。输入框复用已正式准入的固定“请输入姓名”Input 主组件 `141:3`，原生实例 `220:6` 位于 x=80、宽 240、高 32；不重新绘制 Input。

[候选审计](../artifacts/task-086/form-candidate-audit.json)8 项检查 PASS。Figma 独立读回、PNG/SVG、重复 PNG 存于 [证据目录](../artifacts/task-086/figma)，两次 PNG 逐字节一致。候选元数据在 `adapters/figma/metadata/form-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_form_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
