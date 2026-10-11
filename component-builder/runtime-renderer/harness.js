import { createApp, h, nextTick } from 'vue';
import { Button, Input, Select, Option } from 'view-ui-plus';
import cases from './cases.json';

const components = { Button, Input, Select };
const instances = new Map();
createApp({
  render() {
    return h('main', { id: 'runtime-gallery', style: { display: 'flex', gap: '24px', padding: '24px', alignItems: 'flex-start' } }, cases.cases.map(item => {
      const slots = item.componentType === 'Button' ? { default: () => item.text } :
        item.componentType === 'Select' ? { default: () => item.options.map(option => h(Option, { value: option.value, label: option.label }, () => option.label)) } : undefined;
      return h('section', { 'data-runtime-case': item.logicalId, style: { width: `${cases.containerWidth}px` } }, [h(components[item.componentType], { ...item.props, ref: instance => instances.set(item.logicalId, instance) }, slots)]);
    }));
  }
}).mount('#app');
await nextTick();
window.__runtimeMounted = true;
window.__runtimeResolvedProps = () => Object.fromEntries([...instances].map(([id, instance]) => [id,
  JSON.parse(JSON.stringify(instance.$props, (_key, value) => typeof value === 'function' ? { runtimeType: 'function' } : value === undefined ? { runtimeType: 'undefined' } : value))
]));
