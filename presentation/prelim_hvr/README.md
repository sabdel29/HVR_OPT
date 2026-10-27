# HVR_OPT preliminary-exam deck

Self-contained Reveal.js deck explaining the project from first principles, plus a
deterministically rendered PDF.

| file | what it is |
|---|---|
| `index.html` | the interactive deck (Reveal.js, speaker notes with `S`) |
| `print.html` | a static one-page-per-slide render used only for the PDF |
| `HVR_OPT_Prelim.pdf` | 16:9, exactly one page per slide |
| `theme.css` | typography, semantic status colours |
| `figs/*.svg` | charts, all generated from repository artifacts |
| `SPEAKER_NOTES.md` | notes extracted from the deck source |
| `vendor/reveal.js` | vendored Reveal.js 5.1.0 (no `node_modules`) |

## Reproduce

```bash
python scripts/prelim_make_figs.py      # charts  -> presentation/prelim_hvr/figs
python scripts/prelim_build_deck.py     # index.html + print.html + SPEAKER_NOTES.md
python scripts/prelim_qa_slides.py      # QA: renders the PDF and checks every page
```

`prelim_qa_slides.py` produces the PDF with headless Chrome and fails if the page
count does not equal the slide count.

## Why the PDF comes from `print.html`, not Reveal's `?print-pdf`

Reveal's own print mode lays the deck out at runtime. Headless Chrome snapshots
before that settles, and it produced a **single blank page**. `print.html` is static —
one `div.pg` of exactly 1600×900 px per slide with `page-break-after: always`, and no
JavaScript at all — so the page count cannot depend on timing. Both files are built
from the same slide list, so they cannot drift.

## Nothing in the deck is hand-typed

Every quantitative value and every chart is read from the repository artifacts at
build time (`research/phase0nai/`, `research/phase0naj/`, `research/phase0nak/`,
`research/phase0nw/physical_gates.json`, `research/phase0nah/`). Rebuild the artifacts
and the deck follows. This is deliberate: a slide holding its own copy of a
phase-dependent number goes stale independently of the artifact it came from.
