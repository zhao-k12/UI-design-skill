# V0.2 默认字体 Card：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `content.card.default.user-info` 固定配置：标题“用户信息”、默认槽“暂无内容”、240×106px、`bordered=true`、`disHover=true`、`shadow=false`、`padding=16`。Figma 采用目标文件默认 Inter：标题 Medium 16/22，正文 Regular 14/21。中文实际回退字体若无原生证据记 `UNVERIFIED`。

Figma 原生主组件、真实关联实例、标题和正文可编辑文字、来源色变量绑定、4px 圆角、1px `#E8EAEC` 边框与分隔线必须保留。标题区从 (1,1) 起 238×51px；内容区从 (1,52) 起 238×53px。候选与独立复验的原生读回、PNG、SVG 必须一致；PNG 重复导出逐字节一致。人工复核须绑定复验 PNG 哈希。

浏览器与 Figma 两张 240×106px 图片不缩放、不平移。Figma PNG 先以白底合成透明像素。文字区域在标题 x=15..99、y=12..37，正文 x=15..94、y=66..89；文字字形因默认字体改编可不同。区域外应有至少 99.8% 像素逐像素一致，最大 RGB 通道差不超过 3，确保白底、边框和分隔线未变。Figma 标题可见深色像素至少 300 个，位于 x=17..89、y=15..37 内；正文至少 200 个，位于 x=17..89、y=68..88 内，不触及固定文字框外缘。

用户决定暂缓 Penpot，因此本政策只授权 Figma 单端 QA。PASS 仍为 `admissionEligible=false`，不可登记正式 Registry，也不表示 V0.2 发布就绪。历史 Penpot 工作和双平台准入条件保留。
