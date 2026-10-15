import {createApp, h, nextTick} from 'vue';
import {Tabs, TabPane} from 'view-ui-plus';
import cases from './tabs-cases.json';

const instances = new Map();
createApp({
  render() {
    return h('main', {id: 'runtime-gallery', style: {padding: '24px'}},
      cases.cases.map(item => h('section', {
        'data-runtime-case': item.logicalId,
        style: {width: `${cases.containerWidth}px`}
      }, [h(Tabs, {...item.props, ref: instance => instances.set(item.logicalId, instance)},
        {default: () => item.tabs.map(tab => h(TabPane, {name: tab.name, label: tab.label},
          {default: () => tab.text}))})])));
  }
}).mount('#app');
await nextTick();
await nextTick();
window.__runtimeMounted = true;
window.__runtimeResolvedProps = () => Object.fromEntries([...instances].map(([id, instance]) => [id,
  JSON.parse(JSON.stringify(instance.$props, (_key, value) => typeof value === 'function'
    ? {runtimeType: 'function'} : value === undefined ? {runtimeType: 'undefined'} : value))]));
