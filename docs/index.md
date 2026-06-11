<!--
  Home page. The feature bullets are pulled straight from README.md (single
  source of truth) via the include-markdown plugin; everything else links into
  the guide.
-->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/perrette/datamanifest.toml/main/design/logo/lockup-dark.svg">
    <img src="https://raw.githubusercontent.com/perrette/datamanifest.toml/main/design/logo/lockup.svg" alt="datamanifest.toml" height="76">
  </picture>
</p>

# datamanifest.toml

A normative specification for a **manifest** — a TOML file, committed alongside a
project's code, that declares the project's data dependencies. The same file is
read by tools in different languages.

{%
  include-markdown "../README.md"
  start="<!-- intro-start -->"
  end="<!-- intro-end -->"
%}

## Get started

```toml
# datasets.toml
["jesstierney/lgmDA"]
uri      = "https://github.com/jesstierney/lgmDA/archive/refs/tags/v2.1.zip"
checksum = "sha256:da5f85235baf7f858f1b52ed73405f5d4ed28a8f6da92e16070f86b724d8bb25"
extract  = true
```

- **[Quickstart](quickstart.md)** — the manifest in one minute, declaring datasets.
- **[Language bindings](guide/bindings.md)** — `fetcher`/`loader` references, per language.
- **[Storage](guide/storage.md)** — where fetched datasets and the produced cache live.
- **[Schema spec](schema.md)** — the full normative reference.

## Guide

- [The manifest in one minute](guide/manifest.md)
- [Declaring datasets](guide/datasets.md)
- [Language bindings](guide/bindings.md)
- [Resolution: the fetch and load ladders](guide/resolution.md)
- [Storage](guide/storage.md)
- [Produced datasets and caching](guide/caching.md)
- [Maintenance (inspect)](guide/maintenance.md)
- [Cross-machine sync](guide/sync.md)
- [Conformance and versioning](guide/conformance.md)
- [Migration and deprecations](guide/migration.md)

## Reference

- [Schema specification](schema.md) — the normative `SCHEMA.md`.
- [JSON Schemas](schemas.md) — machine-readable validation, one schema file per spec tag.
- [Examples](examples.md) — a full, runnable manifest.
- [Conformance fixtures](fixtures.md) — the shared test suite: manifest files paired
  with machine-checked expected outcomes, which every implementation runs against a
  pinned spec version.
- [Roadmap](roadmap.md) · [Changelog](changelog.md) — planned work and version history.

## From the same author

A few other open-source tools I maintain.

**Scientific writing & data**

- [**texmark**](https://perrette.github.io/texmark/) — write scientific articles in Markdown and convert them to journal-ready LaTeX/PDF.
- [**papers**](https://perrette.github.io/papers/) — command-line BibTeX bibliography and PDF library manager.
- [**datamanifest**](https://perrette.github.io/datamanifest/) — declarative, reproducible dataset management. *(See also the [DataManifest.jl](https://awi-esc.github.io/DataManifest.jl/) Julia port.)*

**Speech to Text (dictate) and Text to Speech (read-aloud) tools**

- [**scribe**](https://perrette.github.io/scribe/) — speech-to-text dictation.
- [**bard**](https://perrette.github.io/bard/) — text-to-speech reader.
