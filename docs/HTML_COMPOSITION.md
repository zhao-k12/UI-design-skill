# 内容 Tree → 官方组件组合

新页面使用 `core/pipeline/html_composition.py`、`adapters/html/composition.mjs` 和 `scripts/export_html_composition.mjs`。结构由Tree递归描述，执行器不识别“用户管理”“职务权限”等页面名称，不预设侧栏、顶栏、筛选区或表格。已有专用脚本仅用于恢复历史任务。

## 输入契约

`content-tree.json` 顶层为 `sourceSha256`、`title`、`root`，需要动态绑定图标时加 `icons` 列出来源支持的Remix名称。每个节点有稳定 `id`；业务内容用 `sourceIds` 绑定来源观察。共同重复结构可以关联多个来源编号，例外另设节点，不复制几十份组件规则。

| kind | 内容与用途 |
| --- | --- |
| `container` | `layout` 和 `children`；表达横纵排、对齐、留白、换行、Fill或24栅格占宽，不决定组件外观 |
| `component` | `component`为官方导出名；`props`为官方属性，`children`为默认槽，`slots`为命名槽；`icon`通过官方customIcon属性接入Remix |
| `text` | `value`为来源文字或绑定，`defaultValue`为组件审核态的占位文案 |
| `icon` | `name`为锁定Remix名称；放入组件官方允许的图标位置 |
| `repeat` | `items`数组或绑定及`template`；渲染菜单、选项、行操作等重复结构，不强制业务数量 |

绑定写为 `{"bind":"item.label"}`。repeat模板可读`item`与`index`；Table单元格可读`row`、`column`、`index`；嵌套repeat保留外层row。缺失绑定报具体路径，不静默删内容。

`container.layout`支持：`direction: horizontal|vertical`、`gap/padding: none|xs|sm|md|lg`、`justify: start|end|center|space-between`、`align: start|end|center|stretch`、`wrap`、`fill`、`span: 1..24`、`minHeight: viewport`。后者用于至少占满当前视口的外壳，不定义固定画布高度；与Fill子容器组合可把退出等区域推至底部。间距引用锁定版官方变量，但某区域采用哪个值仍需说明适用关系。组件本身的布局优先使用Row/Col、Space、Layout等官方属性。容器布局不能覆盖组件颜色、字号、边框等视觉。

导出器在Core目录和输出目录之后可传预览视口宽、高，例如`.../core .../html 1912 956`；仅决定浏览器截图视口，不向组件注入原型像素尺寸。省略时使用默认预览视口。

## 官方组件与Table

组件名来自锁定包 `src/components/index.js`，保存源码和导出索引哈希；不为新的组件组合维护页面专属准入表。官方组件存在就调用其实现；首次用到的属性和槽位核对相应官方源码，不能把“可导入”误称为所有组合已测试。

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

## 变更与验收

- 区域顺序、嵌套、菜单层级、工具栏、列数、行数、动作列表改变：只改Tree。
- 官方已有组件／属性／插槽但通用翻译未支持：补通用节点或组件能力，并用两种不同配置验证复用；不加按页面名分支。
- 官方确实无对应能力：记录特殊内容缺口和理由。未知业务内容或原图关键歧义按原有来源复核处理。

新入口保留一次浏览器会话的三态截图和静态快照，随后做原有的来源与视觉集中复核。生成器的运行PASS只说明渲染、基本结构和静态导出可用，不能替代本次原图的完整性和视觉校对。配置开发测试也不能冒充新的用户原型验收。
## 紧凑作者输入

通用执行器支持`use/p/text/from/stack`与任务内`definitions/ref`简写，先无损展开为本契约再编译；Core/UI-IR字段不变。完整行数据、状态及例外不得省略。用法见[快速入口](HTML_FAST_WORKFLOW.md#无损简写-tree)。
