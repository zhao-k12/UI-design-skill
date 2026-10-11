import {hash} from '../source-reader/source-lock.mjs';

const plain=value=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype;
function keys(value,expected,label){
  if(!plain(value)||Object.keys(value).length!==expected.length||expected.some(key=>!Object.hasOwn(value,key)))throw Error('invalid_table_'+label);
}
function text(value,label){
  if(typeof value!=='string'||!value.trim()||value.length>512||/[\u0000-\u001f\u007f]/.test(value))throw Error('invalid_table_'+label);
}

/** Compile static plain-text data into an official Table fixture; never admit it. */
export function compileTableRequest(request){
  keys(request,['version','containerWidth','columns','records'],'request');
  if(request.version!=='0.1.0'||!Number.isInteger(request.containerWidth)||request.containerWidth<128||request.containerWidth>3840)throw Error('invalid_table_dimensions');
  if(!Array.isArray(request.columns)||request.columns.length<1||request.columns.length>12)throw Error('invalid_table_columns');
  const seen=new Set();let width=0;
  const columns=request.columns.map(column=>{
    keys(column,['key','title','width'],'column');text(column.title,'title');
    if(typeof column.key!=='string'||!/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(column.key)||['__proto__','prototype','constructor'].includes(column.key)||seen.has(column.key))throw Error('invalid_table_column_key');
    if(!Number.isInteger(column.width)||column.width<64)throw Error('invalid_table_column_width');
    seen.add(column.key);width+=column.width;
    return {title:column.title,key:column.key,width:column.width};
  });
  if(width!==request.containerWidth)throw Error('table_column_width_total_mismatch');
  if(!Array.isArray(request.records)||request.records.length<1||request.records.length>50)throw Error('invalid_table_records');
  const data=request.records.map(record=>{
    keys(record,[...seen],'record');
    return Object.fromEntries(columns.map(column=>{text(record[column.key],'cell');return [column.key,record[column.key]];}));
  });
  const normalized={version:'0.1.0',containerWidth:request.containerWidth,columns,records:data};
  const requestSha256=hash(JSON.stringify(normalized));
  const cases={casesVersion:'0.1.0',viewport:{width:request.containerWidth+48,height:Math.max(400,data.length*48+96)},containerWidth:request.containerWidth,
    cases:[{logicalId:'data.table.config.'+requestSha256,componentType:'Table',variant:'default',props:{showHeader:false,border:false,stripe:false,columns,data}}]};
  return {request:normalized,requestSha256,cases};
}
