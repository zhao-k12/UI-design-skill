# 内容 Tree → 官方组件组合

新页面使用 `core/pipeline/html_composition.py`、`adapters/html/composition.mjs` 和 `scripts/export_html_composition.mjs`。结构由Tree递归描述，执行器不识别“用户管理”“职务权限”等页面名称，不预设侧栏、顶栏、筛选区或表格。已有专用脚本仅用于恢复历史任务。

## 输入契约

`content-tree.json` 顶层为 `sourceSha256`、`title`、`root`，需要动态绑定图标时加 `icons` 列出来源支持的Remix名称。每个节点有稳定 `id`；业务内容用 `sourceIds` 绑定来源观察。共同重复结构可以关联多个来源编号，例外另设节点，不复制几十份组件规则。

容器或组件可以显式指定 `designRole` 选择已接入的共享样式，例如 `"designRole":"search-panel"`；角色清单、能力边界和验证范围见[已确认的页面模块](CONFIRMED_REUSABLE_MODULES.md#已接入的样式角色)。此属性不生成内容或省略完整 Tree；未实现的模块装配和样式不得标记已实现。

用户提供的默认 Logo 可用 `{"id":"logo","kind":"asset","name":"default-logo"}` 插入完整 Tree；仅用户明确要求其他 Logo 时，项目 Logo 使用 `project_logo` 构造已嵌入且经过编译器校验的资源节点。`TabPane.tabLabel` 可保存完整标签子树以显示数量徽标，必须具有显式节点 id，适配器通过官方标签渲染能力呈现。两者均不读取历史业务内容。

| kind | 内容与用途 |
| --- | --- |
| `container` | `layout` 和 `children`；表达横纵排、对齐、留白、换行、Fill或24栅格占宽，不决定组件外观 |
| `component` | `component`为官方导出名；`props`为官方属性，`children`为默认槽，`slots`为命名槽；`icon`通过官方customIcon属性接入Remix |
| `text` | `value`为来源文字或绑定，`defaultValue`为组件审核态的占位文案 |
| `icon` | `name`为锁定Remix名称；放入组件官方允许的图标位置 |
| `repeat` | `items`数组或绑定及`template`；渲染菜单、选项、行操作等重复结构，不强制业务数量 |

绑定写为 `{"bind":"item.label"}`。repeat模板可读`item`与`index`；Table单元格可读`row`、`column`、`index`；嵌套repeat保留外层row。缺失绑定报具体路径，不静默删内容。

`container.layout`支持：`direction: horizontal|vertical`、`gap/padding/paddingX/paddingY: none|xs|sm|md|lg`、`justify: start|end|center|space-between`、`align: start|end|center|stretch`、`wrap`、`fill`、`span: 1..24`、`minHeight: viewport`。其中 `paddingX` 和 `paddingY` 分别覆盖横向和纵向的 `padding`；未指定方向沿用 `padding`，都未指定则为零。`minHeight` 用于至少占满当前视口的外壳，不定义固定画布高度；与Fill子容器组合可把退出等区域推至底部。间距引用锁定版官方变量，但某区域采用哪个值仍需说明适用关系。组件本身的布局优先使用Row/Col、Space、Layout等官方属性。容器布局不能覆盖组件颜色、字号、边框等视觉。

跨模块快捷导航需要浅色顶栏、选中项可辨且不采用页内Tabs式下划线时，可用 `semantic: "navigation"` 的容器包裹官方 `Link`；容器可设置非空 `ariaLabel`。当前项的 Link 设置 `current: true` 和官方 `strong: true`，其他项可使用官方 `type: "secondary"`；运行时输出 `nav` 和 `aria-current="page"`，静态快照保留这两项语义且不执行跳转。水平间距通过容器中已核实的间距 token 配置，不覆盖官方组件样式。这个组合仅用于无须下拉菜单的平级入口；多级、下拉和其他导航应依据原型另选官方组合。当前选项的显示必须对截图复核，不能仅凭 aria 元数据认定视觉通过。

导出器在Core目录和输出目录之后可传预览视口宽、高，例如`.../core .../html 1912 956`；仅决定浏览器截图视口，不向组件注入原型像素尺寸。省略时使用默认预览视口。

## 官方组件与Table

组件名来自锁定包 `src/components/index.js`，保存源码和导出索引哈希；不为新的组件组合维护页面专属准入表。官方组件存在就调用其实现；首次用到的属性和槽位核对相应官方源码，不能把“可导入”误称为所有组合已测试。

## 图标与查询操作

普通查询模块默认顺序为“查询、重置、收起/展开”：查询用官方主按钮，重置用官方默认按钮；只有存在筛选区域折叠时，才在末尾提供当前状态对应的“收起”上箭头或“展开”下箭头。本次明确要求优先；原型省略重置时可按该项目默认补充，折叠能力不能凭空增加。静态交付只呈现当前状态，不实现动作。

主动配置的图标统一选 Remix Icon，并核对锁定图标库名称、方向和语义。对于支持 `customIcon` 的官方Button、Avatar等，通过Tree顶层节点的 `icon` 字段传入 Remix 名称；独立图标使用 `kind: icon`。不要在组件 `props.icon` 或 `Icon.props.type` 填写 `ios-*` 等内置图标。组件没有自定义图标属性时，先核实其官方插槽，再用独立图标节点组合；未开放替换的组件内部默认指示图形保留官方组件并如实记录，不用CSS覆盖，不声称它已换成Remix。用户单独指定的品牌或头像素材按其要求处理；截图中可见图形不等于单独提供素材，非关键且没有精确还原要求时可采用合理替代并记录取舍。

例如以下两个实际锁定库名称分别表达按钮左侧图标与独立图标；`icon` 是节点字段，不是 `props.icon`：

```json
[
  {"id":"query","kind":"component","component":"Button","props":{"type":"primary"},"icon":"search-line","children":[{"id":"query-text","kind":"text","value":"查询"}]},
  {"id":"collapse-icon","kind":"icon","name":"arrow-up-s-line"}
]
```

将图标与查询操作顺序合并到既有Tree和一次综合复核：对照原图和Tree检查位置、含义、方向及固定状态，并在交付DOM/源码清单核对主动配置的图标来源。不要把运行PASS或图标占位当作来源验证，也不新增单独审核轮次。

先按[官方区域组合参考](IVIEW_COMPOSITION_PATTERNS.md)选择容器职责及宽度策略，再确定组件、变体和插槽。查询工具条可在Card正文中独立排列；详情分区可用Card head，不按“右侧=extra”映射。状态按展示用途及填充/描边/圆点特征选Tag、Badge或文字；普通描述不自动变成禁用表单。完整Tree保存本次区域和数据，不从官方例页导入业务默认值。在线Admin Plus专用布局仅作参考，未取得源码不作为本地官方组件调用。

遵循[项目默认主题与表单](IVIEW_COMPOSITION_PATTERNS.md#项目默认主题与表单)：不以Header/Sider默认值或适配便利决定双深色；先确定整页主题，再用已核实能力覆盖正确容器。桌面Form默认左右标签关系，项的横纵排列由Row/Col或inline独立表达，不默认top；例外理由写入现有证据。不得借新默认政策覆盖官方视觉CSS。

Table直接配置官方`props.columns`、`props.data`、`stripe`、`border`、树字段等。列数、选中列、树列、行数、状态变体与操作均由本次原型决定。需要自定义单元格时给该列增加声明式`cell`子Tree，由Adapter转换为官方`render`接口；不在JSON中放函数或页面业务代码。例如：

```json
{
  "title": "操作",
  "key": "actions",
  "cell": {
    "id": "actions", "kind": "repeat", "items": {"bind": "row.actions"},
    "template": {
      "id": "action", "kind": "component", "component": "Button",
      "props": {"type": "text", "size": "small"},
      "icon": {"bind": "item.icon"},
      "children": [{"id": "action-label", "kind": "text", "value": {"bind": "item.label"}, "defaultValue": "操作"}]
    }
  }
}
```

组件审核态沿用同一结构与固定选中外观，文字用`defaultValue`，placeholder等内容属性通过`defaultProps`给默认文案；不要把颜色、类型、树结构或状态变体改成另一种。交付态注入来源文案。无自定义cell的Table列在组件态统一占位，原始行形状和变体数据不修改。

编写Tree时一并决定整页层级、比例与密度，不能以每个组件默认尺寸代替设计。普通记录列表按用户批准的[10条政策](PROTOTYPE_OBSERVATION_QA.md#列表条数空值与裁切)配置完整`props.data`：不足补演示记录并内部注明，超过仅保留前10条，已有空值保留；汇总行和分类/采样数据另判。右下方使用官方Page：默认第1页、10条/页、10页及每页条数选择，未知真实总数时100仅为演示配置并内部标注；数量不是Adapter硬编码，只交付静态页面。

## 变更与验收

- 区域顺序、嵌套、菜单层级、工具栏、列数、行数、动作列表改变：只改Tree。
- 官方已有组件／属性／插槽但通用翻译未支持：补通用节点或组件能力，并用两种不同配置验证复用；不加按页面名分支。
- 官方确实无对应能力：记录特殊内容缺口和理由。未知业务内容或原图关键歧义按原有来源复核处理。

新入口保留一次浏览器会话的三态截图和静态快照，随后做原有的来源与视觉集中复核。生成器的运行PASS只说明渲染、基本结构和静态导出可用，不能替代本次原图的完整性和视觉校对。配置开发测试也不能冒充新的用户原型验收。
## 完整作者输入

通用执行器仅接受完整节点字段和显式编号，不再支持键名简写、`definitions/ref`或`$repeat`行数据简写；Core/UI-IR契约不变。实际行数据逐条列出，父子归属明确表达。用法见[快速入口](HTML_FAST_WORKFLOW.md#完整-tree)。
