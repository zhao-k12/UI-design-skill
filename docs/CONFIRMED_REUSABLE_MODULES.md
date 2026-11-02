# 已确认的页面模块与复用边界

本规范归纳用户确认的设计，不包含风电场页面的业务数据。下列数值是用户确认的设计目标；实际支持范围以下方已接入能力为准，不能仅凭阅读此文档宣称生成结果已达到。

## 已接入的样式角色

完整 Tree 的容器或组件可显式填写 `designRole`，目前允许 `page-shell`、`sidebar`、`brand`、`topbar`、`topbar-tool`、`topbar-tool-large`、`topbar-user`、`breadcrumb`、`search-panel`、`search-grid`、`search-field`、`search-label`、`search-actions`、`table-panel`、`table-toolbar`、`table-actions`、`row-actions`、`row-action`、`tab-label`、`tab-count`、`pagination`。角色只选择共享样式；样式在 `adapters/html/confirmed-modules.css`，导出器打包进离线页面。未知角色会被拒绝，不填写角色时旧页面保持原行为。

`scripts/confirmed_modules.py` 提供 `sidebar`、`topbar`、`breadcrumb`、`search_panel`、`table_panel`、`action_column`、`project_logo`、`page_shell`，接受调用者明确给出的菜单、字段、行数据、操作与状态，直接返回标准完整 Tree，既不读取历史页面也不保存引用。侧栏默认注入用户提供的默认 Logo；用户提供项目素材时用 `brand_node=project_logo('project-brand', path)` 替换，支持 PNG、JPEG、WebP 和通过安全校验的 SVG，默认按比例高 32px 并嵌入离线页面。SVG 中脚本、外部资源和不安全标记会被拒绝，遇到不支持的合法 SVG 应说明具体限制并处理，不能冒充成功。顶部栏默认包含五个工具和“用户”演示头像名称，项目身份由本次输入替换，明确传 `username=None` 才移除用户区；`table_panel` 默认演示分页，传 `page=None` 可移除，`active_tab` 显式指定当前页签。Tabs 可配置数量徽标；字段、按钮和菜单项可传 `sourceIds`，其余来源仍须由调用者逐项绑定。

在读取入口与当前原型后，使用这些函数一次组装标准 Tree，再交给现有 `html_fast_workflow.py render` 和 `finalize`；不要把配置作为新的替代 Tree 输入。典型调用（演示变量均为本次任务实际识别的数据）：

```python
from confirmed_modules import sidebar, topbar, breadcrumb, search_panel, table_panel, action_column, page_shell
side = sidebar('side', menu_entries, active_name=active_name, open_names=open_names)
header = topbar('header', username=current_username)
trail = breadcrumb('trail', breadcrumb_labels)
query = search_panel('query', search_fields)
results = table_panel('results', table_columns, table_rows, tabs=status_tabs, buttons=toolbar_buttons, page=page_props)
root = page_shell('page', sidebar_node=side, topbar_node=header, breadcrumb_node=trail, sections=[query, results])
# 将 root 放入当前任务的完整 content，按原型补齐各节点 sourceIds，连同独立观察/复扫写入 job.json。
```

`action_column('actions')` 返回标准表格列；各行显式提供 `actions` 数组，每项包含 `label`、`icon` 和 `tone`（普通为 `''`，危险为 `'danger'`），内容 Tree 顶层 `icons` 显式列出所有可能的 Remix 名称。分页器的左右和下拉箭头由已打包的 Remix 图形呈现。`table_panel` 对没有固定宽度、最小宽度或复杂表头的列默认按本次内容测量并均分剩余空间；遇到显式宽度或复杂表头默认保留原配置，也可显式设置 `equal_gaps=False`。强制均分与这些配置冲突时会报错。静态快照本身不执行脚本：修改数据或视口后需重新渲染才能重新计算列宽，不能声称在已交付静态页面中实时重算。

已用真实导出器和浏览器测试三种不同业务标签、2/3/4 个查询字段及有无 Tabs 的组合，检查默认及项目 Logo 32px、侧栏 256px、顶部栏 64px、输入框 34px、面包屑与模块间距、四字段时操作换行、徽标、分页图标、斑马纹、行高和不同记录的操作数量。表格等间距检查测量生成时的列宽减去预检得到的各列内容最小宽度；这是机器布局检查，不代替视觉验收。测试不证明所有设计目标或响应式场景已实现。当前仍未完整支持含特殊资源的 SVG、已交付静态页面中数据变化后的自动重排、所有表格细节及复杂页面；遇到缺口不能复制过去页面的业务内容。

## 决策与来源

本次用户指令和原型明确的业务内容、状态及特殊布局优先；本规范作为默认设计。菜单名称、字段、数据、选项、业务状态、行操作从本次原型读取，不从本规范或历史页面复制。模块可以独立使用或组合；页面不需要的查询区、表格、Tabs、选择列等不要凭模板自动增加。用户要求完整 Tree，保存的 Tree 须包含全部节点、实例、行数据和来源绑定，不能仅保存模块引用或简写 Tree。

## 页面框架与侧栏

默认背景 `#f8f8f9`；有侧栏时宽 256px，白色背景至少铺满视口或内容高度，右侧柔和外阴影；Logo 与菜单属于同一侧栏，Logo 区高 64px，Logo 左侧 24px、整体高 32px 并按比例缩放。项目素材优先；未提供且页面需要 Logo 时使用 `assets/default-logo.svg`，不要重复添加其中已有的文字。一级与二级菜单行高 52px；一级左图标 16px、`#808695`，箭头 `#b5b5b5`。菜单项、图标、层级、展开与选中状态均由本次原型配置，不固定数量或展开项。

## 顶部导航与面包屑

顶部导航高 64px，有侧栏时从侧栏右边界开始，无侧栏时可占满页面宽度，下边缘使用柔和阴影。默认工具从左至右：收起、刷新；右侧大屏、全屏、消息、头像与名称；可根据项目要求配置。图标分别为 Remix `indent-decrease`（18px）、`reset-right-line`、`slideshow-line`、`fullscreen-line`、`notification-3-line`（后四项 16px），颜色 `#808695`；工具容器高 64px、左右 padding 12px，顶部栏两端无额外 padding。头像 24px，头像和名称间距 12px，组合容器高 64px、左右 padding 12px；头像和名称由当前项目配置，不能复制示例用户身份。

面包屑按当前层级配置文字，距侧栏右边及顶部栏下边各 12px；行高及容器高 20px，字重 400，父级 `#999999`，当前级 `#515a6e`，分隔符 `#dcdee2`。无侧栏或顶部栏时根据实际边界重新安排，不保留空白占位。

## 查询模块

默认左右距主区边界 24px；有面包屑与顶部栏时顶部距导航底部 44px。白色容器圆角 4px、padding 16px；默认四列等宽，标签水平排列并按最长七字宽度对齐。输入框和选择框高 34px、圆角 4px、边框 `#dcdee2`、提示文字 `#ccc`。查询与重置靠右，图标分别为 `search-line`、`refresh-line`，16px，与文字间距 6px；查询图标白色、重置图标 `#808695`。三字段可与操作同排、四列满时操作换行；小屏或内容不足时自然换行。字段类型、文案、是否有折叠与额外按钮由原型决定。

## 表格模块

默认与查询区相隔 16px，左右距主区边界各 24px；无查询区时按实际页面布局放置。Tabs 可选，显示数量时使用独立徽标：背景 `#f8f8f9`、1px 边框 `#dcdee2`、文字 `#515a6e`；Tab 高 37px，内容上下 padding 8px、左右 16px，文字与徽标间距 6px，Tab 之间 16px，底部有灰色通栏及选中蓝线。工具按钮间距 12px、顶部距模块 16px；灰线距表头 16px。当 Tab 与 32px 按钮顶部对齐时，按钮底部到表头为 21px，不能同时声称为 16px。

表头高 40px，数据行高 48px，内容白色与 `#f8f8f9` 交替。首列内容离表格左边 18px，操作内容离右边 18px，操作表头居中。列按内容所需宽度动态分配，剩余空间在相邻列之间均匀分配，内容过宽允许横向滚动。行操作可按需配置 Remix 图标与名称（示例查看 `eye-line`、编辑 `edit-box-line`、删除 `delete-bin-line`），图标 16px，相邻操作组间距 16px，避免内层多余 margin。默认分页第 1 页、10 条/页、10 页、Remix 箭头并垂直居中；100 条仅作为总数未知时的演示默认，原型或用户明确给出的分页优先。

## 复核与性能

按当前任务将模块一次配置并组合；一次预览后集中检查内容来源、菜单和业务状态、实际尺寸、背景、图标、阴影、列间距、分页与边界，问题合批修正并重看。每个页面重新校对其原型，不复用其他页面的业务内容或视觉 PASS。记录真实的准备、编写、生成、复核和发布用时；未测得的部分不猜测，五分钟是目标而非保证。不同字段数量、有无 Tabs、不同菜单与不同行操作的配置须实际测试，检查长内容、窄屏和空值，不能只验证文字或模板结构。
