# TASK-089 — Modal Figma 默认字体原生候选

日期：2026-10-19。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-088 官方固定通知内容框来源。Figma 目标文件 `V0.2 / Default-font Modal candidate` 页建立 320×104px 原生主组件 `222:13` 和真实关联实例 `222:14`。标题“提示”为 Inter Medium 16/20，正文“操作已完成”为 Inter Regular 14/21，均可编辑。标题区 51px、正文区 53px，白底、6px 圆角、1px `#E8EAEC` 分隔线及 0/4/12、15% 黑色阴影按来源建立；背景、标题、正文和分隔线绑定来源变量。此固定内容组件不包含遮罩、关闭按钮或页脚。

[候选审计](../artifacts/task-089/modal-candidate-audit.json)9 项检查 PASS。Figma 独立读回、PNG/SVG、重复 PNG 存于 [证据目录](../artifacts/task-089/figma)，两次 PNG 逐字节一致。阴影使原生导出画布扩展为 344×128px，组件本体仍为 320×104px。候选元数据在 `adapters/figma/metadata/modal-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_modal_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
