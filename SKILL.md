---
name: ui-design-skill
description: Read a UI prototype, normalize its layout against iView rules, and deliver one audited HTML page that progresses through a colored skeleton, official components, and final prototype content.
---

# UI Design Skill

当前交付物是一个可离线打开的 HTML 页面。先阅读 [开发状态](.dev/DEVELOPMENT_STATE.md)、[架构](ARCHITECTURE.md)、[约束](CONSTRAINTS.md) 和 [HTML 执行说明](docs/HTML_WORKFLOW.md)。历史版本及迁移记录保留原始含义；当前任务只执行以下路线。

## 原型 → 页面

1. **理解原型，建立统一内容 Tree**：逐项记录原文、来源位置、内容层级、顺序和业务关系。Tree QA 核对内容正确、完整，缺失或不确定项标为 Review。原型的贴边、空白、控件尺寸和残缺画法不是最终布局依据。
2. **按规范计算布局**：组件视觉来自锁定的 View UI Plus 官方源码、运行包和 CSS；页面级空间使用明确的项目规则。模型先决定容器、24 栅格、内边距、对齐、间距和表格占宽，再由 Core 计算 UI-IR。可补充展示所需容器和留白，不得补造业务字段、操作或记录。Tree、布局质量和 iView 规范检查必须 PASS。
3. **同页骨架状态**：把每个 Cell 的位置、范围、组件类型和颜色标在页面上。核对组件选型、来源项覆盖、区域内边距、栅格、间距和占宽。检查失败时修正 Tree 或布局，并从受影响阶段重跑。
4. **同页组件状态**：将骨架切换为正式组件实例，保留官方默认文案。核对真实组件 DOM、结构、位置、尺寸和默认内容。不得用普通图形模拟缺失组件。
5. **同页交付状态**：将来源绑定的原型内容填入组件与文字区域。逐项对照原型，检查文案、表格数据、组件、布局、溢出和整体截图。只有所有状态 QA 均 PASS 才交付。

只生成一个 `page.html`；默认打开时显示交付状态，页面顶部可切换查看骨架和默认组件状态。各状态独立保存截图和结构化 QA，出现问题时以同一来源重新生成，不依赖被覆盖的页面内容。详细命令和验收边界见 [HTML 执行说明](docs/HTML_WORKFLOW.md)。

## 执行与恢复

按顺序运行 HTML Core、分阶段准备、`run_html_checks.py` 和 `export_html_page.mjs`。检查或渲染失败是待修复工作：读取具体 issue，找出最早受影响的来源、布局、组件或渲染阶段，修正后使用新 revision 重跑依赖阶段。不得复制旧页面、改写原型事实或虚构 PASS。所有任务保存来源指纹、版本锁、checkpoint、截图和 QA；仅在实际浏览器校对通过后报告交付。

当前已实测用户管理列表页的 Input、Select、Button、带表头 Table、静态文字和 Remix 图标。新组件结构、属性或页面模式若超出正式目录和规则，先补来源与验收契约，再生成。当前只处理静态页面，不增加交互或业务逻辑。
