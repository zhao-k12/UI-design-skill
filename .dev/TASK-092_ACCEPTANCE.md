# TASK-092 — Drawer Figma 默认字体原生候选

日期：2026-10-20。状态：**CANDIDATE_REVIEW**；单端独立 QA 与双端正式 Fidelity Gate 尚未完成。

从 TASK-091 官方 `overlay.drawer.detail.open` 来源构建 Figma 原生主组件 `226:8` 和真实关联实例 `226:13`，位于文件 `0vGWSRoLxBiVPXiZ8xJAX9` 的页面 `226:2`。固定面板 320×500px，标题区 51px、正文区 449px；“详情”和“抽屉内容”为可编辑文字，使用 Figma 默认 Inter。背景、标题、正文、分隔线绑定四项来源颜色变量；阴影保持官方 0/4/12、15% 黑。

[候选审计](../artifacts/task-092/drawer-candidate-audit.json)九项检查 PASS，包含官方来源锁、组件关联、几何、变量、默认字体、阴影、重复 PNG/SVG 和 344×524px 导出尺寸。原生读回及导出见 `artifacts/task-092/figma/`；候选元数据见 `adapters/figma/metadata/drawer-default-font-candidate-0.2.0.json`。人工预览确认标题、正文、分隔线和面板阴影可见。测试：`python -m unittest tests.test_default_font_drawer_candidate_v02`，1 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；尚未进入正式 Registry。
