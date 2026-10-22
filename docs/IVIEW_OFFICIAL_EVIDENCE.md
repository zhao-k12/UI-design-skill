# View UI Plus 官方依据清单

当前 HTML 路线锁定 `view-ui-plus@1.3.24`，官方源码快照见仓库 `node_modules/view-ui-plus`，来源版本与哈希见 `component-builder/source-reader` 和 `registries/design-standards/iview-plus-1.3.24.json`。上游项目为 [ViewUIPlus](https://github.com/view-design/ViewUIPlus)，组件文档入口为 [iView](https://www.iviewui.com)。本清单只列已核实的规则，不把原型截图或旧项目 CSS 当成规范。

| 范围 | 锁定版本依据 | 可采用的规则 |
| --- | --- | --- |
| 基础文字 | `src/styles/custom.less` 的 `@font-family`、`@font-size-base` | 官方字体栈；基础字号 14px。HTML 不再沿用历史平台默认字体改编。 |
| 色彩与边框 | 同文件的 `@primary-color`、`@text-color`、`@layout-body-background`、`@border-color-base`、`@border-color-split` | 使用官方 CSS 原值；不得按截图取色。 |
| 间距变量 | 同文件的 `@padding-lg/md/sm/xs` | 24/16/12/8px 是官方变量；具体区域能否使用某一变量仍须有组件或布局来源，不能见到变量就随意套用。 |
| 基础圆角、输入和按钮 | 同文件的 `@border-radius-base`、`@input-height-base`、`@btn-height-base`，以及 `src/styles/components/input.less`、`button.less` | 由官方组件 CSS 与公开属性决定外观；不为匹配原型另写字号、圆角、高度或内边距。 |
| 表格 | 同文件的 `@table-thead-bg`、`@table-td-stripe-bg`；`src/styles/components/table.less` | 表头与条纹背景、文字、单元格样式由官方 CSS 决定；表格占用容器可用宽度，不由截图中的空白决定。 |
| Layout / Grid | `src/styles/components/layout.less`、`grid.less` 及相应官方组件属性 | 优先用官方 Layout、Row、Col 表达区域和 24 栅格；不要把截图的侧栏、顶栏、间距像素伪称官方默认值。 |

每次新原型先列出实际用到的组件和页面区域，再逐项核实对应官方文档、源码、运行 CSS 与 API。清单没有覆盖到的组件或属性须补充证据后再标为“官方”；官方没有规定的整页模式、侧栏宽度、内容卡片形态等记为**规范未定义**，采用官方组件自然／自适应行为，不借视觉测量补数字。若布局需要项目自定义视觉规则，等用户另行提出特殊要求；当前不作为规范交付。

验收时记录：使用的官方组件与属性、源码或文档路径、骨架中对应区域、实际浏览器组件 DOM、是否存在本地 `.ivu-*` 覆盖、原型内容逐项校对。单纯检查官方组件类名存在，不足以证明页面符合规范。
