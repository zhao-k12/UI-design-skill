# TASK-095 — Upload Figma 默认字体原生候选

日期：2026-10-20。状态：**CANDIDATE_REVIEW**；单端独立 QA 与双端正式 Fidelity Gate 尚未完成。

从 TASK-094 官方 `data.upload.drag.empty` 来源构建 Figma 原生主组件 `229:7` 和真实关联实例 `229:9`，位于文件 `0vGWSRoLxBiVPXiZ8xJAX9` 的页面 `229:2`。固定框 320×82px，白底、4px 圆角、1px 内描边虚线（3/2 节距）；“上传文件”为可编辑文字，使用 Figma 默认 Inter Regular 14/21。背景、边框和文字绑定三项来源颜色变量。

[候选审计](../artifacts/task-095/upload-candidate-audit.json)九项检查 PASS，包含官方来源锁、组件关联、几何、变量、默认字体、虚线、重复 PNG/SVG 和导出尺寸。原生读回及导出见 `artifacts/task-095/figma/`；候选元数据见 `adapters/figma/metadata/upload-default-font-candidate-0.2.0.json`。人工预览确认居中文字和虚线边框可见。测试：`python -m unittest tests.test_default_font_upload_candidate_v02`，1 项 PASS。

`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`；尚未进入正式 Registry。
