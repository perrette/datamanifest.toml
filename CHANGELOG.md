# Changelog

## v1 (schema `_META.schema = 1`)

### Breaking structural changes

- **Structural `_*` keys.** Keys beginning with `_` are reserved at the top level
  (`_META`, `_LANG`, legacy `_LOADERS`) and within a dataset table (`_LANG`). They
  are not datasets and must not be treated as such.
- **`_LANG` namespace.** Per-dataset executable bindings (`fetcher`, `loader`) now
  live under `[<dataset>._LANG.<lang>]`. Project-wide format defaults live under
  `[_LANG.<lang>.loaders]`. The flat per-dataset `julia=`/`python=`/`callable=`/
  `shell=`/`loader=` keys are deprecated.
- **`module:function` refs only.** All executable references are `module:function`
  strings. Inline code (e.g. Julia `include_string`) and `*_modules`/`*_includes`
  fields are retired; the tool puts the manifest's directory on the import path by
  convention.
- **`[_META]` header.** A v1 manifest carries `[_META]` with `schema = 1`. A file
  without `[_META]` is read as v0 (legacy flat), leniently.

### New features

- **Resolution ladders.** The fetch ladder is: own language → `shell` → (opt-in)
  peer-CLI delegation → `uri` → error. The load ladder is: own → manifest format
  default → built-in default → error. Load never delegates across a process boundary.
- **Preservation contract.** A conforming writer regenerates its own `_LANG.<self>`
  and copies every other `_LANG.*` verbatim on write, ensuring lossless round-trips
  in multi-language projects.
- **Conformance levels.** Named capabilities (`lang-read`, `lang-write`,
  `shell-fetch`, `delegation`) let partial implementations declare what they support
  and run the matching fixture-suite tests. The spec is never forked per package.
- **Peer-CLI contract.** Normative invocation interface for opt-in delegation:
  `datamanifest fetch <name> --datasets-toml <path>`.
- **Conformance fixture suite.** `tests/fixtures/` holds example manifests and
  machine-readable expected outcomes consumed as tests by all implementations.

### Deprecations (still read; should not be written by v1 tools)

- `[_LOADERS]` — replaced by `[_LANG.<lang>.loaders]`.
- Per-dataset `julia=`, `python=`, `callable=`, `shell=`, `loader=` — replaced by
  `[<dataset>._LANG.<lang>].fetcher` / `.loader`.
- `julia_modules`, `python_includes` — retired; legacy `*_includes` still accepted
  as extra import-path entries.

## v0 (no `[_META]` header)

Original flat format: one table per dataset with optional top-level `[_LOADERS]`
and per-dataset language-specific keys (`julia=`, `python=`, `callable=`, etc.).
