# V0.2 默认字体 Select 的限定保真政策

仅适用于 View UI Plus 1.3.24 `form.select.default.medium` 的静态默认状态、`modelValue=enabled`、固定所选文字“启用”、240×32。Figma 使用目标文件默认 Inter Regular 400；Penpot 使用新验收文件默认 `sourcesanspro` regular 400。中文实际回退字体身份未验证，保持 `UNVERIFIED`。

文字区（x=5..59、y=3..28）允许平台默认字体与官方网页字体栈形成字形差异，但必须有完整、可读、无缺字或裁剪的“启用”。组件箭头沿用官方 Ionicons U+F116 字形，不以 Remix 或手绘图替代。Figma 保留原生 Ionicons 文字；Penpot 因新文件无 Ionicons 字体，使用从已验收的原生字形导出的可编辑矢量轮廓。两端原生 SVG 中箭头完整路径坐标与该来源轮廓相差不超过 0.001；因渲染器抗锯齿不同，箭头区相对于官方截图的 RGB 通道绝对误差合计不超过 1500。

非文字、非箭头、非四角的区域必须与官方浏览器截图逐像素相同。四个 5×5 圆角允许不同抗锯齿采样，但像素须为白色与 `#DCDEE2` 内描边的混色，最大通道残差不超过 2。外框仍为 240×32、白底、1px 内描边和 4px 圆角。两端原生 PNG 独立重复导出须逐字节相同；SVG 分别核验 Figma 文字轮廓和 Penpot 准确 Unicode/默认字体绑定。视觉复核需与 PNG 哈希绑定。

Gate PASS 只提供这个固定内容样张的准入资格，不包括其他值、占位状态、尺寸或交互状态；Registry 另行执行有限范围准入。
