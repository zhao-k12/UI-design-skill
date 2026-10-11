// Read-only host discovery. No native writes, network, credentials or user profile.
function discoverPenpotHost(api) {
  if (!api.currentFile || !api.currentPage) throw new Error('open_design_file_required');
  return {platform:'penpot', fileReference:api.currentFile.id, fileRevision:api.currentFile.revn,
    pageReference:api.currentPage.id, pages:api.currentFile.pages.map(p => ({id:p.id,name:p.name})),
    fonts:api.fonts.all.map(f => ({fontId:f.fontId,family:f.fontFamily,
      variants:f.variants.map(v => ({fontVariantId:v.fontVariantId,weight:Number(v.fontWeight),style:v.fontStyle}))})),
    components:api.library.local.components.map(c => {
      const main = c.mainInstance();
      return {componentReference:c.id,name:c.name,mainReference:main?.id,width:main?.width,height:main?.height};
    })};
}
