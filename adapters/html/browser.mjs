import { createApp, h, nextTick, ref } from 'vue';
import {
  Button, Input, Select, Option, Table, Tag, Checkbox, Radio, Switch,
  Card, Page, Tabs, TabPane, Tree, DatePicker, Form, FormItem,
  Modal, Drawer, Upload, Cascader,
} from 'view-ui-plus';

const payload = JSON.parse(document.getElementById('design-payload').textContent);
const stages = ['skeleton', 'component', 'delivery'];
const initialStage = location.hash.slice(1);
const currentStage = ref(stages.includes(initialStage) ? initialStage : 'delivery');
const token = name => {
  const entry = payload.tokens[name];
  if (!entry) throw new Error(`unknown_token:${name}`);
  const value = entry.value;
  return value && typeof value === 'object' && value.token ? token(value.token) : value;
};
const length = value => value == null ? undefined : `${Number(value)}px`;
const measure = value => value?.mode === 'fixed' ? length(value.value) : undefined;
const textOf = value => typeof value === 'string' ? value : value?.text ?? '';
const content = node => payload.content[node.sourceIds?.[0]] ?? {};
const scope = node => payload.catalog[node.componentId]?.contentScope ?? {};
const scopedProps = scopeValue => scopeValue.props && typeof scopeValue.props === 'object' ? scopeValue.props : scopeValue;
const getText = (node, field, fallback = '') => textOf(content(node).props?.[field]) || fallback;

function boxStyle(node) {
  const layout = node.layout ?? {};
  const style = { boxSizing: 'border-box', minWidth: '0', flexShrink: '0' };
  if (measure(layout.width)) style.width = measure(layout.width);
  if (measure(layout.height)) style.height = measure(layout.height);
  if (node.type === 'Page') style.minHeight = `${payload.minPageHeight}px`;
  if (node.children?.length) {
    style.display = 'flex';
    const childrenWidth = node.children.reduce((sum, child) => sum + (child.layout?.width?.value ?? 0), 0);
    const gapSize = layout.gap?.token ? token(layout.gap.token) : layout.gap?.value ?? 0;
    const gridBreaksRows = node.type === 'Grid' && childrenWidth + gapSize * (node.children.length - 1) > (layout.width?.value ?? Infinity) + 1;
    style.flexDirection = gridBreaksRows ? 'column' : layout.direction === 'horizontal' || node.type === 'Grid' || node.type === 'HorizontalStack' ? 'row' : 'column';
    style.gap = length(layout.gap?.token ? token(layout.gap.token) : layout.gap?.value) ?? '0px';
    if (layout.wrap) style.flexWrap = 'wrap';
    const main = layout.alignment?.main;
    if (main) style.justifyContent = { start: 'flex-start', end: 'flex-end', center: 'center', 'space-between': 'space-between' }[main] ?? 'flex-start';
    const cross = layout.alignment?.cross;
    if (cross) style.alignItems = { start: 'flex-start', end: 'flex-end', center: 'center', stretch: 'stretch' }[cross] ?? 'stretch';
  }
  if (layout.padding) for (const side of ['top', 'right', 'bottom', 'left']) {
    const part = layout.padding[side];
    style[`padding${side[0].toUpperCase()}${side.slice(1)}`] = length(part?.token ? token(part.token) : part?.value ?? 0);
  }
  if (node.style?.fill?.token) style.backgroundColor = token(node.style.fill.token);
  return style;
}

function component(node) {
  const kind = payload.catalog[node.componentId]?.componentType;
  const defaults = scope(node);
  const base = structuredClone(scopedProps(defaults));
  for (const key of ['kind', 'visibleText', 'text', 'selectedText', 'value', 'showHeader', 'border', 'stripe', 'columns', 'data']) {
    if (key in base && !['showHeader', 'border', 'stripe', 'columns', 'data'].includes(key)) delete base[key];
  }
  const final = currentStage.value === 'delivery';
  const source = content(node);
  const attrs = { 'data-node-id': node.id, 'data-source-id': node.sourceIds?.[0] ?? '', 'data-component-type': kind,
    class: 'component-cell', style: { width: measure(node.layout?.width), minWidth: '0' } };
  let child;
  switch (kind) {
    case 'Button':
      child = h(Button, { type: 'primary', size: 'default' }, () => final ? textOf(source.slots?.label?.[0]?.claim) : defaults.text);
      break;
    case 'Input':
      child = h(Input, { placeholder: final ? getText(node, 'placeholder', defaults.placeholder) : defaults.placeholder,
        modelValue: defaults.value ?? '', readonly: true, style: { width: '100%' } });
      break;
    case 'Select': {
      const label = final ? getText(node, 'value', defaults.selectedText) : defaults.selectedText;
      const value = defaults.modelValue ?? label;
      child = h(Select, { modelValue: value, style: { width: '100%' } },
        { default: () => h(Option, { value, label }, () => label) });
      break;
    }
    case 'Table': {
      const table = scopedProps(defaults);
      const headers = source.props?.headers;
      const columns = final && headers ? table.columns.map((column, index) => ({ ...column, title: textOf(headers[index]) })) : table.columns;
      const data = final && source.tableRecords ? source.tableRecords.map(row => Object.fromEntries(Object.entries(row).map(([key, value]) => [key, textOf(value)]))) : table.data;
      child = h(Table, { columns, data, showHeader: table.showHeader, border: table.border, stripe: table.stripe,
        width: Number(node.layout?.width?.value), size: 'default' });
      break;
    }
    case 'Tag': child = h(Tag, base, () => defaults.text ?? defaults.visibleText?.[0] ?? ''); break;
    case 'Checkbox': child = h(Checkbox, base, () => defaults.text ?? defaults.visibleText?.[0] ?? ''); break;
    case 'Radio': child = h(Radio, base, () => defaults.text ?? defaults.visibleText?.[0] ?? ''); break;
    case 'Switch': child = h(Switch, base); break;
    case 'Card': child = h(Card, base, { default: () => defaults.visibleText?.[0] ?? '' }); break;
    case 'Pagination': child = h(Page, base); break;
    case 'Tabs': child = h(Tabs, base, { default: () => [h(TabPane, { name: 'overview', label: defaults.visibleText?.[0] ?? '概览' }, () => defaults.visibleText?.[1] ?? ''), h(TabPane, { name: 'detail', label: defaults.visibleText?.[2] ?? '详情' })] }); break;
    case 'Tree': child = h(Tree, base); break;
    case 'DatePicker': child = h(DatePicker, base); break;
    case 'Form': child = h(Form, base, { default: () => h(FormItem, { label: defaults.visibleText?.[0] ?? '' }, () => h(Input, { modelValue: '' })) }); break;
    case 'Modal': child = h(Modal, base, { default: () => defaults.visibleText?.[0] ?? '' }); break;
    case 'Drawer': child = h(Drawer, base, { default: () => defaults.visibleText?.[0] ?? '' }); break;
    case 'Upload': child = h(Upload, base, { default: () => defaults.visibleText?.[0] ?? '' }); break;
    case 'Cascader': child = h(Cascader, base); break;
    default: throw new Error(`unsupported_html_component:${kind}:${node.componentId}`);
  }
  return h('div', attrs, [child]);
}

function renderNode(node) {
  if (node.type === 'ComponentInstance') return component(node);
  if (node.type === 'Text') {
    const typo = node.style?.typographyToken?.token ? token(node.style.typographyToken.token) : {};
    const fontSize = typo.fontSize?.token ? token(typo.fontSize.token) : typo.fontSize ?? 14;
    const lineHeight = typo.lineHeight?.token ? token(typo.lineHeight.token) : typo.lineHeight ?? 22;
    const style = { ...boxStyle(node), fontFamily: 'Inter, Arial, sans-serif', fontSize: length(fontSize),
      fontWeight: typo.fontWeight ?? 400, lineHeight: length(lineHeight), whiteSpace: 'nowrap',
      color: node.style?.colorToken?.token ? token(node.style.colorToken.token) : token('color.text') };
    return h('div', { 'data-node-id': node.id, 'data-source-id': node.sourceIds?.[0] ?? '', class: 'page-text', style }, currentStage.value === 'component' ? '文本' : node.text);
  }
  if (node.type === 'IconInstance') {
    const svg = payload.icons[node.iconId];
    if (!svg) throw new Error(`missing_icon:${node.iconId}`);
    return h('span', { 'data-node-id': node.id, 'data-source-id': node.sourceIds?.[0] ?? '', class: 'page-icon',
      style: { ...boxStyle(node), display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }, innerHTML: svg });
  }
  return h('div', { 'data-node-id': node.id, 'data-source-id': node.sourceIds?.[0] ?? '',
    'data-node-type': node.type, class: `design-${node.type.toLowerCase()}`, style: boxStyle(node) },
    node.children?.map(renderNode) ?? []);
}

function renderSkeleton() {
  const skeleton = payload.skeleton;
  return h('main', { class: 'skeleton-page', style: { width: length(skeleton.box.width), height: length(Math.max(skeleton.box.height, payload.minPageHeight)),
    background: token('color.page'), position: 'relative' } }, skeleton.cells.map(cell =>
      h('div', { 'data-cell-id': cell.cellId, 'data-source-id': cell.sourceId, 'data-component-type': cell.componentType,
        class: 'skeleton-cell', style: { position: 'absolute', left: length(cell.box.x), top: length(cell.box.y),
          width: length(cell.box.width), height: length(cell.box.height), background: cell.color } },
      `${cell.componentType} · ${cell.label}`)));
}

const labels = { skeleton: '彩色骨架', component: '默认组件', delivery: '交付页面' };
createApp({ render: () => h('div', [
  h('nav', { class: 'stage-nav', 'aria-label': '页面阶段' }, stages.map(stage =>
    h('button', { type: 'button', class: currentStage.value === stage ? 'active' : '',
      onClick: () => window.__setDesignStage(stage) }, labels[stage]))),
  currentStage.value === 'skeleton' ? renderSkeleton() :
    renderNode(payload.documents[currentStage.value].pages[0]),
]) }).mount('#app');
window.__setDesignStage = async stage => {
  if (!stages.includes(stage)) throw new Error(`unknown_stage:${stage}`);
  currentStage.value = stage;
  location.hash = stage;
  await nextTick();
  await document.fonts.ready;
};
await nextTick();
window.__designReady = true;
