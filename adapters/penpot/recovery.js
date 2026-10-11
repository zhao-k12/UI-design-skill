// Read-only inspection of an exact partial-write ledger. Never deletes or duplicates work.
function inspectPenpotRecovery(api, ledger) {
  if (ledger.status !== 'FAIL' || ledger.nativeExecution !== 'PARTIAL' || ledger.scope !== 'penpot_partial_translation') throw new Error('invalid_partial_ledger');
  if (api.currentFile?.id !== ledger.fileReference || api.currentPage?.id !== ledger.pageReference) throw new Error('recovery_context_mismatch');
  if (!Array.isArray(ledger.createdNodeIds) || !ledger.createdNodeIds.every(id => typeof id === 'string') ||
      new Set(ledger.createdNodeIds).size !== ledger.createdNodeIds.length || !Array.isArray(ledger.mutatedNodeIds) || ledger.mutatedNodeIds.length) {
    throw new Error('invalid_creation_ledger');
  }
  const created = new Set(ledger.createdNodeIds), present = [], missing = [], unexpectedChildren = [];
  for (const nodeId of ledger.createdNodeIds) {
    if (nodeId === ledger.pageReference) { present.push({nodeId,type:'page',name:api.currentPage.name}); continue; }
    const n = api.currentPage.getShapeById(nodeId);
    if (!n) { missing.push(nodeId); continue; }
    present.push({nodeId,type:n.type,name:n.name,parentReference:n.parent?.id});
    for (const child of n.children || []) if (!created.has(child.id)) unexpectedChildren.push({parentReference:nodeId,nodeId:child.id});
  }
  return {status:'REVIEW',scope:'penpot_partial_recovery_inspection',fileReference:ledger.fileReference,pageReference:ledger.pageReference,
    createdNodeIds:[],mutatedNodeIds:[],present,missing,unexpectedChildren,automaticResumeAllowed:false,
    reason:'Review the surviving native nodes and ledger before any targeted repair'};
}
