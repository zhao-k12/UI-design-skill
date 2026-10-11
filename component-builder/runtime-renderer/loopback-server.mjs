import {randomInt} from 'node:crypto';

// The Fetch bad-port table ends below this range. Never bypass browser security.
// https://fetch.spec.whatwg.org/#port-blocking
export async function listenBrowserLoopback(server, pickPort=()=>randomInt(49152,65536)) {
  for(let attempt=0;attempt<16;attempt++) {
    const port=pickPort();
    if(!Number.isInteger(port)||port<49152||port>65535)throw new Error('invalid_browser_loopback_port');
    try {
      await new Promise((resolve,reject)=>{
        const cleanup=()=>{server.removeListener('error',failed);server.removeListener('listening',ready);};
        const failed=error=>{cleanup();reject(error);};
        const ready=()=>{cleanup();resolve();};
        server.once('error',failed);server.once('listening',ready);
        try {server.listen(port,'127.0.0.1');} catch(error) {failed(error);}
      });
      return;
    } catch(error) {if(error.code!=='EADDRINUSE')throw error;}
  }
  throw new Error('browser_loopback_ports_exhausted');
}
