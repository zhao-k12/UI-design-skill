# V0.2 默认字体 Cascader：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `form.cascader.region.selected` 固定两级选中闭合态：“浙江 / 杭州”，240×32px。Figma 使用当前文件默认 Inter，保留可编辑文字、原生 Cascader 主组件和关联实例；输入框与官方下箭头同源于已准入 Select 基础，绑定 Cascader 专用颜色变量。

官方与 Figma 原生 PNG 均以白底 240×32px 对齐，不缩放、不平移。排除文字和箭头区域后，只允许四个 5×5px 圆角内至多 41 个像素差异，最大通道差 4；其余像素必须完全一致。文字区至少 250 个深色像素，箭头区至少 12 个可见像素，均完整位于指定范围。独立原生读回和 PNG/SVG 与候选一致，重复 PNG 逐字节一致；视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
