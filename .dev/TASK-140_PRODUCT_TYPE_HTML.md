# TASK-140 商品类型原型 → HTML

## 已完成的页面与证据

- 原型：`artifacts/task-140/product-types/prototype.png`，SHA-256 为 `478df474bfc1bce0ce4f02412f6d16fa5c7ca1a3b4a20e595954bf5c594023e7`。
- 可离线打开的单页：`artifacts/task-140/product-types/page.html`。TASK-141 后已转为静态交付快照；彩色骨架和默认组件仅留作内部截图证据。
- 初读、独立复扫与逐项视觉记录：`source-observations.json`、`independent-scan.json`、`visual-review.json`。64 项覆盖顶栏、11 个一级菜单及其箭头、2 个子菜单、筛选、6 列、11 个可见行及每行的状态和图标操作。
- View UI Plus 1.3.24 官方组件运行：Layout、Menu/Submenu、Breadcrumb、RadioGroup、DatePicker、Input、Card、Tree Table、Badge、Button、Avatar、Dropdown、Divider。功能图标从锁定的 Remix Icon Registry 读取。页面布局 CSS 不使用 `.ivu-*` 外观覆盖。
- `qa.json` 中骨架、默认组件和交付浏览器检查均 PASS；`source-visual-qa.json` 中双次来源扫描和三张截图字节绑定复核 PASS。浏览器检查另外覆盖 11 个菜单箭头、11 个状态圆点、8 个子级右箭头、33 个行操作图标及主内容与侧栏的横向关系。修复了从骨架切换后主内容落到侧栏下方的问题。

## 官方化改编和素材边界

原图的蓝色品牌图形及真人头像未提供单独源资产；页面使用官方 Avatar 与已锁定的 Remix 图标作为占位，不声称图案一致。原图侧栏为浅色；页面选用官方 Sider 与深色 Menu 组合，使侧栏全高背景连续。原图父级树节点是细向下箭头；官方 Table tree 使用原生展开方标，子级保留官方向右 Icon。原图“启用”文字也是绿色；官方 Badge success 保留绿色点和无框状态角色，文字由官方 CSS 决定。以上不以自写 CSS 模拟原型外观。

## 版本化迁移决定与验收

`run_html_pipeline.py` 的旧 Profile 锁定 `registries/components/v0.2.9/catalog.json`。该目录缺少本原型需要的 Layout、Sider、Content、Menu、Submenu、MenuItem、Breadcrumb、Badge、Avatar、Dropdown、Divider 等角色。用户已批准按本任务方案版本化接入并重跑，旧目录和历史输出保持原样。

新增 `registries/components/html-v1/catalog.json`、`core/pipeline/html_page_v1.py` 与 `adapters/html/page-v1.mjs`。新 Profile 将 64 项观察中的 63 个纳入项逐一映射到独立的 Page Tree、布局 Tree、组件角色及 UI-IR；排除的浏览器滚动条保留理由。Core 校验来源哈希、两次扫描、11 个菜单箭头、11 个状态面型和 11 行操作、6 列表头及官方源码存在性。HTML Adapter 从生成的 UI-IR 读取 Menu、筛选、状态和树表变体与实际内容，不从原型模板直接决定组件；锁定官方运行包 1.3.24。旧 Profile 和历史结果不变。

本次 Core `core-v1-r4/qa_report.json` 为 PASS：64 项来源观察、63 项纳入映射、11 行、24 栅格元数据；`ui_ir.json` 的哈希写入页面元数据和 `qa.json`。HTML 三状态结构浏览器 QA PASS；五项 Core 回归覆盖正常编译、漏项、菜单箭头、状态面型和独立复扫漂移。TASK-141 用户指出的图文间距、树符间距、右侧按钮与分隔线位置、标题强调线角色四处问题不属于旧 QA 覆盖范围，**不能把旧 PASS 当作新组合视觉验收**；此页面未修正四处视觉问题。当前版本只处理静态后台树形列表这一页面模式，不声称已覆盖任意原型或完整交互。品牌原始图像仍缺失，使用官方 Avatar 和已登记图标占位。
