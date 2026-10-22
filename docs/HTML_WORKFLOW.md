# 原型 → iView HTML 页面

HTML 是当前可选的交付平台。原型理解、统一内容 Tree、规范化布局决策和 24 栅格仍按主流程执行。页面使用锁定的 View UI Plus 1.3.24 Vue 组件与官方 CSS，布局容器使用项目页面规则。只输出一个可离线打开的 `page.html`：同一页面依次进入彩色骨架、默认文案组件和原型内容交付三个状态，页面顶部可切换查看。每个状态单独保存截图与 QA，不再生成三份 HTML。Penpot 继续搁置。

## 执行

阅读本次原型并独立编写来源观察、内容映射、布局意图和计划。先运行 HTML 内容模式的 Core，避免把 Figma 固定文案当成网页的准入条件；此模式仍逐条核对来源证据、正式组件映射、布局和 UI-IR。再准备 V0.3 分阶段目录，完成内容 Tree、布局质量和 iView 规范 QA。三项未 PASS 时不得导出 HTML。HTML 导出不会把旧 Figma QA 当成本次浏览器 QA，也不能沿用旧原型的审核指纹。

```powershell
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_html_pipeline.py artifacts/<任务>/input --output-dir artifacts/<任务>/core
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/prepare_revised_workflow.py --help
rtk proxy .venv/Scripts/python.exe -X utf8 scripts/run_revised_figma_stages.py --help
```

准备分阶段目录后，按 `tree-qa`、`layout-qa`、`iview-qa --delivery-mode html-official-runtime` 的顺序运行。`page_content_tree_qa.json` 或 `page_content_tree_review.json` 中须有与当前 Tree 指纹匹配的 PASS，且后两项均 PASS。各阶段的完整参数以相应命令的 `--help` 为准。

```powershell
rtk proxy node scripts/export_html_page.mjs --core-dir artifacts/<任务>/core --staged-dir artifacts/<任务>/staged --source-dir artifacts/<任务>/input --output-dir artifacts/<任务>/html-r1
```

输出目录必须为空。程序只写入一次 `page.html`，在同一个 Chromium 标签页中按骨架 → 默认组件 → 交付内容的顺序切换并验收；每一步 PASS 后才进入下一步。直接打开文件默认显示交付内容，顶部按钮可查看之前两个状态。`skeleton.png`、`component.png`、`delivery.png` 与 `html_workflow_qa.json` 保存逐阶段证据，出现问题可从对应状态重新生成，不依靠旧页面内容。QA 记录官方源码版本和 CSS 哈希、Tree/UI-IR/组件目录哈希、单页文件与截图哈希、实际组件 DOM、来源项覆盖、逐 Cell 几何、表格占宽、最终文案与溢出检查。`deliverable=true` 仅表示这些明确检查通过，仍需看交付截图与原型做视觉校对。

当前已在用户管理列表页实测 Input、Select、Button、带表头 Table、Remix 设置图标和静态 Text；这些控件由官方组件运行包渲染。其他现有组件虽已接入渲染映射，尚未逐类完成 HTML 页面实测。复杂 CSS、字体回退及未来 HTML→Figma 导入效果仍需独立验收。

HTML 内容模式允许来源支持的组件文字与 Table 行内容随新原型变化；历史 Figma 原生模式继续使用旧版固定内容准入。组件类型、Table 列结构、可用属性、设计 Token 和已定义的布局模式仍由当前正式目录与 Core 规则决定。超出这些范围的新页面需要补充相应的组件或布局契约，不能仅凭浏览器能显示就宣称已验收。当前实测了 1660px 用户管理页和同一来源内的表格行内容变体；后者是开发验证，不是新的用户审核原型。
