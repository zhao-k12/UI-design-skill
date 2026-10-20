import {createApp, h, nextTick} from 'vue';
import {Upload} from 'view-ui-plus';
import cases from './upload-cases.json';

const instances = new Map();
createApp({
  render() {
    return h('main', {id: 'runtime-gallery', style: {padding: '24px'}},
      cases.cases.map(item => h('section', {style: {width: `${cases.containerWidth}px`}},
        [h(Upload, {...item.props, 'data-runtime-case': item.logicalId,
          ref: instance => instances.set(item.logicalId, instance)},
          {default: () => h('div', {
            style: {width: '100%', height: '80px', display: 'flex',
              alignItems: 'center', justifyContent: 'center'}
          }, item.text)})])));
  }
}).mount('#app');
await nextTick();
window.__runtimeMounted = true;
window.__runtimeResolvedProps = () => Object.fromEntries([...instances].map(([id, instance]) => [id,
  JSON.parse(JSON.stringify(instance.$props, (_key, value) => typeof value === 'function'
    ? {runtimeType: 'function'} : value === undefined ? {runtimeType: 'undefined'} : value))]));
