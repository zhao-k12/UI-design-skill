// Preserve observed runtime data. This module does not infer component visuals.
export function assembleComponentIr(item, captured, resolvedProps, context, screenshot) {
  if (!resolvedProps || captured.rootBounds.width <= 0 || captured.rootBounds.height <= 0) throw new Error('empty_runtime_component: ' + item.logicalId);
  return {
    componentIrVersion: '0.1.0', evidenceKind: 'official-runtime',
    logicalComponentId: item.logicalId, componentType: item.componentType,
    variant: item.variant, state: 'default-static', props: structuredClone(item.props), resolvedProps,
    content: { text: item.text ?? null, options: structuredClone(item.options ?? []) },
    fixtureContext: { containerWidth: context.containerWidth },
    provenance: structuredClone(context.provenance), environment: structuredClone(context.environment),
    ...captured, screenshot
  };
}
