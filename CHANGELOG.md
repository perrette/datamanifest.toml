# Changelog

## spec-v4 (schema `_META.schema = 1`) — unreleased

A **breaking storage-layout revision** centered on scope: everything is **project-scoped by
default**, the project owns the namespace (the library does not), and scope is no longer
guessed. The TOML *shape* is unchanged (additive keys + new resolution/layout), so
`_META.schema` stays **1**; the break is in *where bytes land on disk*, versioned on the
spec-tag axis (as spec-v3 itself was). Existing stores need migration or a clean re-fetch.

- **Datasets default flipped: empty/shared → the project name.** Fetched datasets are now
  project-isolated by default, like produced artifacts. Sequential projects — possibly built
  against different evolved spec versions — stay insulated, and a project's data is one
  `rm`/tar/rsync-able subtree. Restore sharing via `[_STORAGE._SCOPE].datasets = "<pool>"`
  (or `""`), or `scope = ""` on the individual heavy datasets.
- **Scope is the first path segment (scope-first).** Composition changes from
  `<root>/<prefix>/[<scope>/]<key>` to **`<root>/[<scope>/]<prefix>/<key>`** (produced
  likewise). A project's fetched and produced data now live together under `<root>/<scope>/`.
  Reserved prefix names `datasets`/`cached` may not be used as a scope.
- **The project owns the namespace, not `datamanifest`.** The built-in `$data`/`$cache`
  defaults now use the **project scope as the platformdirs appname** (was the literal
  `"datamanifest"`): `~/.local/share/<scope>/datasets/…` instead of
  `~/.local/share/datamanifest/<scope>/…`. For these OS-default roots the scope is the
  appname (not also a segment); for `$DATAMANIFEST_DIR` / user folders it is the leading
  segment. `datamanifest` survives only as the appname for the empty/global scope (data owned
  by no single project).
- **No global tool folder; staging is partition-local.** A tool's app-internal files (HTTP
  metadata, etc.) live under the **active scope's** root, not a separate global
  `~/.cache/datamanifest/`. And materialization stages **within the target store partition**
  (a `$scratch` dataset stages on `$scratch`) — required for an atomic rename and so
  voluminous data never transits a small `~/.cache` first. The `datamanifest` appname is the
  home of explicit `scope = ""` *data* only.
- **No guessing the scope.** The built-in default is the **project name** — Python
  `[project].name`, Julia `Project.toml` **`name`** (the name, **not** the `uuid`). If no
  project file declares a name, a tool MUST require an explicit scope (`[_STORAGE].scope` /
  `DATAMANIFEST_SCOPE` / per-item `scope`) and **error** rather than synthesize one (no path
  hash, no directory name) — mirroring the produced-dataset `cachetype` no-stable-identity
  rule, now that scope governs where every byte lands.
- **Three-level scope, one ladder.** Project-wide **`[_STORAGE].scope`** (new) → per-kind
  **`[_STORAGE._SCOPE].<kind>`** → per-item (a dataset's `scope` field / a produced `scope=`).
  Env mirrors: **`DATAMANIFEST_SCOPE`** (new) and `DATAMANIFEST_SCOPE_<KIND>`. Resolves
  **first-explicitly-set** (an explicit `""` is a real value — the global store — not
  "unset"); the resolved value drives both the path and the recorded entry. Host-specific
  scope, if needed, is just `DATAMANIFEST_SCOPE` per machine (no `_HOST` scope table). `scope`
  becomes a reserved top-level `[_STORAGE]` key.
- `manifest.v3.json` types the new `[_STORAGE].scope` and per-dataset `scope`; the storage
  conformance fixture asserts all three levels. `_META.project` is **not** introduced — the
  project name only ever feeds the scope default, so `[_STORAGE].scope` is its sole home.

## spec-v3.7 (schema `_META.schema = 1`)

Reconcile the produced-dataset / cache model with the implementation: the `cached.toml` index
becomes a self-healing, **nested schema-2** registry, and the produced-dataset identity model
(cachetype / scope / conflicts / default format) is formalized cross-language. The manifest
`_META.schema` stays **1**; `cached.toml`'s own `_META.schema` goes **1 → 2** (schema 1 is
still read, always rewritten as 2).

1. **`cached.toml` field `project` → `scope`.** The declarable knob is named for what it sets
   — the scope partition — not for the project id that merely *defaults* it. There is no
   per-dataset `project`; `scope` is recorded per recipe (parallel to a dataset's `store`).

2. **`cached.toml` index lifecycle: self-healing transparency view.** The index is reframed
   from a write-once log to a per-machine transparency view that **converges to the artifacts
   present on disk**. A tool registers on produce (miss), **registers-if-missing on cache
   hit** (so a deleted `cached.toml` repopulates as datasets are accessed; the steady-state
   check is read-only, off the hot path), and **prunes a stale entry** when it observes the
   artifact is gone (single ops reconcile their own entry, `inspect` the whole file). Pruning
   a dangling pointer is bookkeeping, **not** the "never auto-delete data" rule (which
   protects present bytes). On-disk `config.toml` stays the cache-validity authority; index
   mutations use the produce atomic-write+lock and are idempotent. `metadata.toml` provenance
   remains **write-if-absent** (hits don't re-stamp it) — only the index re-registers.

3. **Produced-dataset identity model (cross-language).** (i) **`cachetype` default +
   stable-name rule:** absent an explicit `cachetype`, it derives from the producing
   function's canonical *importable* name (so it coincides with the entry `ref`);
   unique-per-function is the right default (mixing unrelated caches is the worst failure),
   with the accepted rename-orphans consequence and `version` as the deliberate-bust tool; and
   when the function has **no stable importable identity** (script / REPL / eval / notebook) a
   tool MUST require an explicit `cachetype`, never synthesize one (the generalized pickle
   constraint). (ii) **`scope` is ownership, not disambiguation:** resolved from the *caller's*
   project, isolation-by-default / share-by-opt-in; never affects hit validity. (iii)
   **`(cachetype, version)` conflict guard:** a tool SHOULD raise when two distinct functions
   claim the same pair *live in one process at once* (same-process/same-time only; `scope`
   irrelevant). Transient/local/anonymous functions are exempt; *when and how* to detect is
   left to each implementer (the earliest practical point for the language — import time in
   Python; trickier under Julia's precompilation, and possibly infeasible there), hence a
   SHOULD with no fixed mechanism. (iv) **Format coexists under one hash:** `format` is not a
   hash input, so several formats share a `<cachetype>/[<version>/]<hash>` dir; a hit requires
   the `data.<ext>` for the *requested* format, else recompute. (v) **Per-language default
   format** (RECOMMENDED, not normative): `pickle` (Python) / `jld2` (Julia), each with a
   built-in **saver** + loader, so a format-less produced dataset round-trips.

4. **`cached.toml` schema 2 (nested) + scope ladder + centralized `[_STORAGE]`.** (a) **Schema
   2 is nested:** `cached.toml` becomes a `produced` array of recipe tables keyed by
   `(scope, cachetype, version)`, each with one `instances` entry per produced variation
   (parameter `hash` + the `params` key table). Registering **accumulates** instances (so a
   recipe's many parameterizations all stay reachable instead of orphaning); recipe-level
   `ref`/`format`/`store` are refreshed on register and on hit-if-drifted (not hash inputs).
   Schema 1 (flat, one `hash`, no params) is still **read** (→ one-instance recipe) but
   rewritten as schema 2. (b) **Scope resolution ladder:** a producing-call `scope=` override
   (highest) → `DATAMANIFEST_SCOPE_CACHED` → `[_STORAGE._SCOPE].cached` → project id;
   `scope=""` is one global unscoped store; the scope is resolved **once** and drives both the
   path and the recorded entry (no divergence), and reachability is the full
   `(scope, cachetype, version, hash)` tuple. (c) **Centralized storage:** a produced artifact
   reads the nearest manifest's `[_STORAGE]` (a plain TOML read, no fetch layer), so produced
   and fetched data share one storage configuration; env overrides win, an explicit config
   wins over the manifest. The `cached.v3.json` schema now validates the nested schema-2 form.

## spec-v3.6 (schema `_META.schema = 1`)

Replace the spec-v3.4 "warn and fall through" rule for language-implicit bindings with
**fail-loud** semantics.

- A binding that is *present* for the running language — a bare `fetcher`/`loader`, or an
  explicit `[<ds>._LANG.<self>]` — that **fails to resolve is an error**; one that resolves
  and then raises **propagates**. No silent fall-through to a different loader/fetcher
  (which could hand a program wrong-shaped data behind only a warning, especially for a
  loader falling through to the format default).
- The fetch/load ladders still fall through only for bindings that are **absent** for the
  running language (e.g. another language's `_LANG.<other>` fetcher), unchanged.
- Multi-language manifests use explicit `[<ds>._LANG.<lang>]` bindings (absent — and so
  correctly skipped — in other languages); bare bindings are the single-language form.
- **No `--lenient` flag.** A tool-wide best-effort mode (e.g. "fetch all, skip failures")
  is a separate, broader concern, intentionally not introduced by this rule.
- Docs/semantics only; no schema change. `_META.schema` stays **1**.

## spec-v3.5 (schema `_META.schema = 1`)

Move the shell fetcher out of the `_LANG` namespace. `shell` is **language-agnostic** (the
same command for every tool), so it is now a bare dataset field — a command template run as
a subprocess — rather than a pseudo-language under `[<ds>._LANG.shell]`.

- `shell = "<command template>"` on the dataset is the canonical form; same `$var`
  substitutions as before; fetcher only.
- The legacy `[<ds>._LANG.shell].fetcher` is still read and preserved verbatim.
- `schemas/manifest.v3.json`: datasets gain a `shell` string field.
- The bare `julia=`/`python=`/`callable=` flat fields stay **legacy** (they historically
  held inline code, which v1 forbids) — tolerated on read and rewritten by `migrate`; not a
  forward form. The single-language convenience is already covered by bare `fetcher`.
- Reconciled the Deprecations section with spec-v3.4: bare `fetcher`/`loader`
  (language-implicit), bare `shell` (language-agnostic), and `[_LOADERS]` are supported
  forms, not deprecated.
- `_META.schema` stays **1**: additive field + a relocation with legacy tolerance;
  spec-tag axis.

## spec-v3.4 (schema `_META.schema = 1`)

Language-implicit ("bare") bindings, so a single-language project can skip the
`[<dataset>._LANG.<lang>]` ceremony. A dataset MAY carry a bare `fetcher`/`loader`
directly, and a top-level `[_LOADERS]` MAY carry a bare `format → binding` map; a reading
tool interprets these as bindings in **its own language**.

- **Precedence:** an explicit `[<dataset>._LANG.<self>]` binding (and
  `[_LANG.<self>.loaders]`) overrides the bare one.
- **Tolerant:** a bare binding that does not resolve in the running language **warns and
  falls through** the ladder — never a hard error (a shared single-author manifest will
  legitimately fail in the other language).
- **Round-trip:** a writer preserves a bare binding verbatim — it never promotes it into
  `_LANG.<self>`; tools write `_LANG.<self>` only for bindings they generate.
- `[_LOADERS]` is reclassified from deprecated back-compat to the **tolerated**
  language-implicit counterpart of `[_LANG.<self>.loaders]`.
- `schemas/manifest.v3.json`: datasets gain `fetcher`/`loader` (binding-typed); `_LOADERS`
  is a `format → binding` map.
- `_META.schema` stays **1**: additive (new optional fields + a tolerant read rule);
  versioned on the spec-tag axis.

## spec-v3.3 (schema `_META.schema = 1`)

Harmonize executable bindings into **one** form, used identically at every site. A
**binding** — a per-dataset `fetcher`/`loader` and now every entry in a
`[_LANG.<lang>.loaders]` format map — is either a `module:function` string or a
`{ ref, args, kwargs }` table.

- The **string is an alias** for the ref-only table (`"M:f"` ≡ `{ ref = "M:f" }`); a
  reader accepts either form anywhere a binding is allowed.
- **Writer rule:** a binding with no `args` and no `kwargs` MUST be written as the string;
  the table form is used only when it carries arguments.
- **Call semantics follow the arguments:** none → the tool's conventional call (path
  injected for a loader, fetch context for a fetcher); `args`/`kwargs` → an explicit
  `ref(*args; kwargs...)` with `$var` substitution and no auto-injection.
- `schemas/manifest.v3.json`: `[_LANG.<lang>.loaders]` values now accept the table form
  (were string-only), via the shared `binding` definition. `shell.fetcher` stays a
  command-template string (not a `module:function` binding).
- `_META.schema` stays **1**: the TOML shape is back-compatible (a widening plus a writer
  rule); versioned on the spec-tag axis.

## spec-v3.2 (schema `_META.schema = 1`)

Fix the `inspect` **`last-access`** rule. The previous wording ("a tool SHOULD touch an
entry's access time on read") invited a write-on-read implementation — rewriting a
sidecar/index `.toml` on every read — which contends with the produce `.lock`,
serializes concurrent readers, and puts I/O on the lock-free hot path, all for an
advisory value.

- `last-access` is now **filesystem-derived** and **never written on read**: a tool
  reads it from `stat` (access time, with modification-time / `created` fallback) at
  inspect time, and **MUST NOT** rewrite any sidecar/index/`.toml` to record access.
- The signal is explicitly coarse and **may be unknown** (`relatime`, `noatime`,
  network/read-only filesystems); `created` (stamped once at produce time) is the
  always-available age signal.
- `_META.schema` stays **1**: no data-model change; this is a behavioural correction on
  the spec-tag axis.

## spec-v3.1 (schema `_META.schema = 1`)

Refinement of the parameter-hash rules: **finite floats are now permitted as hash
inputs.** A float serializes through the same canonical-JSON projection as every other
value — the Python reference `json.dumps` form is normative (`1.0` → `1.0`, `0.1` →
`0.1`) and a non-Python tool MUST reproduce it byte-for-byte. `NaN` / `±Inf` remain
disallowed (no JSON representation) and nulls remain disallowed (an absent parameter is
omitted, not encoded as `null`). Passing a float-valued knob as a string is still
allowed and remains the most cross-tool-stable option.

- `SCHEMA.md` §Parameter-hash keying: the value-restriction now lists finite floats and
  pins their canonical form.
- `schemas/config-sidecar.v3.json`: `hashValue` now admits `number`.
- New conformance fixture `config_sidecar_float` pins a float reference vector
  (`{"grid":"5x5","sigma":0.5,"threshold":1.0}` → SHA-256 `acc37c63…`).
- `_META.schema` stays **1**: the data-model shape is unchanged; this is a hash-input
  validation widening on the spec-tag axis (the v2 → v2.1 convention).

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
