# V0.2 默认字体 Drawer：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `overlay.drawer.detail.open` 固定右侧打开面板：标题“详情”、正文“抽屉内容”，无关闭按钮，面板 320×500px。Figma 使用当前文件默认 Inter，保留可编辑文字、原生 Drawer 主组件、关联实例、来源颜色与阴影。

官方截图为面板裁切；Figma 导出包含阴影，为 344×524px，面板位于 (12,8)。Figma 透明像素先合成白底，再精确裁切 320×500 面板，不做缩放。排除标题与正文文字区域后，所有像素必须逐像素一致。标题至少 200 个、正文至少 300 个深色像素，字形完整位于文字范围。独立原生读回和 PNG/SVG 与候选一致，重复 PNG 逐字节一致；视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
