# V0.2 默认字体 Upload：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `data.upload.drag.empty` 固定拖拽空态：文案“上传文件”、无上传列表，320×82px。Figma 使用当前文件默认 Inter，保留可编辑文字、原生 Upload 主组件与关联实例。背景、虚线边框及文字绑定来源颜色变量。

官方与 Figma 原生 PNG 均以白底 320×82px 对齐，不缩放、不平移。排除文字区后，差异只能在距外边缘不足 5px 的区域，差异像素至多 667，最大通道差 35；其余非文字像素必须完全一致。这是 CSS 虚线与 Figma 原生描边的栅格化差异，并不放宽框内部像素。文字区至少 200 个深色像素，字形完整位于范围。独立原生读回和 PNG/SVG 与候选一致，重复 PNG 逐字节一致；视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
