// Read every bound Figma master in one host call. The specs assignment is generated from locked Registry data.
const specs = __SPECS__;
const result = {scope:'figma-batch-master-native-read',fileReference:figma.fileKey,
  readMethod:'figma-plugin-api-getNodeByIdAsync',components:{}};
const nodes = await Promise.all(specs.map(spec => figma.getNodeByIdAsync(spec.reference)));
for (let index=0; index<specs.length; index++) {
  const spec = specs[index];
  const node = nodes[index];
  if (!node || node.type !== 'COMPONENT') {
    result.components[spec.logicalId] = {found:false,id:spec.reference,type:node?.type ?? null};
    continue;
  }
  let parent = node.parent;
  while (parent && parent.type !== 'PAGE') parent = parent.parent;
  const texts = node.findAllWithCriteria({types:['TEXT']}).filter(text => text.visible).map(text => ({
    id:text.id,characters:text.characters,
    fontFamily:typeof text.fontName === 'object' ? text.fontName.family : null,
    fontSize:typeof text.fontSize === 'number' ? text.fontSize : null,
    width:text.width,height:text.height
  }));
  result.components[spec.logicalId] = {found:true,id:node.id,type:node.type,name:node.name,
    pageId:parent?.id ?? null,width:node.width,height:node.height,texts};
}
return result;
