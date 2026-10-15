# TASK-069 — Switch Figma 单端质量核验

日期：2026-10-15。状态：**FIGMA_QA_PASS / DUAL_PLATFORM_DEFERRED**。用户说明 Penpot MCP 连接在内外浏览器均不稳定，决定暂缓 Penpot 线，其余任务单走 Figma。此处只执行单端质量核验，不更改双平台正式准入条件。

依赖 TASK-067 官方 Switch 来源锁及 TASK-068 原生候选。限定 `form.switch.default.enabled`、文字“开”、44×22px 与 Figma Inter Regular 12。独立读回 Figma 原生主组件及关联实例，再次导出 PNG/SVG；重复 PNG 与候选逐字节一致。结构、颜色、几何、来源截图对齐、文字完整性及哈希绑定视觉复核全部通过。Figma 像素诊断：蓝色实色区、白色滑块中心完全一致；文字以外最大通道差 27（门限 30）；蓝色分类交并比 0.9904（门限 0.98）。

证据见 [单端报告](../artifacts/task-069/switch-figma-qa.json)、[视觉复核](../artifacts/task-069/visual-review.json)及 `artifacts/task-069/figma/`。已锁定 Figma QA 元数据 `adapters/figma/metadata/switch-default-font-fidelity-0.2.8-figma-only.json`。`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，未登记 Registry。Penpot 历史候选保留于 TASK-068，待用户恢复该线后另作正式双端验收。

测试：`python -m unittest tests.test_default_font_switch_gate_v02`，3 项 PASS；独立 Gate PASS。下一步对剩余组件依次做官方来源锁和 Figma 原生候选/单端 QA，持续维持发布未就绪状态。
