# TASK-024 — 平台默认字体绑定与预检

日期：2026-10-12 至 2026-10-13。用户要求新设计使用 Figma/Penpot 默认字体，并提供实际目标文件；本任务限定字体观测和准备阶段预检。

## 实际结果

Figma 0vGWSRoLxBiVPXiZ8xJAX9 / 0:1：默认 Inter Regular 400，真实样式 Semi Bold 600。最终临时节点 133:2 已删除，顶层清单一致，无历史节点修改。首次原生导出正文缺少末尾“启用”；同一节点第二次连续导出完整，独立节点亦复现。探针以第二次导出为样张，正文和标题视觉 PASS，profile PASS。首次自动宽度、固定宽度和隔离诊断证据均保留。

Penpot 91396aad-60c8-808b-8008-c0885ca79899 / 91396aad-60c8-808b-8008-c0885ca7989a：默认 sourcesanspro regular 400，真实 variant 600。临时节点 f10e2645-81b5-80da-8008-c72dda925514 已删除，顶层清单一致，无历史节点修改。两份中文/英文样张目视完整，profile PASS，仅代表字体绑定与样张范围。

Figma 首次样式分类失败已清理临时节点；一次大返回体被主机拒绝并回滚，不作为成功证据。所有观测保留 nativeAcceptance NOT_RUN、releaseReady false。两平台有效中文 fallback 字体身份未验证，不声明字体自身拥有中文覆盖。

## 开发交付

- 两平台可重用默认字体探针，明确目标身份、真实字重和临时节点清理。
- Adapter 侧 profile 预检，不修改 Core、Schema、Validator、历史 Registry、Tokens 或 source locks。
- 8 项新增测试覆盖不同平台 family、错误目标、未清理/旧节点修改、缺失字重、篡改 PNG 复核、无效 PNG、视觉失败和几何/角色错误。
- 最小组件覆盖计划限定 Button/Input/Select/Table 与已锁 Remix 来源；测量和原生准入均 NOT_RUN。
- 实际 CLI：Figma 与 Penpot 均 PASS（仅字体绑定与样张范围）。产物 artifacts/task-024/{figma,penpot}，视觉预览 samples-preview.png。
- core 分组 145 项 PASS；两份探针通过 Node 语法检查，政策与目标绑定 JSON 可解析，Git diff 检查无空白错误。检查日志在 artifacts/task-024/core。

## 后续依赖

新字体组件仍需真实来源测量和独立原生验收；Figma 的首次导出遗漏要求后续所有文字样张以连续第二次原生导出复核。字体准备不等于 A–H 页面/组件能力完成。
