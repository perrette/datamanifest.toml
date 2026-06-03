# Logo

The mark is **`drive-stack`** — three stacked data drives. Open **`preview.html`** in a
browser to see it at 96 / 32 / 16 px on light and dark, alongside the earlier exploration.

## The chosen mark

| File | Use | Ink |
|---|---|---|
| `drive-stack.svg` | light backgrounds (README default) | dark blue `#2f4d7a` |
| `drive-stack-dark.svg` | dark backgrounds | white `#ffffff` |
| `drive-stack-light.svg` | light backgrounds, mono alt | black `#14181f` |
| `lockup.svg` | horizontal mark + wordmark, light bg | dark blue + amber `[ ]` |
| `lockup-dark.svg` | horizontal mark + wordmark, dark bg | white + amber `[ ]` |

The faceplate lines are part of the drive; there is no activity-LED "knob" (it carried no
meaning). The drives' detail is **knocked out** in the mono variants, so the page
background shows through — one ink, any surface.

Shared palette:

| Role | Hex |
|---|---|
| Drive body (dark blue) | `#2f4d7a` |
| Faceplate lines (ink) | `#1c3050` |
| Accent — TOML brackets (lockup) | `#F0A92B` |
| Muted tagline | `#7d8aa0` |

## Earlier exploration (kept for reference)

- `box-labeled.svg` / `box-plain.svg` — package / archive direction.
- `drive.svg` — a single hard drive.
- `rack.svg` — a server rack.

## Using it in a README

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="design/logo/drive-stack-dark.svg">
    <img src="design/logo/drive-stack.svg" alt="datamanifest" height="96">
  </picture>
</p>
```

Swap to `lockup.svg` / `lockup-dark.svg` for the mark-plus-wordmark form.

## Notes / next steps

- The wordmark uses a system sans stack (`Inter`/Helvetica/Arial). For a portable mark
  that renders identically everywhere (no font dependency), the final pick should have its
  wordmark **converted to paths**.
- Once you choose an icon, I can emit a square `icon.svg`, a 16 px favicon, and a
  monochrome (single-color) variant for places that need one ink.
