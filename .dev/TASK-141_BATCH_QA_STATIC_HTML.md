# TASK-141 集中验收与静态 HTML 交付

## 用户决定

用户指出 TASK-140 页面四处组合问题：顶栏图标／头像与文字间距、树形收起符与名称间距、展开／折叠按钮与标题栏分隔线的位置、标题前强调线的粗细和颜色。随后明确担心继续追加串行检查会拖慢生成，并说明只需要静态 HTML。用户批准整理并调整 Skill。

## ARCHITECTURE_CONFLICT 与已批准方向

**原设计**：Skill 要求 Tree、骨架、默认组件、交付各自逐步 PASS；复核文件为每个来源项写四次阶段 PASS；导出器把含 Vue 运行脚本和阶段切换的 `page.html` 直接交付。官方组件会响应 hover 和点击，超出了静态页面范围。已有 QA 关注数量、组件存在与大区域几何，未覆盖组合间距及强调线角色。

**影响**：逐项重复审核增加产出时间和记录量，旧 PASS 容易被误读为局部视觉匹配；交付 HTML 带多余的交互和审核控件。

**批准的迁移**：保留四类结论而非四轮独立审核。来源关键歧义和缺组件先阻断；同一 UI-IR 一次生成三态，在同一浏览器会话集中截图与审查。关系只记录共同规则及受覆盖实例，例外单列；失败只重建受影响部分。官方组件和整页组合依据按锁定版本复用。交付 `page.html` 从已渲染的最终 DOM 提取，删除脚本与审核控件，以非视觉的指针冻结避免 hover／点击变化，保留官方 CSS、文字节点和固定选中外观。

## 实施和验收边界

- `SKILL.md`、`docs/HTML_WORKFLOW.md`、`docs/PROTOTYPE_OBSERVATION_QA.md` 改为集中审核与静态交付；图标—文字、头像—文字、树符—名称、按钮—容器分隔线、装饰强调角色纳入已有审核类别。
- `scripts/audit_prototype_observations.py` 支持 `batched-v2`：顶层四类一次性结论，关系按组检查；旧逐项格式仍可读取，不重写历史证据。
- `adapters/html/static-snapshot.mjs` 复用浏览器已渲染的官方 DOM。`scripts/export_html_page.mjs` 仅在综合 PASS 后写静态 `page.html`；内部预览发生 FAIL 时保留供修复。TASK-140 的本地页面亦作静态导出验证。
- 静态冻结回归核对无脚本、无切换控件、按钮不可触发 hover，保留所选状态与文字。TASK-140 原视觉审核记录锁定的是旧交互版截图；静态截图替换后 `source-visual-qa.json` 正确报 `screenshot_mismatch:delivery`，不能沿用旧 PASS。此验证不等于 HTML→Figma 导入保真；用户指出的四处组合视觉问题保持未修正，也不记录新视觉 PASS。
