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

A small, normative specification for a TOML file that declares the data
dependencies of a scientific project — read by tools in different languages.

{%
  include-markdown "../README.md"
  start="<!-- intro-start -->"
  end="<!-- intro-end -->"
%}

## Get started

```toml
# datasets.toml
["jesstierney/lgmDA"]
uri     = "https://github.com/jesstierney/lgmDA/archive/refs/tags/v2.1.zip"
sha256  = "da5f85235baf7f858f1b52ed73405f5d4ed28a8f6da92e16070f86b724d8bb25"
extract = true
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
- [JSON Schemas](schemas.md) — machine-readable validation.
- [Examples](examples.md) — a full, runnable manifest.
- [Conformance fixtures](fixtures.md) — the shared test suite.
