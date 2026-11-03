# Terminology standard — {{NAME}} manuscript

One preferred term per concept, to keep wording consistent across the draft and every
figure label and caption. Applies to all prose and figure text. **Exempt:** reference
titles (verbatim) and code identifiers in figure scripts. Paragraph, language and figure
conventions live in `writing_conventions.md`.

**How the preflight uses this file.** Every Markdown table row here is read as
`| Concept | Use | Do not use | Note |`. Each comma- or semicolon-separated entry of the
"Do not use" column is flagged in the draft body. Multi-word entries are always flagged. A
single word is flagged only when the row's Note contains `[enforced]`, because single words
often have legitimate other senses; without the marker it is checked by hand. Keep the "Do
not use" column to forbidden terms only, and write `-` when there are none.

## Preferred terms

Lock a term the first time a concept appears, or when a reviewer flags a variant. Examples
of the row format (shown as a list so the checker ignores them):

- `| The liquid region during processing | **molten pool** | melt pool, weld pool | Two words; never shortened to bare "pool". |`
- `| Effect of an event on the fields | **disturbance** | perturbation, perturbations, perturbed | One noun for the effect; [enforced] |`
- `| How a scalar trends with a parameter | **increase** / **decrease** | - | Not grow / rise / fall for a scalar metric; context-checked. |`

| Concept | Use | Do not use | Note |
|---|---|---|---|

## Spelling

- **One spelling variety throughout** (e.g. American: labeled, color, behavior, center,
  analyzed, modeling). Reference titles stay verbatim.
- **X-ray**, capitalized, in prose and captions.

## Numerical hedging

- **`approximately` is reserved for genuine estimates, approximate scales and approximate
  relationships,** not for a rounded computed or measured result.
- **Rounded results are written bare** at the selected precision: "The depth is 20 μm."
- **Do not hedge an exact prescribed value or a range:** "the cases span 150–350 W".
- **`approximate` is an adjective only.**
- **`about` is not used for numbers;** keep it for "regarding" or "centered on".

## Punctuation

- **No em-dashes (—) in prose.** Recast with a comma, colon, parentheses or a separate
  sentence. En dashes (–) for numeric and compound ranges (150–350 W, Figures 14–20) are
  correct.
- **Equation references are `Eq. (3)`**, including `Eq. (A.3)`; equation blocks are
  punctuated as sentences and definitions open with "Here, ...".

## Notation

- **Subfigure references carry the panel label in parentheses:** `Figure 4(a)`,
  `Figures 4(e2) and 4(f2)`.
- **Vectors and tensors bold, scalars plain italic;** vector magnitudes use bars
  ($|\mathbf{v}|$) unless a symbol is defined as a magnitude.
- **One symbol, one meaning** wherever possible; `notation.md` records meanings, units,
  locations, open issues and accepted reuse.

## Verbatim exceptions (never change)

- Reference titles: keep the original wording.
- Code identifiers and data-file or column names in figure scripts.

## Resolved decisions

Dated log of terminology decisions, newest last, each with its source and the number of
occurrences changed in the draft. Format:

- **old term → new term** (YYYY-MM-DD, author / reviewer ID) — reason; what was replaced
  and where; what was deliberately kept; enforced by the preflight or checked by hand.
