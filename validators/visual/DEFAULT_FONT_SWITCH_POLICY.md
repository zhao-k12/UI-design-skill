# V0.2 默认字体 Switch：Figma 单端质量核验

仅适用于 View UI Plus 1.3.24 `form.switch.default.enabled` 的静态 Switch：`modelValue=true`、`trueValue=true`、`falseValue=false`、`disabled=false`、`size=default`、`loading=false`，固定 open slot 文字“开”，DOM 外框 44×22px。Figma 使用目标文件已观测的 Inter Regular 12。用户批准的默认字体改编允许字形与官方浏览器 PingFang SC 不同，不扩展到其他内容或状态。

用户决定暂缓不稳定的 Penpot 连接，因此本政策只核验 Figma；历史 Penpot 候选保留，但不参与本次门禁。本次 PASS 表示 Figma 单端质量通过，`admissionEligible=false`，不触发双平台正式 Fidelity Gate、Registry 准入或 V0.2 发布。

浏览器元素截图是 44×23px：DOM 根节点 y=24.375px 为分数坐标，截图多含底部一行空白。像素比较必须先确认该行纯白，然后只裁去最底行，使官方 44×22px 内容与原生 44×22px 画布对齐；不得缩放、任意平移或跳过其他行。

Figma 须保留蓝色 `#2D8CF0`、44×22px 圆角胶囊、18×18px 白色滑块（x=24、y=2）、白色文字、可编辑的原生 Inter 文字、原生主组件和真实关联实例。胶囊中央蓝色实色区与滑块中心白色实色区须与浏览器逐像素一致；文字以外区域的蓝色像素分类交并比不低于 0.98。边缘抗锯齿最大 RGB 通道差不得超过 30，且超过 40 的差异只允许发生在含中间色的胶囊或滑块边缘像素；内部实色区不可改变。

“开”字在固定文字框 x=8..19、y=1..20 内至少有 20 个可见浅色像素，不得触及该框外缘。Figma 独立重复导出 PNG，须与候选 PNG 逐字节一致；SVG 须保留来源蓝白与可见字形轮廓。人工视觉复核绑定本次 PNG 哈希。中文实际回退字体身份若无原生证据，记录为 `UNVERIFIED`。
