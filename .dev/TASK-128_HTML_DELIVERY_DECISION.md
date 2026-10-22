# TASK-128 — HTML 交付路线架构决定

用户于 2026-10-22 明确提出先完善“按原型和 iView 规范生成 HTML”，用 HTML 页面制作减少 Figma 逐节点绘制时间。这是对 `CONSTRAINTS.md` 第 14 条“V0.1 不提前代码生成”和旧架构仅列 Figma/Penpot Adapter 的明确新方向。该授权允许新增 HTML Adapter；旧 V0.1/V0.2 锁与原生验收结论保持历史含义。

当前设计：复用通过的语义 Tree、布局和 UI-IR，在独立 HTML Adapter 中读取正式组件映射，以官方 View UI Plus 1.3.24 运行包和 CSS 输出自包含 HTML。三个可见阶段各自保存文件、截图和浏览器 QA。最终 HTML 不宣称已导入 Figma，也不宣称生成了 Figma 组件实例。

首版范围：用户管理列表页的 Input/Select/Button/带表头 Table、Text 和 Remix 图标实测；来源内容依旧受 Core 已锁定的固定配置约束。新原型文本和表格内容可配置化需要后续版本化契约，不能以 HTML 能动态渲染为由跳过 Core 限制。更多组件需逐类实测。

风险与验收：官方 CSS/运行包字节需保持来源锁；HTML 阶段必须独立检查来源项、实际组件 DOM、逐 Cell 几何、表格填充、文本与溢出。浏览器截图由人工复核。未来 HTML→Figma 导入是否保持文字编辑及组件关联，另立验收，不属于本任务 PASS 范围。
