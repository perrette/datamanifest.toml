# Logo candidates

Open **`preview.html`** in a browser to see every mark at 96 / 32 / 16 px on light and
dark backgrounds. Shared palette so the brand is identical across all implementations:

| Role | Hex |
|---|---|
| Box / device body | `#2f4d7a` |
| Lighter face / highlight | `#3a5d92` |
| Edge / vents (ink) | `#1c3050` |
| Accent — TOML brackets, activity LED | `#F0A92B` |
| Label paper | `#FBF7EE` |
| Muted tagline | `#7d8aa0` |

## Candidates

**Box / archive family** — the literal shipping-manifest metaphor.
- `box-labeled.svg` — package with a cream label carrying `[ ]` + manifest rows.
- `box-plain.svg` — same box, no paper label; the amber `[ ]` is stamped on the crate.

**Hard-drive / data-center family.**
- `drive.svg` — a single hard drive (vents + amber activity LED).
- `drive-stack.svg` — three stacked drives, a small data array.
- `rack.svg` — a server rack, the most "data-center" read.

**`lockup.svg`** — the horizontal README form: icon + `[datamanifest]` wordmark
(brackets in amber) and an optional tagline. The icon is `drive-stack` here but is a
drop-in `<g>` you can swap for any mark above.

## Using it in a README

```md
<p align="center"><img src="design/logo/lockup.svg" alt="datamanifest" height="80"></p>
```

Light/dark variants (if you add a `*-dark.svg`):

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="design/logo/lockup-dark.svg">
  <img src="design/logo/lockup.svg" alt="datamanifest" height="80">
</picture>
```

## Notes / next steps

- The wordmark uses a system sans stack (`Inter`/Helvetica/Arial). For a portable mark
  that renders identically everywhere (no font dependency), the final pick should have its
  wordmark **converted to paths**.
- Once you choose an icon, I can emit a square `icon.svg`, a 16 px favicon, and a
  monochrome (single-color) variant for places that need one ink.
