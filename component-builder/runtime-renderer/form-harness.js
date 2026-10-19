import {createApp, h, nextTick} from 'vue';
import {Form, FormItem, Input} from 'view-ui-plus';
import cases from './form-cases.json';

const instances = new Map();
createApp({
  render() {
    return h('main', {id: 'runtime-gallery', style: {padding: '24px'}},
      cases.cases.map(item => h('section', {
        'data-runtime-case': item.logicalId,
        style: {width: `${cases.containerWidth}px`}
      }, [h(Form, {...item.props, ref: instance => instances.set(item.logicalId, instance)}, {
        default: () => h(FormItem, {label: '姓名', prop: 'name'}, {
          default: () => h(Input, {modelValue: '', placeholder: '请输入姓名', clearable: false})
        })
      })])));
  }
}).mount('#app');
await nextTick();
window.__runtimeMounted = true;
window.__runtimeResolvedProps = () => Object.fromEntries([...instances].map(([id, instance]) => [id,
  JSON.parse(JSON.stringify(instance.$props, (_key, value) => typeof value === 'function'
    ? {runtimeType: 'function'} : value === undefined ? {runtimeType: 'undefined'} : value))]));
