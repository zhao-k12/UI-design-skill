import test from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {renderNativeSvg} from '../component-builder/runtime-renderer/native-svg-probe.mjs';
test('real browser renders a bounded native SVG without resizing or resource requests',async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({deviceScaleFactor:1});const requests=[];page.on('request',request=>requests.push(request.url()));
    const result=await renderNativeSvg(page,{width:8,height:8,svg:'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 8 8"><rect width="8" height="8" fill="white"/></svg>'});
    assert.deepEqual(result.bounds,{x:0,y:0,width:8,height:8});assert.equal(result.png.readUInt32BE(16),8);assert.equal(result.png.readUInt32BE(20),8);
    assert.equal(requests.length,0);
    for(const svg of ['<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>',
      '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 8 8"><rect width="8" height="8" fill="url(https://example.com)"/></svg>',
      '<svg xmlns="http://www.w3.org/2000/svg" width="9" height="8" viewBox="0 0 9 8"/>']) {
      await assert.rejects(renderNativeSvg(page,{width:8,height:8,svg}));
    }
    assert.equal(requests.length,0);
  } finally {await browser.close();}
});
