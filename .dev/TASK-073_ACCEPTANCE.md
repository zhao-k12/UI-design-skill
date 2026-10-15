# TASK-073 — Pagination 固定三页配置官方运行来源锁

日期：2026-10-15。状态：PASS（官方来源）；Figma 候选与单端 QA 尚未执行，双端正式准入仍暂缓。

按 View UI Plus 1.3.24 官方源码和浏览器运行，锁定 `data.pagination.default.three-pages`：第 1 页、总数 30、每页 10，默认尺寸、非简洁模式、无总数/跳页/页大小控件。真实容器 400×32px；可见五个 32×32px 控件，左至右为禁用上一页、选中 1、2、3、下一页；4px 间距。白色底、4px 圆角、默认边框 `#DCDEE2`（观察 JSON 中 RGB 220,222,226）、选中蓝边 `#2D8CF0`。上一页和下一页由 View UI Plus 自身 `ivu-icon-ios-arrow-*` 图标字体绘制。

[来源证据](../artifacts/task-073/pagination-source)保存 Component IR、浏览器截图、运行环境、源码/CSS 哈希、Manifest 与完整观察记录。`verify_artifacts(..., expected_types={"Pagination"})` 无问题，样张视觉确认数字和箭头完整。来源测试通过。该证据不代表 Figma 原生候选、单端 QA 或正式 Registry 准入。

后续 Figma 候选须遵守仓库功能图标约束：先检查已同步的真实 Remix Icon 组件与现有 Pagination 候选；如官方图标字体与 Remix 视觉不一致，应记录来源与改编差异，不能自行绘制或静默替换。
