# Changelog

## spec-v3 (schema `_META.schema = 1`)

A breaking **behavioral** revision of the storage and cache model. `_META.schema` stays
**1** — the TOML *shape* is back-compatible (changes are resolution semantics + additive
structural tables); the break is in *resolution* and *layout*, which is what the spec-tag
axis versions. Nothing implemented spec-v2 storage yet, so practical migration is nil.

1. **Storage: top-level folder roots + layer-applied prefixes + scope.** Folder variables
   (`$data`/`$cache`/`$repo`/user-defined) are now **bare top-level roots** (`$data` =
   `user_data_dir`, not `…/Datasets`). The lowercase content prefixes **`datasets/`** (fetch)
   and **`cached/`** (produce) are applied by the consuming layer, configurable via
   `[_STORAGE._PREFIX]` / `DATAMANIFEST_PREFIX_*`. A new **`scope`** partition segment
   (`[_STORAGE._SCOPE]` / `DATAMANIFEST_SCOPE_*`) controls sharing — empty for `datasets`
   (shared), the **project id** for `cached` (project-isolated). New **`DATAMANIFEST_DIR`**
   application base. **Breaking:** `[_STORAGE]` folder values drop their `/datasets` suffixes;
   fetched paths become `<root>/datasets/[scope/]<key>`. `_PROFILE` is **shelved** (reserved,
   preserved verbatim); `_HOST` kept.

2. **Produced datasets: composition + recipe `version`.** A produced artifact composes its
   path via folder / `cached` prefix / scope: `<folder>/cached/<project-id>/<cachetype>/
   [<version>/]<hash>`. The cached scope defaults to the **project id** (declared
   `[_META].project` → `pyproject.toml`/`Project.toml` name/uuid → path hash). New optional
   **`version`** path segment — a human-set recipe/code version (not in the parameter hash)
   that prevents a stale cross-branch/clone hit.

3. **`inspect` (renamed from `cache-gc`): user-driven maintenance, no automatic collector.**
   Replaces root-reachability GC (which had a read-only-consumer hole) with a field-oriented
   store listing: enumerate objects (datasets + cached) by `kind`, `key`/`hash`, `location`,
   `referenced`/orphan, `scope`, `format`, `size`, `created`, `last-access`; filter; and act
   on an explicit selection (`delete`, optional `move`). Never deletes by default;
   liveness/`last-access` are advisory. Reference CLI: `datamanifest list … --delete`.

4. **`sync`: cross-machine transfer.** New optional capability — `push`/`pull` a stored
   object between two stores over SSH/rsync, addressed by `name`/`alias`/`doi` (fetched) or
   `cachetype[/version]/hash` (produced). Each end resolves its own store from env + `_HOST`
   (`$repo` excluded); symmetric; writes no manifest (objects arrive as orphans); integrity
   via rsync; idempotent.

## spec-v2.1 (schema `_META.schema = 1`)

Prose-only correction on the spec-document axis — no `_META.schema` bump, no on-disk
format change, fixtures unaffected.

- **Produce-or-load is a *layer*, not necessarily a separate *package*.** spec-v2 baked a
  distribution decision into the format spec ("lives in a companion package that depends
  on datamanifest"). spec-v2.1 separates the two concerns it conflated: it keeps the
  normative **capability boundary** (`cache-produce` / `cache-gc` are never declared by the
  core fetch capability; the core keeps no GC and no disposability) and **relaxes the
  packaging mandate** — shipping the layer as a separate package or as an optional module
  of the same package is now explicitly the implementation's choice. Rationale and the
  per-language packaging asymmetry: `design/package-architecture.md`.

## spec-v2 (schema `_META.schema = 1`)

Two changes, both on the spec-document axis (no `_META.schema` bump — see
`design/storage-model-revision.md`):

1. **Storage model revision.** Stores-with-policy become a `$`-folder-variable
   namespace — *locations only, no lifetime policy in the core*. This **revises** the
   spec-v1.1 `store`/`[_STORAGE]` semantics (the `store` value-grammar changes; bare
   names are hard-migrated to `$`-form), gated by the `storage` capability.
2. **Produce-or-load as a companion layer.** Promotes the `@cached` design
   (`design/caching-and-dataset-storage.md` §6.D) as a cross-tool **format** spec, but
   the layer itself lives in a **companion package** (one per language), not the core.
   Additive over a `datasets.toml`: **no new hand-authored field**, no schema change; a
   produced dataset is recorded only in machine-generated sidecars + the `cached.toml`
   index (each carrying its own `_META.schema = 1`). `cache-produce` / `cache-gc` are
   declared by the companion, not the core; the core keeps no GC and no disposability.

### Storage model revision (`storage`)

- **Folders are a `$`-variable namespace.** `[_STORAGE]` holds **folder variables** —
  built-in `$data` / `$cache` / `$repo` plus any user-defined key (`scratch = "…"` →
  `$scratch`) — and the new project-wide `default` selector. Built-ins resolve to
  dataset-root locations: `$data` = `user_data_dir("datamanifest")/Datasets`, `$cache` =
  `user_cache_dir("datamanifest")/Datasets`, `$repo` = `<project_root>/datasets` (the exact
  v1.1 on-disk paths — no re-download).
- **Two field kinds.** *Selectors* (`default`, a dataset's `store`) are `$`-folder
  references, optionally with a sub-path (`$cache/sub`), keying the dataset at
  `<resolved-folder>[/sub]/<key>`; `store` defaults to `default`, `default` to `$data`.
  *Path expressions* (`[_STORAGE]` values, `local_path`) are full paths interpolating
  `$`-folders, `$USER`/env, and `~`.
- **`$`-references only (hard migration).** Bare `store = "data"` (the v1.1 form) is no
  longer valid; a spec-v2 `storage` tool MUST reject it. Bare keys appear only as folder
  *definitions* in `[_STORAGE]`.
- **One host-aware resolution ladder for every variable** (built-in and user-defined):
  `DATAMANIFEST_<NAME>_DIR` env → `_PROFILE.<name>` → `_HOST.<glob>.<name>` →
  `[_STORAGE].<name>` → built-in default. Host-specificity lives entirely in resolving
  the variable — there is **no** per-dataset `_HOST` map; a machine-specific exact path is
  a `local_path` interpolating a host-resolved variable.
- **`mount` removed from the model.** A locations-only model has no home for
  never-materialized in-place access; spec-v2 defines no `mount` capability. In-place
  access is deferred to a future revision — see `ROADMAP.md`.

### Produce-or-load (companion-layer) features

- **Produced datasets.** A dataset whose bytes come from running a project
  function rather than a `uri`. It has **no `datasets.toml` entry** — it
  originates from the `@cached` surface and is recorded only in machine-generated
  files. `cachetype` is not a `datasets.toml` field; it is a namespace that
  appears only in those records (the `cached.toml` entry, the `config.toml`
  `_META`, and the on-disk path). Defaults to `store = "$cache"` and is keyed by a
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
- **Garbage collection (`cache-gc`).** The companion's `gc` is a root-reachability
  collector: roots are still-existing `datasets.toml` (incl. `$cache`-folder
  entries) and `cached.toml` files, discovered via a depot-level usage log. An
  artifact under `$cache` is collectable iff no live root references its key and it is
  older than a grace age; the per-artifact back-pointer is audit-only. The **core keeps
  no GC**.
- **New capabilities.** `cache-produce` (produced datasets + sidecars) and
  `cache-gc` (the `cached.toml` index + usage log + `gc`) — both declared by the
  **companion package**, not the core fetch tool.

### Cross-language fetch (rung 3) clarified

- **`delegate` is now a defined field** (per-dataset bool) plus the per-run `--delegate`
  flag, and a brief `SCHEMA.md` §Cross-language fetch frames the rung as the **rare** case
  (a dataset whose bytes need a fetcher in another language, with no native/`shell`/`uri`).
- **Mechanism left to the implementation:** a tool may call the other language's runtime
  directly or fall back to the **Python CLI** (the reference implementation, which aims to
  cover every language). Fall-through to `uri` when the toolchain is absent. Does not
  extend to produced (`@cached`) datasets.

### Explicitly deferred

- The `@cached` macro/decorator **API** is per-language, not normative (only the
  on-disk formats + GC rule are).
- Produced-artifact serialization format is a per-tool/per-`format` choice (no
  cross-language loading implied).
- Cloud / `fsspec` / CAS backends remain optional per-language extras, not a spec
  contract. In-place / mounted access (the former `mount` store) is deferred past
  spec-v2 — see `ROADMAP.md`.
- Where the companion package keeps its own app-internal state is a companion concern,
  not part of this cross-tool format spec.

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
