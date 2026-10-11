# Official runtime font diagnostic

Run `node component-builder/runtime-renderer/font-probe.mjs --output artifacts/task-009/font-probe --reference artifacts/task-006`.
The output must be separate from the reference. Source packages, CSS, harness, browser settings and extraction are reused; the optional observer reads CDP font usage. Original TASK-006 files are retained. A new extraction records the current renderer hash, rather than rewriting the original provenance.

The report binds the reference Component IR hash and compares each component screenshot hash and environment. PASS here means only that this diagnostic reproduced the reference. It never admits a native design component; fidelityGate remains NOT_RUN. Drift produces REVIEW, execution errors produce FAIL.

CDP [CSS.getPlatformFontsForNode](https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-getPlatformFontsForNode) returns fonts used by child text nodes. Element, pseudo-element and user-agent shadow observations are kept separate. Glyph counts from parent and child observations can overlap and must not be summed. Empty usage remains NO_GLYPHS_REPORTED; it does not establish an absent font. No system font filename, per-character font assignment or substitute is inferred.

The actual Windows reference uses PingFang SC (PingFangSC-Regular) for button text, the input placeholder and selected text. The Select before pseudo-element uses the custom Ionicons font. These names differ from project Noto Sans SC tokens. The recorded Figma font discovery did not expose these source families; native fidelity remains pending.

Real browser tests cover placeholder shadow glyphs, pseudo glyphs, unchanged reference files and pixels, reference drift and protected output rejection.
