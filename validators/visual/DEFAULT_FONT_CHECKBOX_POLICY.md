# V0.2 默认字体 Checkbox 限定保真政策

仅适用于 View UI Plus 1.3.24 `form.checkbox.default.enabled` 的静态 Checkbox：`modelValue=true`、`trueValue=true`、`falseValue=false`、`disabled=false`、`indeterminate=false`、`size=default`、`border=false`，固定文字“启用”，外框 52×21px。Figma 使用当前目标文件已观测的 Inter Regular 14；Penpot 使用当前验收文件已观测的 `sourcesanspro` regular 14。用户批准的默认字体改编允许文字字形与官方浏览器 PingFang SC 不同，不扩展到其他内容或状态。

官方浏览器截图、Component IR、来源锁与两端候选元数据须完整。两端保留可编辑原生文字、原生主组件、关联实例和白色原生矢量勾选标记；蓝色 `#2D8CF0`、文字 `#515A6E`、2px 方框圆角和 16×16 方框保持来源结构。官方 DOM 顶部为 2.375px；原生画布为对齐浏览器截图采用 2px 的像素栅格位置，必须记录这个 0.375px 差异，不得隐瞒。勾选标记路径按官方 CSS 的 4×8px、2px 右/下边框及 45 度旋转重建。Figma、Penpot 各自的两次原生 PNG 导出必须逐字节一致，SVG 须保留方框、白色标记、来源颜色和文字语义。

白底合成后，来源方框的非标记区域只允许四角抗锯齿差异：位置限于 x=0..1、14..15 且 y=2..3、16..17，最大 RGB 通道差不超过 40。蓝色直边与内部填充不得有其他差异。标记区域 x=3..13、y=5..14 以亮度 ≥220 的高亮像素核对：来源高亮像素必须全部保留，最多额外 2 像素，交并比至少 0.875。该余量只覆盖当前两种原生矢量栅格化与浏览器 CSS 栅格化的边缘抗锯齿；不得据此变更标记结构或扩大配置范围。两字各须有至少 20 个深色像素且不裁剪；人工视觉复核需绑定 PNG 哈希。

Gate PASS 只授予上述固定配置的 Registry 准入资格，不能直接登记 Registry 或声明 V0.2 已发布。中文实际回退字体身份若无原生证据，记录为 `UNVERIFIED`。
