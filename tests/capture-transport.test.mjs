import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
const source=await readFile(new URL('../adapters/figma/capture_transport.js',import.meta.url),'utf8');
const context=vm.createContext({Math,Array,Object,JSON,Number,unescape,encodeURIComponent});vm.runInContext(source,context);
test('bounded native transport SHA256 matches independent crypto for Unicode and raw PNG bytes',()=>{
  for(const value of ['', '查询 · 用户列表', 'x'.repeat(10000)])assert.equal(context.captureSha256(value),createHash('sha256').update(value).digest('hex'));
  const bytes=Uint8Array.from({length:1000},(_,i)=>i%256);assert.equal(context.captureSha256('',bytes),createHash('sha256').update(bytes).digest('hex'));
});
test('transport slices reassemble one hash-bound successful capture and reject invalid indexes',()=>{
  const result={status:'PASS',value:'查询'.repeat(8000)},first=context.captureTransportPiece(result,0),parts=[];
  for(let i=0;i<first.count;i++){const part=context.captureTransportPiece(result,i);assert.equal(part.captureSha256,first.captureSha256);assert.ok(part.chunk.length<=6500);parts.push(part.chunk);}
  assert.deepEqual(JSON.parse(parts.join('')),result);assert.throws(()=>context.captureTransportPiece(result,first.count));
});
