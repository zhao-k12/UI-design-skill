// Bounded transport of a single deterministic capture, never image processing.
function captureSha256(text,inputBytes){
  const bytes=inputBytes===undefined?Array.from(unescape(encodeURIComponent(text)),c=>c.charCodeAt(0)):Array.from(inputBytes);
  const length=bytes.length;bytes.push(128);while(bytes.length%64!==56)bytes.push(0);
  const bits=length*8;for(let i=7;i>=0;i--)bytes.push(i>=4?0:(bits>>>i*8)&255);
  const constants=[],initial=[];let prime=2;
  while(constants.length<64){let valid=true;for(let d=2;d*d<=prime;d++)if(prime%d===0){valid=false;break;}
    if(valid){if(initial.length<8)initial.push((Math.sqrt(prime)%1*4294967296)|0);constants.push((Math.cbrt(prime)%1*4294967296)|0);}prime++;}
  const rotate=(x,n)=>(x>>>n)|(x<<(32-n));const hash=initial.slice();
  for(let offset=0;offset<bytes.length;offset+=64){const w=[];for(let i=0;i<16;i++)w[i]=(bytes[offset+i*4]<<24)|(bytes[offset+i*4+1]<<16)|(bytes[offset+i*4+2]<<8)|bytes[offset+i*4+3];
    for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(rotate(a,7)^rotate(a,18)^(a>>>3))+w[i-7]+(rotate(b,17)^rotate(b,19)^(b>>>10)))|0;}
    let[a,b,c,d,e,f,g,h]=hash;for(let i=0;i<64;i++){const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+constants[i]+w[i])|0;const t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))|0;h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;}
    [a,b,c,d,e,f,g,h].forEach((value,i)=>hash[i]=(hash[i]+value)|0);
  }
  return hash.map(n=>(n>>>0).toString(16).padStart(8,'0')).join('');
}
function captureTransportPiece(result,index){
  if(result.status!=='PASS')return result;
  const raw=JSON.stringify(result),chunkSize=6500,count=Math.ceil(raw.length/chunkSize);
  if(!Number.isInteger(index)||index<0||index>=count)throw new Error('invalid_capture_transport_piece');
  return{scope:'figma_capture_transport_piece',status:'PASS',index,count,totalCharacters:raw.length,
    captureSha256:captureSha256(raw),chunk:raw.slice(index*chunkSize,(index+1)*chunkSize)};
}
