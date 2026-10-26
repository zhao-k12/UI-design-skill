import { createApp, h, ref, nextTick } from 'vue';
import { Layout, Sider, Content, Menu, MenuItem, Card, Button, Input, Table, Icon, Avatar } from 'view-ui-plus';

const ir = JSON.parse(document.getElementById('design-ir').textContent);
if (ir.schemaVersion !== 'html-role-v1.0' || ir.registryVersion !== 'html-role-v1.0') throw new Error('unsupported_ui_ir');
const c = ir.content, p = ir.componentPlan;
const stage = ref('skeleton');
const tableWidth = ref(0);
const copy = (value, fallback) => stage.value === 'delivery' ? value : fallback;
const iconClass = name => `remix-custom remix-${name}`;
const icon = name => h(Icon, { custom: iconClass(name), 'data-icon': name });
const button = (item, props = {}, fallback = '操作') => h(Button,
  { ...props, ...(item.icon ? { customIcon: iconClass(item.icon) } : {}), 'data-action': item.label },
  item.label ? () => copy(item.label, fallback) : undefined);
const brand = () => h(Menu, { ...p.brand, activeName: '_none', 'data-region': 'brand' }, () =>
  h(MenuItem, { name: 'brand' }, () => h('span', { class: 'brand-identity' }, [
    h(Avatar, { shape: 'square', size: 'large', customIcon: iconClass(c.brand.icon) }),
    h('strong', copy(c.brand.label, '系统名称'))
  ])));
const sidebar = () => h(Sider, { class: 'role-side' }, () => h('div', { class: 'side-flow' }, [
  brand(),
  h(Menu, { theme: p.sidebar.theme, width: 'auto', activeName: p.sidebar.activeName, 'data-region': 'sidebar' }, () =>
    c.sidebar.map(item => h(MenuItem, { name: item.key, 'data-menu': item.key }, () =>
      [icon(item.icon), copy(item.label, '菜单项目')]))),
  h('div', { class: 'logout-zone' }, [h(Menu, { theme: p.sidebar.theme, width: 'auto', activeName: '_none' }, () =>
    h(MenuItem, { name: 'logout', 'data-region': 'logout' }, () => [icon(c.logout.icon), copy(c.logout.label, '退出')]))])
]));
const header = () => h(Menu, { ...p.header, activeName: '_none', 'data-region': 'header' }, () => [
  h(MenuItem, { name: 'page' }, () => [icon(c.heading.icon), copy(c.heading.label, '页面标题')]),
  h('div', { class: 'header-actions' }, c.headerActions.map(item =>
    button(item, { type: 'text', 'aria-label': item.accessibleLabel })))
]);
const toolbar = () => h('div', { class: 'role-toolbar', 'data-region': 'toolbar' }, [
  h('div', { class: 'toolbar-left' }, [
    button(c.create, { type: 'primary' }, '新增'),
    h('div', { class: 'search-field' }, [h(Input, { ...p.search, placeholder: copy(c.search, '搜索内容'), 'data-region': 'search' })]),
    button(c.help, { type: 'text' }, '帮助')
  ]),
  h('div', { class: 'toolbar-right' }, c.sortActions.map(item => button(item, {}, '排序')))
]);
const rowActions = row => h('div', { class: 'role-row-actions' }, row.actions.map(item =>
  button(item, { ...p.rowActions }, '操作')));
const table = () => {
  const columns = c.columns.map(col => ({ title: copy(col.title, '列标题'), key: col.key,
    ...(tableWidth.value ? { width: Math.floor(tableWidth.value * col.span / 24) } : {}),
    ...(col.key === 'actions' ? { render: (_, { row }) => rowActions(row) } : {}),
    ...(['name', 'memberCount'].includes(col.key) ? {
      render: (_, { row }) => h('a', { 'data-link-cell': col.key }, row[col.key])
    } : {})
  }));
  const data = c.rows.map(row => ({ ...row, name: copy(row.name, '职务名称'),
    memberCount: copy(row.memberCount, '0'), description: copy(row.description, '职务描述'),
    updatedAt: copy(row.updatedAt, '更新时间') }));
  return h(Table, { ...p.table, columns, data, 'data-region': 'table' });
};
const rendered = () => h(Layout, { class: 'role-layout', key: 'page' }, () => [sidebar(),
  h(Layout, null, () => [header(), h(Content, { class: 'role-main' }, () =>
    h(Card, { disHover: true, 'data-region': 'card' }, () => [toolbar(), table()]))])
]);
const block = (label, region, tone) => h('div', { class: `skeleton-cell sk-${tone}`, 'data-region': region }, label);
const skeleton = () => h(Layout, { class: 'role-layout', key: 'skeleton' }, () => [
  h(Sider, { class: 'role-side' }, () => h('div', { class: 'side-flow' }, [
    block('Menu · 齿轮＋系统名', 'brand', 'brand'),
    block('MenuItem ×11 · 每项左图标；职务权限固定选中；原图无展开箭头', 'sidebar', 'nav'),
    block('MenuItem · 电源图标 + 安全退出', 'logout', 'nav')
  ])),
  h(Layout, null, () => [block('Menu 横向 · 职务权限 + 人员权限图标；右侧返回 / 刷新', 'header', 'header'),
    h(Content, { class: 'role-main' }, () => [
      block('Card / 工具栏 · Button 新增职务 + 图标后缀 Input + 帮助；右对齐排序 Button ×2', 'toolbar', 'toolbar'),
      block('Table · 5 列 / 15 行 / 24 栅格自适应占满容器；名称和人数为链接；每行 6 个带图标操作', 'table', 'table')
    ])])
]);
createApp({ render: () => stage.value === 'skeleton' ? skeleton() : rendered() }).mount('#app');
window.__setStage = async value => {
  stage.value = value;
  await nextTick();
  if (value !== 'skeleton') {
    const body = document.querySelector('[data-region="card"] .ivu-card-body');
    const style = getComputedStyle(body);
    tableWidth.value = body.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    await nextTick();
  }
  await document.fonts.ready;
};
await nextTick();
window.__ready = true;
