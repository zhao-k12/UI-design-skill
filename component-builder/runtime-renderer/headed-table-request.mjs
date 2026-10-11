import {compileTableRequest} from './table-request.mjs';
import {hash} from '../source-reader/source-lock.mjs';

// Separate identity prevents a headed table from reusing a body-only admission.
export function compileHeadedTableRequest(request){
  const compiled=compileTableRequest(request);
  const requestSha256=hash(JSON.stringify({scope:'official_table_with_header',request:compiled.request}));
  const cases=structuredClone(compiled.cases);
  cases.viewport.height+=64;
  cases.cases[0].logicalId='data.table.headed.'+requestSha256;
  cases.cases[0].props.showHeader=true;
  return {...compiled,requestSha256,cases};
}
