# Evidence-bound fidelity 0.2.0

Approved scope: TASK-009 decision AD-017, 2026-10-07. Policy 0.1.0 remains available for exact pixel comparison.

Admission requires every strict proof: source reproduction, native geometry/styles/content, actual font binding and file effect, complete directed glyph regions, measured baselines, render state, and whole-native-vector binding. The adapter preserves original observations and records proof input hashes; it does not copy browser measurements into native observations. Missing or unsupported equivalence rejects admission.

The original Figma PNG is alpha-composited on white, without resizing, cropping, filtering or reference overlays. A separately exported native SVG is rendered in the reference browser solely to construct a coverage boundary. Eight-neighbor color transitions plus one pixel of support define that boundary. Every differing pixel must belong both to this boundary and to a verified text region or explicitly verified rounded corner. Whole-page ratios and wide channel tolerances are not used. All nontext vector pixels outside approved corners must match the browser reference exactly. The Table has no corner exemption; all of its nontext pixels must match in both native PNG and browser SVG.

Each visible glyph also retains between half and twice the reference's foreground coverage proxy. This is a missing/solid-glyph guard, not an aggregate difference allowance. It cannot certify typography or geometry: those must already PASS the independent exact proofs. Tests reject erased thin glyphs even when every changed pixel lies inside the edge band.

The Ionicons arrow uses a fixed six-significant-digit serialization proof, with every point and directed contour checked. Arbitrary small coordinate differences do not pass. Chinese contours require exact nonzero path equivalence; a uniform reversal preserves the zero winding set. Glyph horizontal origins and measured baselines remain exact.

The Table's same-paint adjoining cell borders are emitted as their exact geometric union, avoiding internal coverage seams. Its bottom pseudo-element is derived from the hash-verified official CSS. Full directed path identity establishes mathematical glyph extents and common baseline translation; rounded floating-point extrema diagnostics are not substituted for that proof.

Only the four locked static fixtures are admitted. The Table fixture uses official `showHeader=false`; its separate column labels are UI-IR nodes. Arbitrary source props/slots, additional component types and dual-platform release acceptance remain outside this milestone.
