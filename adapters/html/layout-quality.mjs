// Browser measurements only; these checks cannot authenticate source observations.
export function measureLayoutQuality() {
  const results = [];
  const documentWidth=document.documentElement.scrollWidth;
  if(documentWidth>innerWidth+1)results.push({id:'viewport',kind:'page-overflow',status:'FAIL',issues:['viewport_overflow'],measurement:{documentWidth,viewportWidth:innerWidth}});
  const canvas = document.createElement('canvas'), context = canvas.getContext('2d');
  const rect = e => { const r=e.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
  const id = e => e.closest('[data-tree-node]')?.dataset.treeNode || 'unbound';
  const emit = (element, kind, issues, measurement) => results.push({id:id(element),kind,status:issues.length?'FAIL':'PASS',issues,measurement});
  for (const input of document.querySelectorAll('input.ivu-input')) {
    const r=rect(input), style=getComputedStyle(input);
    if (!r.width || !r.height || style.visibility==='hidden' || input.type==='hidden') continue;
    const text=input.value || input.placeholder;
    if (!text || input.type==='password') continue;
    context.font=style.font;
    const spacing=parseFloat(style.letterSpacing)||0;
    const needed=context.measureText(text).width+Math.max(0,text.length-1)*spacing;
    let available=r.width-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0)
      -(parseFloat(style.borderLeftWidth)||0)-(parseFloat(style.borderRightWidth)||0);
    // A suffix can overlap the native input even when padding was not reserved.
    for (const suffix of input.parentElement.querySelectorAll(':scope > .ivu-input-suffix')) {
      const sr=rect(suffix);
      available=Math.min(available,sr.left-r.left-(parseFloat(style.paddingLeft)||0));
    }
    emit(input,'input-text-fit',needed>available+1?['input_text_clipped']:[],{text,needed,available,input:r});
  }
  for (const label of document.querySelectorAll('.ivu-form-item-label')) {
    const form=label.closest('.ivu-form'), item=label.closest('[data-component="FormItem"]');
    if (!label.textContent.trim() || !label.getBoundingClientRect().width || form?.classList.contains('ivu-form-label-top') || item?.dataset.allowLabelWrap==='true') continue;
    const range=document.createRange();range.selectNodeContents(label);
    const lines=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
    const tops=[];for(const line of lines)if(!tops.some(y=>Math.abs(y-line.top)<=1))tops.push(line.top);
    emit(label,'horizontal-label-lines',tops.length>1?['horizontal_label_wrapped']:[],{text:label.textContent.trim(),lines:tops.length,label:rect(label)});
  }
  for(const selected of document.querySelectorAll('.ivu-select-selection .ivu-select-selected-value,.ivu-select-selection .ivu-select-placeholder')){
    const r=rect(selected),s=getComputedStyle(selected),text=selected.textContent.trim();
    if(!r.width||!r.height||!text||s.visibility==='hidden'||s.display==='none')continue;
    context.font=s.font;
    const needed=context.measureText(text).width+Math.max(0,text.length-1)*(parseFloat(s.letterSpacing)||0);
    const available=r.width-(parseFloat(s.paddingLeft)||0)-(parseFloat(s.paddingRight)||0);
    emit(selected,'select-text-fit',needed>available+1?['select_text_clipped']:[],{text,needed,available,selection:r});
  }
  const roles=['module-panel','summary-panel','steps-panel'];
  const modules=[...document.querySelectorAll('[data-design-role]')].filter(e=>roles.includes(e.dataset.designRole)||
    (e.dataset.designRole==='form-section'&&e.parentElement.dataset.treeNode?.endsWith('-main')));
  for(const panel of modules){
    const r=rect(panel), parent=rect(panel.parentElement), issues=[];
    const left=r.left-parent.left,right=parent.right-r.right;
    if(Math.abs(left-24)>1||Math.abs(right-24)>1)issues.push('module_outer_spacing_mismatch');
    const previous=panel.previousElementSibling;
    let gap=null;
    if(previous&&(roles.includes(previous.dataset.designRole)||previous.dataset.designRole==='form-section')){
      gap=r.top-rect(previous).bottom;if(Math.abs(gap-16)>1)issues.push('module_gap_mismatch');
    }
    emit(panel,'module-spacing',issues,{left,right,gap,panel:r,parent});
  }
  for(const close of document.querySelectorAll('[data-design-role="module-close"]')){
    const panel=close.closest('[data-design-role="summary-panel"]');if(!panel)continue;
    const r=rect(close),p=rect(panel),top=r.top-p.top,right=p.right-r.right;
    emit(close,'summary-close',Math.abs(top-16)>1||Math.abs(right-16)>1||Math.abs(r.width-16)>1||Math.abs(r.height-16)>1?['summary_close_geometry_mismatch']:[],{top,right,width:r.width,height:r.height});
  }
  for(const meta of document.querySelectorAll('[data-design-role="summary-panel"] [data-design-role="summary-meta"]')){
    const heading=meta.parentElement.querySelector(':scope > [data-design-role="summary-heading"]');if(!heading)continue;
    const gap=rect(meta).top-rect(heading).bottom;
    emit(meta,'summary-meta-gap',Math.abs(gap-16)>1?['summary_meta_gap_mismatch']:[],{gap});
  }
  return {status:results.some(r=>r.status==='FAIL')?'FAIL':'PASS',results,
    scope:'Input text fit, horizontal label lines and explicit reusable module geometry only; no source or aesthetic judgment.'};
}
