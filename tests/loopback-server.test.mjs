import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {randomInt} from 'node:crypto';
import {listenBrowserLoopback} from '../component-builder/runtime-renderer/loopback-server.mjs';
const close=server=>new Promise(resolve=>server.close(resolve));
test('occupied high loopback port retries on real sockets and releases listeners',async()=>{
  const first=createServer(),second=createServer();
  try {
    await listenBrowserLoopback(first);let calls=0;
    await listenBrowserLoopback(second,()=>calls++===0?first.address().port:randomInt(49152,65536));
    assert.ok(calls>=2);assert.notEqual(first.address().port,second.address().port);
    assert.equal(second.address().address,'127.0.0.1');assert.equal(second.listenerCount('error'),0);
    // Node's HTTP server keeps its own listening hook; compare the same server type.
    assert.equal(second.listenerCount('listening'),first.listenerCount('listening'));
  } finally {await close(second);await close(first);}
});
test('unsafe random allocation cannot silently reach browser navigation',async()=>{
  const server=createServer();
  await assert.rejects(listenBrowserLoopback(server,()=>6668),/invalid_browser_loopback_port/);
  assert.equal(server.listening,false);
});
