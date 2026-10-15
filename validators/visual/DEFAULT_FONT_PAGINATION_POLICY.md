# V0.2 默认字体 Pagination：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `data.pagination.default.three-pages`：第 1 页、总数 30、每页 10、默认尺寸，无总数/跳页/页大小控件。官方容器 400×32px，五个 32×32px 控件在 x=0、36、72、108、144。数字 1/2/3 保留为 Figma 默认 Inter Regular 14 可编辑文字。

边框、白底与选中蓝色保持官方来源 `#DCDEE2`、`#FFFFFF`、`#2D8CF0`，使用来源变量。上一页/下一页功能图标只能取自仓库哈希锁定的 Remix Icon 4.9.1 `arrow-left-s-line` 和 `arrow-right-s-line` 原始 SVG；通过 viewBox 缩放，不可手绘。官方浏览器图标字体与 Remix 图标外观的差异属于明示设计改编，不能声称箭头像素完全一致。

两张 400×32px 图片不缩放、不平移；Figma 原生 PNG 以白底合成。排除每个文字/图标中心区域后，其余像素的逐像素一致比例不低于 98%，最大 RGB 通道差不超过 20。候选与独立复验的原生读回、PNG、SVG 应一致，重复 PNG 逐字节一致。人工视觉复核绑定复验 PNG 哈希。上一页图标与下一页图标、数字 1/2/3 均有可见像素，且不触及各自中心区域外缘；选中态由 Figma 原生蓝色边框和蓝色数字共同表示。

Penpot 线按用户决定暂缓。本政策 PASS 仅代表 Figma 单端 QA，`admissionEligible=false`，不可正式登记 Registry 或宣称 V0.2 发布就绪。
