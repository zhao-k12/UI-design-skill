const nonce = "0bfa1e6ac1f009706d5c8fd2702ec6c71cdece35cbd67f44";

    const button=document.getElementById('inspect'), status=document.getElementById('status');
    button.onclick=()=>{button.disabled=true;status.textContent='正在读取实际文件…';parent.postMessage({type:'task010-inspect'},'https://design.penpot.app');};
    window.addEventListener('message',async event=>{
      if(event.source!==parent || event.origin!=='https://design.penpot.app' || event.data?.type!=='task010-result')return;
      try {
        const response=await fetch('/receipt',{method:'POST',headers:{'Content-Type':'application/json','X-Task-Nonce':nonce},body:JSON.stringify(event.data)});
        if(!response.ok)throw new Error('本机记录保存失败');
        const result=event.data.result;
        status.textContent=event.data.status==='CAPTURED'?`端到端执行：${result.status}，最终验收待检查。`:event.data.error;
      }catch(error){status.textContent=String(error);}finally{button.disabled=false;}
    });
    
document.getElementById('create').onclick=()=>parent.postMessage({type:'pipeline-create'},'https://design.penpot.app');
document.getElementById('capture').onclick=()=>parent.postMessage({type:'pipeline-capture'},'https://design.penpot.app');
document.getElementById('style').onclick=()=>parent.postMessage({type:'pipeline-style'},'https://design.penpot.app');
document.getElementById('instances').onclick=()=>parent.postMessage({type:'pipeline-instances'},'https://design.penpot.app');