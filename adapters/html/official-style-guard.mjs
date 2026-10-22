// Local page CSS may arrange hosts and annotate the skeleton, never restyle View UI Plus internals.
export function assertNoOfficialComponentOverrides(localCss, label = 'local CSS') {
  const selectors = [...localCss.matchAll(/([^{}]+)\{/g)]
    .map(match => match[1].trim())
    .filter(selector => /\.ivu-[a-z0-9-]+/i.test(selector));
  if (selectors.length) {
    throw new Error(`official_component_style_override:${label}:${selectors[0]}`);
  }
}
