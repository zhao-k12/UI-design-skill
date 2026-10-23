# TASK-140 商品类型原型 → HTML

## 已完成的页面与证据

- 原型：`artifacts/task-140/product-types/prototype.png`，SHA-256 为 `478df474bfc1bce0ce4f02412f6d16fa5c7ca1a3b4a20e595954bf5c594023e7`。
- 可离线打开的单页：`artifacts/task-140/product-types/page.html`。同页有彩色骨架、默认文案组件、原型内容交付三个状态，默认显示交付状态。
- 初读、独立复扫与逐项视觉记录：`source-observations.json`、`independent-scan.json`、`visual-review.json`。64 项覆盖顶栏、11 个一级菜单及其箭头、2 个子菜单、筛选、6 列、11 个可见行及每行的状态和图标操作。
- View UI Plus 1.3.24 官方组件运行：Layout、Menu/Submenu、Breadcrumb、RadioGroup、DatePicker、Input、Card、Tree Table、Badge、Button、Avatar、Dropdown、Divider。功能图标从锁定的 Remix Icon Registry 读取。页面布局 CSS 不使用 `.ivu-*` 外观覆盖。
- `qa.json` 中骨架、默认组件和交付浏览器检查均 PASS；`source-visual-qa.json` 中双次来源扫描和三张截图字节绑定复核 PASS。浏览器检查另外覆盖 11 个菜单箭头、11 个状态圆点、8 个子级右箭头、33 个行操作图标及主内容与侧栏的横向关系。修复了从骨架切换后主内容落到侧栏下方的问题。

## 官方化改编和素材边界

原图的蓝色品牌图形及真人头像未提供单独源资产；页面使用官方 Avatar 与已锁定的 Remix 图标作为占位，不声称图案一致。原图侧栏为浅色；页面选用官方 Sider 与深色 Menu 组合，使侧栏全高背景连续。原图父级树节点是细向下箭头；官方 Table tree 使用原生展开方标，子级保留官方向右 Icon。原图“启用”文字也是绿色；官方 Badge success 保留绿色点和无框状态角色，文字由官方 CSS 决定。以上不以自写 CSS 模拟原型外观。

## ARCHITECTURE_CONFLICT：当前 HTML 预览尚未走完 Core/UI-IR

**当前设计**：`run_html_pipeline.py` 锁定 `registries/components/v0.2.9/catalog.json`。该目录有 Table、Button、DatePicker、Input 等类型，但无 Layout、Sider、Content、Menu、Submenu、MenuItem、Breadcrumb、Badge、Avatar、Dropdown、Divider；Table 的树形属性也未在本任务建立完整 Core 映射。

**原因与影响**：本次原型需要侧栏分组、通知徽标、头像及树表；不能删除这些可见内容来使旧组件目录通过。当前 `page.html` 是项目内的页面专用 View UI Plus 运行构建，保留来源 Tree、官方源码依据、逐项视觉 QA 和真实浏览器截图；它可供查看与评审，但不能宣称现有 Core、UI-IR、正式组件 Registry 和 HTML Adapter 全链路 PASS。页面级 `qa.json` 的 PASS 只覆盖本任务实际检查过的性质。

**建议的版本化迁移**：新增 HTML 官方运行组件目录与对应 Core/UI-IR 映射，逐项纳入上述缺口及 Tree Table 的 `tree`、`children`、`_showChildren` 属性。先对锁定版官方源码、CSS、DOM 和变体建来源/保真契约，再将本次独立观察与 Tree 经统一 Core、布局和 HTML Adapter 重跑；保留本次页面作为对照，不改写历史 Registry 或旧任务结果。该主链路迁移须依 `CONSTRAINTS.md` 第 16 条作明确架构决策后执行。
