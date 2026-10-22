import { createApp, h, nextTick, ref } from 'vue';
import { Button, Input, Select, DatePicker, Table, Breadcrumb, BreadcrumbItem, Badge } from 'view-ui-plus';

const payload = JSON.parse(document.getElementById('design-payload').textContent);
const source = payload.tree;
const stages = ['skeleton', 'component', 'delivery'];
const initial = location.hash.slice(1);
const current = ref(stages.includes(initial) ? initial : 'delivery');
const final = () => current.value === 'delivery';
const icon = (name, size = 18) => {
  const svg = payload.icons[`remix.${name}`];
  if (!svg) throw new Error(`missing_icon:remix.${name}`);
  return h('span', { class: 'remix-icon', style: { width: `${size}px`, height: `${size}px` },
    innerHTML: svg, 'aria-hidden': 'true' });
};
const sk = (name, kind, extra = '') => h('div', {
  class: `skeleton-block skeleton-${kind} ${extra}`, 'data-skeleton': name,
}, `${kind} · ${name}`);
const text = (value, placeholder = '文本') => final() ? value : placeholder;

const navIcons = [
  'home-4-line', 'file-list-3-line', 'user-3-line', 'inbox-archive-line',
  'bank-card-line', 'bar-chart-2-line', 'customer-service-2-line',
  'focus-2-line', 'mail-open-line', 'team-line', 'computer-line',
];
function sidebar() {
  return h('aside', { class: 'sidebar', 'data-region': 'navigation' }, [
    h('div', { class: 'brand' }, [h('div', { class: 'brand-icon' }, icon('focus-2-line', 32)),
      h('strong', text(source.brand, '品牌名称'))]),
    h('nav', { class: 'side-nav' }, source.navigation.map((item, index) =>
      h('div', { class: ['side-item', index === 2 && final() ? 'selected' : ''],
        'data-nav-index': index }, [icon(navIcons[index]), h('span', text(item, '导航项'))]))),
  ]);
}

function topbar() {
  return h('header', { class: 'topbar', 'data-region': 'topbar' }, [
    h('div', { class: 'sidebar-toggle' }, icon('menu-fold-line', 20)),
    h('div', { class: 'topbar-right' }, [
      h('div', { class: 'global-search' }, [
        h(Input, { placeholder: final() ? source.topbar.searchPlaceholder : '输入内容', readonly: true,
          style: { width: '200px' } }), icon('search-line', 16),
      ]),
      h('div', { class: 'topbar-item' }, [icon('volume-up-line'), h(Badge,
        { count: final() ? source.topbar.notificationCount : 0 },
        { default: () => text(source.topbar.notifications, '消息') })]),
      ...source.topbar.actions.map((action, index) => h('div', { class: 'topbar-item' }, [
        icon(index === 0 ? 'lock-line' : 'settings-3-line'), text(action, '操作'),
      ])),
      h('div', { class: 'topbar-item account' }, [icon('account-circle-line', 22),
        text(source.topbar.user, '用户'), icon('arrow-down-s-line', 14)]),
    ]),
  ]);
}

function breadcrumb() {
  return h('div', { class: 'breadcrumb-row', 'data-region': 'breadcrumb' }, [
    h(Breadcrumb, null, { default: () => source.breadcrumb.map((part, index) =>
      h(BreadcrumbItem, null, { default: () => [index === 0 ? icon('home-4-line', 15) : null,
        text(part, index === 2 ? '页面标题' : '导航')] })) }),
  ]);
}

function filterControl(filter, index) {
  const attrs = { class: 'filter-control', 'data-filter-index': index };
  const placeholder = final() ? filter.placeholder : (filter.type === 'input' ? '输入内容' : '请选择');
  if (filter.type === 'input') return h('div', attrs, h(Input, { placeholder, readonly: true }));
  if (filter.type === 'date') return h('div', attrs, h(DatePicker, {
    type: 'date', placeholder, editable: false, style: { width: '100%' },
  }));
  return h('div', attrs, h(Select, { placeholder, style: { width: '100%' } }));
}

const toolbarIcons = ['add-line', 'flag-line', 'file-add-line', 'repeat-line', 'download-2-line', 'upload-2-line'];
function filters() {
  return h('section', { class: 'filter-section', 'data-region': 'filters' }, [
    h('div', { class: 'filter-controls' }, source.filters.map(filterControl)),
    h('div', { class: 'filter-actions' }, [
      h(Button, { type: 'primary' }, { default: () => [icon('search-line', 15), text(source.filterActions[0], '按钮')] }),
      h(Button, null, { default: () => [icon('restart-line', 15), text(source.filterActions[1], '按钮')] }),
      h('span', { class: 'more-filters' }, [icon('filter-3-line', 15), text(source.filterActions[2], '更多')]),
    ]),
  ]);
}

function toolbar() {
  return h('div', { class: 'toolbar', 'data-region': 'actions' }, [
    h('div', { class: 'toolbar-primary' }, source.toolbarActions.map((action, index) =>
      h(Button, { type: index === 0 ? 'primary' : 'default', 'data-action-index': index },
        { default: () => [icon(toolbarIcons[index], 15), text(action, '按钮')] }))),
    h('div', { class: 'toolbar-utility' }, source.toolbarUtilities.map((action, index) =>
      h('span', { title: final() ? action : '工具', 'data-utility-index': index },
        icon(index === 0 ? 'refresh-line' : 'settings-3-line', 18)))),
  ]);
}

function statusCell() {
  return h('span', { class: 'status-cell' }, [h('i', { class: 'status-dot' }), source.table.repeatedRow.status]);
}
function actionCell() {
  const kinds = ['info', 'success', 'error'];
  const actionIcons = ['edit-2-line', 'checkbox-circle-line', 'delete-bin-line'];
  return h('div', { class: 'row-actions' }, source.table.repeatedRow.actions.map((label, index) =>
    h(Button, { size: 'small', type: kinds[index], ghost: true },
      { default: () => [icon(actionIcons[index], 12), label] })));
}
const tableColumns = [
  { type: 'selection', width: 54, align: 'center' },
  { title: source.table.columns[1], key: 'number', minWidth: 110, sortable: true },
  { title: source.table.columns[2], key: 'company', minWidth: 215, sortable: true },
  { title: source.table.columns[3], key: 'status', minWidth: 120, sortable: true,
    render: statusCell },
  { title: source.table.columns[4], key: 'industry', minWidth: 125, sortable: true },
  { title: source.table.columns[5], key: 'source', minWidth: 125, sortable: true },
  { title: source.table.columns[6], key: 'owner', minWidth: 110 },
  { title: source.table.columns[7], key: 'updated', minWidth: 180, sortable: true },
  { title: source.table.columns[8], key: 'actions', minWidth: 220, render: actionCell },
];
function table() {
  const rows = final() ? Array.from({ length: source.table.visibleRows }, (_, index) => ({
    ...source.table.repeatedRow, _rowKey: index,
  })) : [];
  return h('div', { class: 'table-wrap', 'data-region': 'table' },
    h(Table, { columns: tableColumns, data: rows, stripe: true, border: false,
      'row-key': '_rowKey', style: { width: '100%' } }));
}

function floating() {
  if (!final()) return null;
  return h('div', { class: 'floating-tools', 'data-region': 'floating' }, [
    h('div', { class: 'floating-demo' }, [icon('radio-button-line'), source.floating.demo]),
    h('div', { class: 'floating-shortcuts' }, source.floating.shortcuts.map((label, index) =>
      h('div', [icon(['add-circle-line', 'phone-line', 'chat-3-line'][index]), h('span', label)]))),
  ]);
}

function page() {
  return h('div', { class: 'design-page', 'data-stage': current.value }, [
    sidebar(), h('div', { class: 'main-column' }, [topbar(), breadcrumb(),
      h('main', { class: 'content-area' }, [h('article', { class: 'content-card' }, [
        h('div', { class: 'card-title' }, text(source.title, '页面标题')),
        h('div', { class: 'card-body' }, [filters(), toolbar(), table()]),
      ])]),
    ]), floating(),
  ]);
}

function skeleton() {
  return h('div', { class: 'design-page skeleton-page', 'data-stage': 'skeleton' }, [
    h('aside', { class: 'sidebar' }, [sk('品牌', 'brand'), ...source.navigation.map((_, i) => sk(`导航 ${i + 1}`, 'navigation'))]),
    h('div', { class: 'main-column' }, [
      h('header', { class: 'topbar' }, sk('顶栏搜索与操作', 'header')),
      h('div', { class: 'breadcrumb-row' }, sk('面包屑', 'breadcrumb')),
      h('main', { class: 'content-area' }, [h('article', { class: 'content-card' }, [
        h('div', { class: 'card-title' }, sk('客户管理标题', 'title')),
        h('div', { class: 'card-body' }, [
          h('div', { class: 'skeleton-filter-row' }, [
            ...source.filters.map((_, i) => sk(`筛选 ${i + 1}`, 'input')),
            ...source.filterActions.map((_, i) => sk(`筛选操作 ${i + 1}`, 'button')),
          ]),
          h('div', { class: 'skeleton-toolbar-row' }, source.toolbarActions.map((_, i) => sk(`操作 ${i + 1}`, 'action'))),
          sk('九列表格与十条记录', 'table'),
        ]),
      ])]),
    ]),
  ]);
}

const labels = { skeleton: '彩色骨架', component: '默认组件', delivery: '交付页面' };
createApp({ render: () => h('div', [
  h('nav', { class: 'stage-nav', 'aria-label': '页面阶段' }, stages.map(stage =>
    h('button', { type: 'button', class: current.value === stage ? 'active' : '',
      onClick: () => window.__setDesignStage(stage) }, labels[stage]))),
  current.value === 'skeleton' ? skeleton() : page(),
]) }).mount('#app');
window.__setDesignStage = async stage => {
  if (!stages.includes(stage)) throw new Error(`unknown_stage:${stage}`);
  current.value = stage;
  location.hash = stage;
  await nextTick();
  await document.fonts.ready;
};
await nextTick();
window.__designReady = true;
