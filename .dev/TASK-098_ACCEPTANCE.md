# TASK-098 — Cascader Figma 默认字体原生候选

日期：2026-10-20。状态：**CANDIDATE_REVIEW**；单端独立 QA 与双端正式 Fidelity Gate 尚未完成。

从 TASK-097 官方 `form.cascader.region.selected` 来源构建 Figma 原生主组件 `231:13` 和真实关联实例 `231:19`，位于文件 `0vGWSRoLxBiVPXiZ8xJAX9` 的页面 `231:7`。复用已准入 Select 的 240×32px 原生几何与 Ionicons 下箭头，然后固定为 Cascader 的“浙江 / 杭州”可编辑文字，使用 Figma 默认 Inter Regular 14/30。背景、边框、文字与箭头绑定四项来源颜色变量。

[候选审计](../artifacts/task-098/cascader-candidate-audit.json)九项检查 PASS，包含官方来源锁、组件关联、几何、变量、默认字体、官方箭头、重复 PNG/SVG 和导出尺寸。原生读回及导出见 `artifacts/task-098/figma/`；候选元数据见 `adapters/figma/metadata/cascader-default-font-candidate-0.2.0.json`。人工预览确认两级文字、边框和箭头可见。测试：`python -m unittest tests.test_default_font_cascader_candidate_v02`，1 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；尚未进入正式 Registry。
