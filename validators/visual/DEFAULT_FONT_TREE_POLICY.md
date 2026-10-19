# V0.2 默认字体 Tree：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `navigation.tree.expanded.departments` 固定静态配置：展开的“部门”父节点和“研发部”“设计部”两个子节点，240×79px。Figma 使用当前文件默认 Inter Regular 14/21；实际中文回退字体身份无原生证据时记为 `UNVERIFIED`。

Figma 必须保留三处可编辑文字、原生主组件与真实关联实例。三行 y=0/29/58、高 21px，行距 8px。父节点展开箭头使用已同步的官方 Remix `arrow-right-s-line` 图标组件实例。文字 `#515A6E` 绑定已锁定的来源变量。子节点不出现无来源的功能图标。

官方与 Figma 图片均为 240×79px，不缩放、不平移；Figma 透明像素先合成到白底。排除三个文字区域和父节点箭头区域后，非内容像素须逐像素完全一致。三个文本区域各须有至少 50、75、75 个深色像素；箭头至少 3 个深色像素。独立复验的原生读回、PNG/SVG 应与候选一致，重复 PNG 逐字节一致；人工视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
