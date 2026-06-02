# Changelog

## spec-v2 (schema `_META.schema = 1`, additive)

Promotes the produce-or-load (`@cached`) design
(`design/caching-and-dataset-storage.md` §6.D) into the normative spec. Additive:
it adds **no field to the hand-authored `datasets.toml`** and does not change its
`_META.schema` (still **1**). A produced dataset reuses the existing engine —
storage model, safe-materialization, loaders — but is **not declared in
`datasets.toml`**; its only on-disk record is the machine-generated sidecars and
the `cached.toml` index, each carrying its own `_META.schema = 1`. Gated by two
independent capabilities so a tool may ship neither, one, or both.

### New features

- **Produced datasets.** A dataset whose bytes come from running a project
  function rather than a `uri`. It has **no `datasets.toml` entry** — it
  originates from the `@cached` surface and is recorded only in machine-generated
  files. `cachetype` is not a `datasets.toml` field; it is a namespace that
  appears only in those records (the `cached.toml` entry, the `config.toml`
  `_META`, and the on-disk path). Defaults to `store = "cache"` and is keyed by a
  **parameter hash** rather than host/path/version. Unifies external-vs-produced
  into one "recipe + key + store + policy" object — the only new axis is
  parameter-hash keying.
- **Parameter-hash keying.** A produced dataset's `key` is `<cachetype>/<hash>`,
  where the hash is the SHA-256 of the **canonical JSON** (JCS, RFC 8785) of its
  hash-affecting parameters — the producing function's **keyword parameters**
  (produced datasets are **keyword-only**; positional `args` have no stable
  name→value identity to hash). A three-way parameter split is normative:
  hash-affecting params (in the hash, in `config.toml`) vs `_`-prefixed runtime
  knobs (excluded) vs audit-only extras (in `metadata.toml`).
- **Self-describing sidecars (`cache-produce`).** `config.toml` (the re-hashable
  key table + `_META.cachetype`/`hash`) and `metadata.toml` (provenance: created,
  tool+version, host, user, `[git]`, `[origin]`) sit next to each produced
  artifact, materialized via the v1.1 safe-materialization primitive.
- **`cached.toml` index (`cache-gc`).** A sibling `Manifest.toml`-analogue listing
  produced datasets by portable key (`cachetype` + `hash`), kept out of the
  hand-authored `datasets.toml`. Gitignored per-machine by default; opt-in commit
  for shared reproducibility.
- **Garbage collection (`cache-gc`).** `datamanifest gc` is a root-reachability
  collector: roots are still-existing `datasets.toml` (incl. `cache`-store
  entries) and `cached.toml` files, discovered via a depot-level usage log. An
  artifact is collectable iff no live root references its key and it is older than
  a grace age; the per-artifact back-pointer is audit-only.
- **New capabilities.** `cache-produce` (produced datasets + sidecars) and
  `cache-gc` (the `cached.toml` index + usage log + `gc`).

### Explicitly deferred

- The `@cached` macro/decorator **API** is per-language, not normative (only the
  on-disk formats + GC rule are).
- Produced-artifact serialization format is a per-tool/per-`format` choice (no
  cross-language loading implied).
- `mount` store mechanics and cloud/`fsspec` backends remain reserved/deferred.

## spec-v1.1 (schema `_META.schema = 1`, additive)

Additive storage model — no schema bump (old readers preserve the new field/table
verbatim), tracked on the spec-document axis. New capabilities gate it.

### New features

- **Storage model (`store` field + `[_STORAGE]`).** A dataset is materialized into a
  named **store**: `data` (persistent, default), `cache` (disposable), `repo`
  (project-tracked), or `mount` (transient, accessed in place). Stores have two policy
  axes — *materialization* (`local`/`mount`) and *retention*. The optional `[_STORAGE]`
  structural table configures each store's root, with `_HOST` (hostname glob/regex) and
  `_PROFILE` override sub-tables.
- **Language-independent default locations.** Default `data`/`cache` roots follow the
  `platformdirs` `user_data_dir`/`user_cache_dir` conventions and are normative, so Python
  and Julia resolve the same dataset to the **same path** (at minimum for reading) and
  genuinely share a store. Read resolution MUST cover the canonical locations.
- **New capabilities.** `storage` (honor `store` + `[_STORAGE]` resolution) and `mount`
  (the transient mounted store). Tools without `storage` preserve `store`/`[_STORAGE]`
  verbatim. `mount` mechanics are not yet specified; tools should not advertise it yet.
- **Canonical key ordering.** All keys at every level are emitted in Unicode
  code-point lexicographic order (no `_LOADERS`/`_META`-first special case), so a logical
  manifest serializes to byte-identical output across tools. New `byte-identity`
  capability + a planned cross-tool fixture guard it. (Previously each tool sorted
  differently — Python by dataclass field order, Julia alphabetically — causing churn.)
- **Parameterized bindings.** A per-dataset `fetcher`/`loader` may be a
  `{ ref, args, kwargs }` table instead of a bare string, so one function is reused across
  datasets that differ only in arguments. `args` is an ordered positional array, `kwargs`
  a keyword table — both plain data, never code — and the tool calls `ref(*args; kwargs)`
  explicitly (no auto-injection), with shell-style `$var` substitution in string values.
  Values with no TOML type (e.g. a Julia `Symbol`) are written as plain strings. New
  `binding-args` capability; a tool that runs the language but lacks it MUST error on
  `args`/`kwargs` rather than ignore them.
- **Normative resolution & concurrency.** Fixed read order (`repo`→`data`→`cache`),
  shared env-var names (`DATAMANIFEST_DATA_DIR` / `_CACHE_DIR` / `DATAMANIFEST_PROFILE`)
  and precedence, and a cross-tool concurrency convention (atomic publish, `.complete`
  marker, `.lock` pidfile) so peer tools share a store safely. `platformdirs` is the
  reference for default paths. `sha256` is verified at fetch, not re-verified on load.

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
