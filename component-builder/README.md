# Official Component Runtime Extractor

TASK-006 从真实运行结果提取 Component IR，不根据文档复刻组件。当前覆盖 Button(primary/default size)、Input(default size)、Select(default size/closed/selected) 三个样例。默认尺寸的逻辑 ID 使用 medium，实际官方 Props 为 size=default，均记录在产物中。

官方来源为 [ViewUIPlus 仓库](https://github.com/view-design/ViewUIPlus) 的 npm 发布包 [view-ui-plus 1.3.24](https://www.npmjs.com/package/view-ui-plus)。对应源码提交为 23a8e5bd2c07143bebfbcadcfb30d6f5bd47834b。不复用或修改工作区其他项目的副本。

## 运行与版本锁

需要 Node.js 24+、npm，以及 Python 校验环境。package.json 固定 View UI Plus、Vue、Playwright、esbuild 版本；package-lock.json 固定全部传递依赖。首次准备：

```powershell
npm ci --no-audit --no-fund
npx playwright install chromium
```

source-reader/source-lock.json 已提交，包含官方 registry URL、发布包 SRI、Git Commit 以及 743 个项目锁文件/官方源码、类型、运行包、CSS、字体及 Vue 文件的 SHA-256。npm 负责发布包完整性校验，提取器再校验本地文件快照。提取前后均校验锁，文件变化立即失败，不自动升级。Git 属性将 JSON/JS/MJS 固定为 LF，避免 Windows checkout 换行转换造成哈希漂移。

`npm run lock:source` 只用于创建首份锁；已有锁时拒绝覆盖。以后更改 npm 依赖或官方源码，需要在新任务/明确 Migration 中记录新的快照，不得悄悄重建旧任务版本。版本锁针对本提取器源码输入，完整设计任务 manifest 属于 TASK-017。

```powershell
npm run extract
.\.venv\Scripts\python.exe -X utf8 -m validators.component_ir artifacts/task-006
npm run test:runtime
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

命令会启动仅监听 127.0.0.1 的临时服务，使用 Playwright 配套的 Chromium，然后关闭浏览器及服务；运行不依赖在线 CDN。浏览器请求限定为本地资源，官方 CSS 及字体以原字节提供。容器只提供布局宽度、间距与外部 padding，不修改组件内部 CSS。Props 不允许 style/class/HTML/event overrides，且传入字段必须属于组件实际解析后的 Props。

## 模块职责

| 模块 | 工作 |
| --- | --- |
| source-reader/ | 锁定官方发布元数据、源码/CSS/字体与依赖文件；拒绝静默变更 |
| runtime-renderer/ | 使用 Vue 和官方命名组件在真实 Chromium 中渲染声明的 Props；等待挂载、字体与稳定帧 |
| style-extractor/ | 调用 getComputedStyle、getBoundingClientRect、Text Range 获取真实 DOM、尺寸、样式、文字和伪元素 |
| component-ir/ | 仅组装观察到的数据和来源证据，不推断视觉值 |
| schemas/component-ir.schema.json | Component IR 的数据契约 |
| validators/component_ir.py | 数据契约、DOM 关联、运行产物和截图哈希检查 |

使用的浏览器接口见 [Playwright Page API](https://playwright.dev/docs/api/class-page) 和 [getComputedStyle](https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle)。

## 产物

输出目录默认为 artifacts/task-006：

- component_ir.json：3 类样例的 Props、实际默认 Props、DOM 树、节点相对坐标、Computed Style、padding/gap/border/radius/color/typography/alignment、文字范围、伪元素和图标盒度量。
- runtime_manifest.json：完整来源锁、CSS/运行包/Fixture/提取代码及 Bundle 哈希，真实浏览器版本及可执行文件哈希，OS、Node、Viewport/DPR/Locale、已加载资源哈希。
- 每个逻辑组件的 PNG，以及 official-runtime-gallery.png：浏览器原始截图。
- extraction_report.json：提取状态、IR/Manifest 文件哈希和 fidelityGate=NOT_RUN。
- component_ir_qa_report.json：独立 IR/证据检查结果。

坐标以组件根节点为原点；CSS 的 normal/auto 等值保持原样，不猜造转换值。隐藏子树也保留，并标记 visible；伪元素保存真实计算样式，图标盒尺寸来自浏览器元素框。Icon 字体属于官方运行组件的观察数据，尚未同步/登记为 Remix Icon 组件。

当前 Input/Select 的 240 宽度来自声明的外部容器，不能称为组件唯一固有宽度。中文字体使用当前环境中的 CSS 字体栈，Computed Family 记录声明栈，未识别每个字形最终使用的系统字体文件。测量和截图绑定该环境；跨 OS 或字体变化可能产生差异，不声称跨环境像素恒定。

提取中发生错误时，报告为 FAIL，旧 component_ir.json 被替换为 FAIL/空组件，不能沿用过期成功结果。测试使用临时目录，重复运行检查完整 IR 及截图哈希；Python 的小型 Schema fixture 只用于契约负面测试，不输出为运行证据。

## 验收边界

TASK-006 的 PASS 表示官方组件已真实运行并提取了参数，且运行产物自洽；不认证任意外来报告来源，也不比较原生设计组件与官方视觉。未运行 Fidelity Gate、未创建平台组件、未修改生产 Catalog 的 planned 状态。TASK-007 需要实际候选设计数据后进行几何与截图保真检查；不能把此提取报告当作保真 PASS。
