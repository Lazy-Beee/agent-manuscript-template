# Symbol table — {{NAME}} manuscript

Editorial companion to `{{DRAFT}}.md`. This file is maintained outside the manuscript and
is not included in the rendered paper. The preflight checker reads it: rows under
**Open notation issues** are reported as open, and every `Eq. (...)` in a location column
must match a `\tag{...}` in the draft.

## Maintenance rules

- Update this table whenever a symbol is added, removed, renamed, or given a new meaning,
  in the same edit as the equation.
- Use bold symbols for vectors and tensors; use plain italic symbols for scalars.
- Give a symbol one meaning throughout the manuscript whenever possible.
- Record a possible reuse in **Open notation issues** and resolve it before submission.
- Move a deliberate, unambiguous reuse to **Accepted notation reuse** after review.
- Equation and section references follow the current draft and must be reconciled after
  equations or appendix blocks are inserted, removed or moved.

## Model symbols

*(One table per model part, e.g. governing equations; constitutive and material models;
boundary conditions; analysis metrics; numerical limits.)*

Examples of the row format (shown as a list so the preflight ignores them):

- `| $T$ | Temperature | K | Section 2.1, energy equation; Figures 3-5 |`
- `| $\mathbf{u}$ | Liquid velocity (vector) | m/s | Section 2.1, momentum equation |`
- `| $\rho$ | Density, a function of temperature | kg/m³ | Section 2.2; Table 1 |`

In a real row an equation location is written `Eq. (n)`, with the number of its `\tag{n}`
in the draft; the preflight checks every such number, so the examples name sections instead.

| Symbol | Meaning | Unit | Current location |
|---|---|---:|---|

## Open notation issues

None.

## Accepted notation reuse

Example (shown as a list):

- `| $h$ | Heat transfer coefficient (Section 2.3); smoothing length (Appendix A.2) | The two never meet in one section, and each is defined where it is used |`

| Symbol | Meanings | Rationale |
|---|---|---|
