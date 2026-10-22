# 原型 → iView HTML 页面（首版）

HTML 是当前可选的交付平台。原型理解、统一内容 Tree、规范化布局决策、24 栅格、彩色组件骨架、默认文案组件页、原型内容填入和最终校对仍按主流程执行。页面使用锁定的 View UI Plus 1.3.24 Vue 组件与官方 CSS，布局容器使用项目页面规则；输出是三个各自可离线打开的 HTML 文件和对应 PNG/QA，不需要向 Figma 写入节点。Penpot 继续搁置。

## 执行

先用现有 Core 流程生成并验收本次原型的 UI-IR，再准备 V0.3 分阶段目录，完成 `page_content_tree_qa.json`、`layout_quality_qa.json`、`iview_conformance_qa.json`。三项未 PASS 时不得导出 HTML。HTML 导出不会把旧 Figma QA 当成本次浏览器 QA。

```powershell
rtk proxy node scripts/export_html_page.mjs --core-dir artifacts/<任务>/core --staged-dir artifacts/<任务>/staged --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/html-r1
```

输出目录必须为空。程序依次写入并在 Chromium 中验收 `skeleton.html`、`default.html`、`final.html`；每一步 PASS 后才进入下一步。`html_workflow_qa.json` 记录官方源码版本和 CSS 哈希、Tree/UI-IR/组件目录哈希、各阶段文件与截图哈希、实际组件 DOM、来源项覆盖、逐 Cell 几何、表格占宽、最终文案与溢出检查。`deliverable=true` 仅表示这些明确检查通过，仍需看最终截图与原型做视觉校对。

当前已在用户管理列表页实测 Input、Select、Button、带表头 Table、Remix 设置图标和静态 Text；这些控件由官方组件运行包渲染。其他现有组件虽已接入渲染映射，尚未逐类完成 HTML 页面实测。复杂 CSS、字体回退及未来 HTML→Figma 导入效果仍需独立验收。

此首版复用现有 Core 的正式组件与内容范围。新原型若改变现有组件的内部文案或表格数据，Core 仍可能报告 Unsupported；HTML 渲染能力并不自动解除 Core 的历史固定内容约束。此缺口不得用虚构 PASS 或绕过 Tree、来源与布局检查掩盖。需为 HTML 路线另建可配置内容契约和相应 QA 后，才能宣称支持任意新文案或表格记录。
