# V0.2 默认字体 Form：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `form.single.name.empty` 固定静态配置：标签“姓名”，labelWidth 80，右对齐；空值 Input，占位“请输入姓名”，320×34px。Figma 使用当前文件默认 Inter，标签 Regular 14/14，输入组件复用已正式准入的固定占位原生主组件 `141:3`。

Figma 必须保留可编辑标签、原生 Form 主组件与真实关联实例、Input 真实组件实例。官方与 Figma 图片不缩放、不平移；Figma 透明像素合成白底。排除标签和占位文字区域后，仅输入框四角抗锯齿允许至多 41 像素差异，最大通道差 4，其余像素完全相同。标签至少 100 个深色像素，占位以 220 阈值至少 150 个像素且完整在范围内。独立原生读回、PNG/SVG 与候选一致，重复 PNG 逐字节一致；视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
