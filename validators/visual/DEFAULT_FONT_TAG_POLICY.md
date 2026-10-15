# V0.2 默认字体 Tag 限定保真政策

只适用于 View UI Plus 1.3.24 `data.tag.default.enabled` 的静态 Tag：`size=default`、`color=default`、`closable=false`、`checkable=false`、`checked=true`，固定文字“启用”，外框 42×22px。Figma 使用目标文件已观察到的 Inter Regular 12；Penpot 使用当前验收文件已观察到的 `sourcesanspro` regular 12。用户批准的默认字体改编允许文字字形与官方浏览器 PingFang SC 不同，不能据此扩大到其他文字、颜色、尺寸或交互状态。

官方浏览器截图、Component IR、来源锁及候选元数据均须完整；两端必须保留可编辑原生文字、原生主组件与真实关联实例。背景 `#F7F7F7`、描边 `#E8EAEC`、文字 `#515A6E`、1px 内描边、3px 圆角、9px 文字内容起点及 42×22px 外框保持来源结构。导出 PNG 必须与候选阶段及本次独立重复导出逐字节一致；SVG 必须保留背景、描边和文字颜色，Figma 有可见字形轮廓，Penpot 保留 Unicode“启用”及默认字体绑定。Penpot SVG 每次导出会为描边分组生成不同的 UUID；仅规范化这一个已观察到的临时 `strokes-<UUID>-<主组件 ID>` 属性后，要求完整 XML 结构相同，其余 ID 与属性不得忽略。

对齐白底后的非文字区域排除 x=7..34、y=3..18 的固定字形区。其他像素只允许四个 4×4 圆角有差异，其最大 RGB 通道差不超过 3；直边与内部填充必须逐像素相同。两字各须有至少 20 个可见深色像素，且字形不得触及外框边缘或被裁剪。独立原生读回必须确认文字、字体、尺寸、颜色和组件关联；人工视觉记录必须与本次 PNG 哈希绑定。

Gate PASS 只授予上述固定配置的 Registry 准入资格，不能直接登记 Registry 或声明 V0.2 已发布。中文实际回退字体身份若无原生证据，记录为 `UNVERIFIED`。
