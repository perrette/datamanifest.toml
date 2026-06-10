<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="design/logo/lockup-dark.svg">
    <img src="design/logo/lockup.svg" alt="datamanifest.toml" height="76">
  </picture>
</p>

[![docs](https://img.shields.io/badge/docs-perrette.github.io%2Fdatamanifest.toml-blue)](https://perrette.github.io/datamanifest.toml/)
[![spec](https://img.shields.io/badge/spec-spec--v4-informational)](https://perrette.github.io/datamanifest.toml/schema/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A small, normative specification for the **`datamanifest.toml`** manifest format — a
TOML file that declares the data dependencies of a scientific project (each dataset's
source URI, checksum, version, format, and how to fetch and load it).

One `datasets.toml` is read by tools in different languages — today
[Python](https://github.com/perrette/datamanifest) and
[Julia](https://github.com/awi-esc/DataManifest.jl) — and covers fetching (download,
checksum, extract, load), portable storage, per-language bindings, and an optional
produce-or-load cache layer. The data model is `_META.schema = 1`; behavioural revisions
are tracked by spec tags (currently `spec-v4`).

<!-- intro-start -->
- **One manifest, many languages.** A single `datasets.toml` declares each dataset's
  source, checksum, format, and how to fetch and load it — and the same file is read
  unchanged by tools in [Python](https://github.com/perrette/datamanifest) and
  [Julia](https://github.com/awi-esc/DataManifest.jl).
- **Fetch, verify, extract, load.** A tool downloads the dataset, verifies its checksum,
  unpacks the archive, and hands your code the local path — re-fetching only when it's
  missing. Add a `format` and it loads the data into a native object too.
- **Portable, local-by-default storage.** Fetched datasets and produced artifacts live in
  repo-relative folders by default, and can be centralized per host via
  `[_STORAGE._HOST]` glob rules without touching the rest of the manifest.
- **Produce-or-load caching.** An optional companion layer keys produced artifacts by a
  hash of their parameters, so derived data is rebuilt only when its inputs change.
- **Normative and conformance-tested.** The prose spec is the source of truth, backed by
  machine-readable JSON Schemas and a shared fixture suite both implementations run.
<!-- intro-end -->

## 📖 Documentation

Full documentation lives at **<https://perrette.github.io/datamanifest.toml/>**:

- [Quickstart](https://perrette.github.io/datamanifest.toml/quickstart/)
- Guide: [the manifest in one minute](https://perrette.github.io/datamanifest.toml/guide/manifest/),
  [declaring datasets](https://perrette.github.io/datamanifest.toml/guide/datasets/),
  [language bindings](https://perrette.github.io/datamanifest.toml/guide/bindings/),
  [resolution](https://perrette.github.io/datamanifest.toml/guide/resolution/),
  [storage](https://perrette.github.io/datamanifest.toml/guide/storage/),
  [caching](https://perrette.github.io/datamanifest.toml/guide/caching/),
  [maintenance](https://perrette.github.io/datamanifest.toml/guide/maintenance/),
  [sync](https://perrette.github.io/datamanifest.toml/guide/sync/),
  [conformance](https://perrette.github.io/datamanifest.toml/guide/conformance/),
  [migration](https://perrette.github.io/datamanifest.toml/guide/migration/)
- [Schema specification](https://perrette.github.io/datamanifest.toml/schema/) (the normative `SCHEMA.md`)
- [JSON Schemas](https://perrette.github.io/datamanifest.toml/schemas/) ·
  [Examples](https://perrette.github.io/datamanifest.toml/examples/) ·
  [Conformance fixtures](https://perrette.github.io/datamanifest.toml/fixtures/)
- [Roadmap](https://perrette.github.io/datamanifest.toml/roadmap/) ·
  [Changelog](https://perrette.github.io/datamanifest.toml/changelog/)

## Quick look

Declare a dataset — its source and checksum — in `datasets.toml`:

```toml
["jesstierney/lgmDA"]
uri      = "https://github.com/jesstierney/lgmDA/archive/refs/tags/v2.1.zip"
checksum = "sha256:da5f85235baf7f858f1b52ed73405f5d4ed28a8f6da92e16070f86b724d8bb25"
extract  = true
```

A tool downloads it, verifies the checksum, unpacks the archive, and hands your code the
local path — re-fetching only when it's missing. Add a `format` and it loads the data into a
native object too; the same file is read unchanged by tools in different languages. The full,
runnable manifest is at
[`examples/datasets.toml`](https://github.com/perrette/datamanifest.toml/blob/main/examples/datasets.toml),
and the [quickstart](https://perrette.github.io/datamanifest.toml/quickstart/) walks through a
fuller example.

## Implementations

The Python package [`perrette/datamanifest`](https://github.com/perrette/datamanifest) is
the **reference implementation** and ships the `datamanifest` command-line tool. A Julia
port, [`DataManifest.jl`](https://github.com/awi-esc/DataManifest.jl), tracks the same spec
and shares the conformance fixtures
([`tests/fixtures/`](https://github.com/perrette/datamanifest.toml/tree/main/tests/fixtures)),
so both read the same `datamanifest.toml`.

| Language | Repository | Description |
|---|---|---|
| Python *(reference)* | [perrette/datamanifest](https://github.com/perrette/datamanifest) | **The reference implementation.** Download, verify, extract, and load datasets declared in a manifest; uses entry-point loader references instead of inline code execution. Provides the **`datamanifest` command-line tool**. |
| Julia | [awi-esc/DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) | Download, verify, extract, and load datasets declared in a manifest, with a Julia-native API. |

## From the same author

A few other open-source tools I maintain.

**Scientific writing & data**

- [**texmark**](https://perrette.github.io/texmark/) — write scientific articles in Markdown and convert them to journal-ready LaTeX/PDF.
- [**papers**](https://perrette.github.io/papers/) — command-line BibTeX bibliography and PDF library manager.
- [**datamanifest**](https://perrette.github.io/datamanifest/) — declarative, reproducible dataset management. *(See also the [DataManifest.jl](https://awi-esc.github.io/DataManifest.jl/) Julia port.)*

**Speech to Text (dictate) and Text to Speech (read-aloud) tools**

- [**scribe**](https://perrette.github.io/scribe/) — speech-to-text dictation.
- [**bard**](https://perrette.github.io/bard/) — text-to-speech reader.

## License

MIT — see [LICENSE](LICENSE).
