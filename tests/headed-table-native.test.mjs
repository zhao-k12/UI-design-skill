import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import vm from 'node:vm';
import {ROOT} from '../component-builder/source-reader/source-lock.mjs';

test('Semibold missing or ambiguous aborts headed Penpot candidate before creating shapes',async()=>{
  const context=vm.createContext({});
  vm.runInContext(await readFile(join(ROOT,'adapters/penpot/component_candidate.js'),'utf8')+'\n'+await readFile(join(ROOT,'adapters/penpot/headed_table_candidate.js'),'utf8'),context);
  const logical='data.table.headed.'+'a'.repeat(64);
  const spec={fileReference:'file',pageReference:'page',logicalId:logical,requiredFonts:['PingFang SC'],rows:[{cells:[{text:{fontFamily:'PingFang SC',fontWeight:600}}]}]};
  let writes=0;
  const font={fontFamily:'PingFang SC',variants:[{fontWeight:'400',fontStyle:'normal',fontVariantId:'normal-400'}]};
  const api={currentFile:{id:'file'},currentPage:{id:'page',root:{children:[]}},library:{local:{components:[]}},fonts:{all:[font]},createBoard(){writes++;throw Error('unexpected write');}};
  await assert.rejects(()=>context.buildHeadedPenpotTableCandidate(api,spec),/candidate_font_variant_missing_or_ambiguous/);
  font.variants.push({fontWeight:'600',fontStyle:'normal',fontVariantId:'normal-600-a'},{fontWeight:'600',fontStyle:'normal',fontVariantId:'normal-600-b'});
  await assert.rejects(()=>context.buildHeadedPenpotTableCandidate(api,spec),/candidate_font_variant_missing_or_ambiguous/);
  await assert.rejects(()=>context.buildHeadedPenpotTableCandidate(api,{...spec,logicalId:'data.table.config.'+'a'.repeat(64)}),/candidate_context_mismatch/);
  assert.equal(writes,0);
});
