import {join} from 'node:path';
import {ROOT} from '../source-reader/source-lock.mjs';
import {probeNativeSvg} from './native-svg-probe.mjs';
import {probeFontFile} from './font-file-probe.mjs';
const options={casesPath:join(ROOT,'component-builder/runtime-renderer/table-cases.json'),harnessPath:join(ROOT,'component-builder/runtime-renderer/table-harness.js')};
const reference=join(ROOT,'artifacts/task-009/table-reference');
const suffix=process.argv[2]??'';
const results=await Promise.allSettled([
  probeNativeSvg(join(ROOT,'adapters/figma/metadata/table-component-svg.json'),reference,join(ROOT,'artifacts/task-009/table-svg-browser'+suffix),options),
  probeFontFile(reference,join(ROOT,'adapters/figma/metadata/font-file-identity.json'),join(ROOT,'artifacts/task-009/table-font-binding'+suffix),options)
]);
for(const result of results){if(result.status==='rejected'){console.error(String(result.reason));process.exitCode=1;}else console.log(JSON.stringify(result.value));}
