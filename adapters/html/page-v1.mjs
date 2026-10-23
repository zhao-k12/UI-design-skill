import { createApp, h, nextTick, ref } from 'vue';
import {
  Layout, Sider, Content, Menu, MenuItem, Submenu, Breadcrumb, BreadcrumbItem,
  Input, DatePicker, Button, Table, Badge, Card, Avatar, Dropdown,
  DropdownMenu, RadioGroup, Radio, Divider, Icon
} from 'view-ui-plus';

const ir = JSON.parse(document.getElementById('design-ir').textContent);
if (ir.schemaVersion !== 'html-v1.0' || ir.registryVersion !== 'html-v1.0') throw new Error('unsupported_ui_ir');
const source = ir.content;
const plan = ir.componentPlan;
const iconAssets = JSON.parse(document.getElementById('icon-assets').textContent);
const stage = ref(['skeleton', 'component', 'delivery'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'delivery');
const actual = () => stage.value === 'delivery';
const copy = (value, fallback) => actual() ? value : fallback;
const icon = name => iconAssets[name]
  ? h('span', { class: 'remix-icon', innerHTML: iconAssets[name], 'aria-hidden': 'true', 'data-icon': name })
  : null;

const navTitle = entry => h('span', { class: 'nav-title' }, [icon(entry.icon), copy(entry.label, '导航分组')]);
const header = () => h(Menu, { mode: plan.header.mode, theme: plan.header.theme, activeName: 'none', 'data-region': 'header' }, () =>
  h('div', { class: 'top-inner' }, [
    h('div', { class: 'brand', 'data-observation': 'brand' }, [
      h(Avatar, { size: 'large', shape: 'circle' }, () => icon('store-2-line')),
      h('strong', copy(source.brand, '系统名称'))
    ]),
    h('div', { class: 'top-actions' }, [
      h(Badge, { count: actual() ? source.messageCount : 0, 'data-observation': 'message-badge' }, () =>
        h(Button, { type: 'text', 'data-observation': 'message' }, () => [icon('notification-3-line'), copy(source.message, '消息')])),
      h(Dropdown, { trigger: 'custom', 'data-observation': 'account' }, {
        default: () => h(Button, { type: 'text' }, () => [h(Avatar, { shape: 'circle', icon: 'ios-person' }), copy(source.account, '账号')]),
        list: () => h(DropdownMenu)
      })
    ])
  ]));

const sidebar = () => h(Sider, { class: 'side' }, () =>
  h(Menu, { theme: plan.sidebar.theme, width: 'auto', activeName: plan.sidebar.activeName, openNames: plan.sidebar.openNames, 'data-region': 'sidebar' }, () =>
    source.sidebar.map(entry => h(Submenu, { name: entry.key, 'data-menu-key': entry.key }, {
      title: () => navTitle(entry),
      default: () => (entry.children || []).map(child => h(MenuItem, { name: child.key }, () => copy(child.label, '子菜单')))
    }))));

const heading = () => h('div', { class: 'page-head' }, [
  h(Breadcrumb, null, () => source.breadcrumb.map((label, index) =>
    h(BreadcrumbItem, null, () => [index === 0 ? icon('home-4-line') : null, copy(label, '导航')]))),
  h('div', { class: 'page-actions' }, source.pageActions.map((action, index) =>
    h(Button, { type: plan.pageActions[index].type, 'data-page-action': action.label },
      () => [icon(action.icon), copy(action.label, '操作')]))),
]);

const filters = () => h(Card, { disHover: true, 'data-region': 'filters' }, () =>
  h('div', { class: 'filter-row' }, [
    h(RadioGroup, { modelValue: source.tabs[0], type: plan.tabs.type, buttonStyle: plan.tabs.buttonStyle, 'data-observation': 'status-tabs' }, () =>
      source.tabs.map((tab, index) => h(Radio, { label: tab }, () => copy(tab, `状态${index + 1}`)))),
    h('div', { class: 'filter-fields' }, [
      h(DatePicker, { type: plan.date.type, placeholder: copy(source.filters[0], '选择日期'), editable: false,
        'data-observation': 'updated-date' }),
      h(Input, { placeholder: copy(source.filters[1], '搜索内容'), search: plan.search.search, readonly: true,
        'data-observation': 'type-search' })
    ])
  ]));

const actionIcons = plan.rowActions.icons;
const rowActions = row => h('div', { class: 'row-actions' }, row.actions.map(label =>
  h(Button, { type: plan.rowActions.type, size: plan.rowActions.size, 'data-row-action': label }, () => [icon(actionIcons[label]), copy(label, '操作')])));
const rowStatus = row => h(Badge, { status: plan.status.status, text: copy(row.status, '状态'), 'data-status': row.key });
const rowData = rows => rows.map(row => ({
  ...row, name: copy(row.name, '分类名称'), status: copy(row.status, '状态'),
  creator: copy(row.creator, '创建人'), note: copy(row.note, '备注'),
  updatedAt: copy(row.updatedAt, '更新时间'),
  children: row.children ? rowData(row.children) : undefined
}));
const columnDefinitions = [
  { type: 'selection', width: 54, align: 'center' },
  ...plan.table.columns.map(column => ({
    title: copy(column.title, column.title), key: column.key, minWidth: column.minWidth,
    ...(column.key === plan.table.treeColumn ? {
      tree: true,
      render: (_, { row }) => h('span', [!row.children ? h(Icon, { type: 'ios-arrow-forward', 'data-tree-leaf': row.key }) : null, row.name])
    } : {}),
    ...(column.key === 'status' ? { render: (_, { row }) => rowStatus(row) } : {}),
    ...(column.key === 'actions' ? { render: (_, { row }) => rowActions(row) } : {})
  }))
];
const list = () => h(Card, { disHover: true, 'data-region': 'list' }, {
  title: () => h('div', { class: 'list-heading' }, [h(Divider, { type: 'vertical' }), copy(source.listTitle, '列表标题')]),
  extra: () => h(Button, { 'data-observation': 'expand-collapse' }, () => [icon('refresh-line'), copy(source.expandLabel, '展开/折叠')]),
  default: () => h(Table, { columns: columnDefinitions, data: rowData(source.rows), stripe: plan.table.stripe, rowKey: plan.table.rowKey })
});
const page = () => h(Layout, { class: 'app-layout', key: 'rendered-page' }, () => [
  header(), h(Layout, null, () => [sidebar(), h(Content, { class: 'main-content' }, () => [heading(), filters(), list()])])
]);

const block = (label, region, tone) => h('div', { class: `skeleton-cell skeleton-${tone}`, 'data-region': region }, label);
const skeleton = () => h(Layout, { class: 'app-layout', key: 'skeleton-page' }, () => [
  block('Menu 横向 · Avatar 品牌 / Badge 消息 / Avatar 账号', 'header', 'header'),
  h(Layout, null, () => [
    h('div', { class: 'skeleton-side' }, block('Menu 纵向 · 11 个带箭头的一级分组 / 商品管理已展开 / 商品类型选中', 'sidebar', 'side')),
    h(Content, { class: 'main-content skeleton-main' }, () => [
      block('Breadcrumb · 系统首页 / 商品管理 / 商品类型　　Button ×3', 'heading', 'heading'),
      block('RadioGroup · 全部类型 / 启用中 / 已停用　　DatePicker / 带搜索后缀的 Input', 'filters', 'filters'),
      block('Card + Tree Table · 分类层级 / Badge 状态圆点 / 行内操作', 'list', 'list')
    ])
  ])
]);

createApp({ render: () => h('div', [stage.value === 'skeleton' ? skeleton() : page(),
  h('div', { class: 'demo-switch' }, ['skeleton', 'component', 'delivery'].map((name, index) =>
    h(Button, { type: stage.value === name ? 'primary' : 'default', onClick: () => window.__setStage(name) },
      () => ['彩色骨架', '默认组件', '交付页面'][index])))
]) }).mount('#app');
window.__setStage = async name => { stage.value = name; location.hash = name; await nextTick(); await document.fonts.ready; };
await nextTick(); window.__ready = true;
