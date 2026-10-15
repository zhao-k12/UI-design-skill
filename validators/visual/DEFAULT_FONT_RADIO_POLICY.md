# V0.2 默认字体 Radio 限定保真政策

仅适用于 View UI Plus 1.3.24 `form.radio.default.enabled` 的静态 Radio：`modelValue=true`、`trueValue=true`、`falseValue=false`、`disabled=false`、`size=default`、`border=false`，固定文字“启用”，DOM 外框 48×21px。Figma 使用当前目标文件已观测的 Inter Regular 14；Penpot 使用当前验收文件已观测的 `sourcesanspro` regular 14。用户批准的默认字体改编允许文字字形与官方浏览器 PingFang SC 不同，不扩展到其他内容或状态。

浏览器元素截图是 48×22px：DOM 根节点的 y=24.875px 为分数坐标，截图多含顶部一行空白。像素比较必须先确认该行空白，并将其裁去，使官方 48×21px 内容与原生 48×21px 画布对齐；不得缩放、任意平移或跳过其他行。两端须保留 16×16 白底蓝边圆环、10×10 来源蓝 `#2D8CF0` 圆点、文字色 `#515A6E`、可编辑原生默认字体文字、原生主组件和真实关联实例。设计画布采用 y=2px 整数栅格使截图对齐，记录与 DOM 相对顶部 2.375px 的 0.375px 差异。

裁切对齐并合成白底后，控件区域 x=0..15、y=0..20 的 RGB 最大通道差不得超过 40；中心实色区 x=5..10、y=7..12 必须逐像素一致；蓝色像素分类（蓝通道至少比红通道高 80）不得产生明显形状丢失。这个差值上限只覆盖已观察到的浏览器/Figma/Penpot 圆形边缘抗锯齿；不得扩大配置范围或改动圆形结构。两字各须有至少 20 个可见深色像素，且不触及文字区域外框。两端各自独立重复导出 PNG，须与候选 PNG 逐字节一致；SVG 应保留来源颜色，Penpot 保留 Unicode“启用”和默认字体，Figma 保留可见字形轮廓。Penpot 每次导出仅允许圆环描边分组 UUID 变化，规范化该 ID 后 SVG 结构必须一致。

人工视觉复核绑定本次 PNG 哈希。Gate PASS 只授予该固定配置的 Registry 准入资格，不等于登记完成或 V0.2 发布。中文实际回退字体身份若无原生证据，记录为 `UNVERIFIED`。
