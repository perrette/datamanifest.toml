# Changelog

## spec-v5.7 (schema `_META.schema = 1`)

**No git-worktree special treatment.** Behavioural only — no schema change, no manifest
change, no new fixtures.

- **The linked-`git worktree` config and state fallbacks are retracted** (reverting
  spec-v5.1 and the spec-v5.4 config extension). A tool no longer resolves a worktree's
  missing `.datamanifest/config.toml` or `.datamanifest/state.toml` against the main
  checkout: lookups are strictly local to the project directory, with no `git` probing.
  Worktree layout is left entirely to the user — symlink `.datamanifest/` (or individual
  files) into a worktree to share config or inventory, as suits the project. This keeps
  path resolution simple to reason about and uniform across checkouts and non-git
  directories alike.

## spec-v5.6 (schema `_META.schema = 1`)

**Manifest file naming and discovery.** Behavioural only — no schema change, no manifest
change, no new fixtures.

- **`datamanifest.toml` is the canonical filename.** A tool creating a new manifest MUST
  name it `datamanifest.toml`; discovery accepts the alternate spellings in a fixed order
  (first existing wins): `datamanifest.toml` > `DataManifest.toml` > `datasets.toml` >
  `Datasets.toml`. Previously the two implementations discovered different, partially
  disjoint name sets (the Julia tool did not find `datamanifest.toml`, the Python tool did
  not find `DataManifest.toml`); existing projects under any of the four names keep
  working. The spec prose now uses `datamanifest.toml` for the manifest file throughout.

## spec-v5.5 (schema `_META.schema = 1`)

**Configuration evaluation timing.** Behavioural only — no schema change, no manifest
change, no new fixtures.

- **The ladder is frozen at materialization.** A tool evaluates the scoped configuration
  once, when a manifest is materialized: the file-backed layers, the environment, and the
  host are captured as one snapshot, and every resolution for that manifest uses it.
  Re-resolution is explicit (re-materialize / refresh). One-shot CLI invocations are
  unaffected. Cross-machine resolution builds the remote machine's own snapshot (its
  config files, probed environment, hostname) instead of overriding parts of the local
  one. Rationale: each config variable has one well-defined value per session, identical
  across tools, instead of drifting with ambient state.

## spec-v5.4 (schema `_META.schema = 1`)

**Structural tables first, the `canonical` directive, worktree config fallback.**
Behavioural only — no schema change, no manifest change, no new fixtures.

- **Canonical ordering: `_*` tables first at the top level.** Writers emit the structural
  `_*` tables (`_META`, `_LANG`, `_LOADERS`, `_STORAGE`, …) at the head of the file, then
  the datasets, each group in code-point order; below the top level the plain recursive
  code-point sort is unchanged. Previously the spec mandated a uniform code-point sort at
  every level, which dropped the structural tables between the upper-cased and lower-cased
  dataset names; both tools already write `_*`-first (Python since 2026-06-05). The
  spec-v5.3 note calling that placement intended is superseded.
- **`canonical` (boolean, default `false`).** A config field on the ordinary scoped
  ladder (`DATAMANIFEST_CANONICAL` env var → config files / `[_STORAGE]`,
  `_HOST`-composable): when truthy, a tool whose native serialization differs from the
  normative reference SHOULD route manifest writes through the reference serializer
  (`datamanifest format`) for cross-tool byte-identical files, falling back to its native
  (semantically identical) output when the reference CLI is unavailable.
- **Linked `git worktree`s read the main checkout's checkout config** when they have none
  of their own — extending the spec-v5.1 state-file fallback to
  `.datamanifest/config.toml`, read-side only; a worktree-local config file always wins.

## spec-v5.3 (schema `_META.schema = 1`)

**The lock staleness age is a config field.** Behavioural only — no schema change, no
manifest change, no new fixtures.

- **`lock_stale_age` (seconds, default `30`).** The spec-v5.2 staleness age is now a named
  configuration field on the ordinary scoped ladder: `DATAMANIFEST_LOCK_STALE_AGE`
  environment variable → config files / `[_STORAGE]` (`_HOST`-composable). TOML number or
  numeric string; tools MUST fall back to the default on an unparsable or non-positive
  value. Rationale: every environment knob should have a config-file equivalent, and the
  ladder provides both (plus per-host composition for clusters) from one definition.

## spec-v5.2 (schema `_META.schema = 1`)

**Lock contention: wait, heartbeat, bounded staleness.** Behavioural only — no schema
change, no manifest change, no new fixtures.

- **Heartbeat.** The materializing writer SHOULD refresh the `.lock` pidfile's mtime on a
  regular interval (recommended `stale_age / 2`), so a long computation keeps a near-zero
  lock age throughout. The lock records `<pid> <hostname>`.
- **Contenders wait and re-check.** Previously the spec left contender behaviour
  undefined and tools diverged (fail vs. proceed unlocked). A contender now SHOULD wait
  for the lock and, on acquiring it, MUST re-check the entry before writing — concurrent
  workers (e.g. HPC jobs hitting the same `@cached` variation) compute once and load
  everywhere else.
- **Staleness rule.** A lock MAY be reclaimed when its age exceeds `stale_age` AND
  (its PID is dead on the local host, OR the age exceeds a several-fold grace multiple of
  `stale_age` — a holder that missed many consecutive heartbeats). A wrong reclaim is safe
  by construction (atomic publish + completion marker): worst case is duplicate work,
  never a partial entry.

## spec-v5.1 (schema `_META.schema = 1`)

**Git worktrees share the main checkout's state file.** Behavioural only — no schema
change, no manifest change, no new fixtures.

- **State-file resolution in linked `git worktree`s.** A linked worktree starts without
  the git-ignored `.datamanifest/` directory. When the project directory holds no state
  file under any recognized path and sits inside a linked worktree, a tool SHOULD fall
  through to the corresponding directory in the main checkout — for reads and as the
  write target, so every worktree of a repository maintains one shared inventory. A state
  file present in the worktree itself always takes precedence. The main checkout SHOULD
  be resolved via the `git` executable (the on-disk worktree layout is git internal);
  when `git` is unavailable, the main repository is bare, or the directory is not inside
  a linked worktree, lookups stay local.

## spec-v5 (schema `_META.schema = 1`)

**Storage v5 — machine-global defaults and scoped configuration.** The two folder fields
default to machine-global locations instead of repo-local folders, a new `$project`
predefined symbol namespaces the produced cache, two git-ignored config files carry
per-machine directives on a git-style resolution ladder, and the state file moves into a
per-checkout `.datamanifest/` directory. Behavioural only — no `_META.schema` change, and
the manifest format itself gains just the optional `[_STORAGE].project` field.

- **New built-in defaults.** `datasets_dir = "$user_data_dir/datamanifest/shared/datasets"`
  and `datacache_dir = "$user_cache_dir/datamanifest/projects/$project/cached"`. Datasets
  are shared and keyed (a key is a globally unique content identity, so one shared store
  deduplicates across projects); the produced cache is per-project (`cachetype/hash` is not
  globally unique and carries no content checksum). The trailing `shared/datasets` /
  `projects/$project/cached` segments keep the two trees disjoint even when both platform
  dirs point at one folder. The repo holds only the manifest and `.datamanifest/`. Setting
  `datasets_dir = "datasets"` / `datacache_dir = "cached"` restores the spec-v4 repo-local
  layout — manifests migrated from spec-v3 pin exactly that and behave unchanged.
- **`$project` (new predefined symbol).** The project name; defaults to the basename of
  the project root, overridable as a bare `project` field on the resolution ladder (a
  committed `project = "…"` is shared intent). Renames are safe: the state file keeps
  finding existing artifacts at their recorded locations.
- **Scoped config files + resolution ladder.** `.datamanifest/config.toml` (per-checkout,
  git-ignored) and `$XDG_CONFIG_HOME/datamanifest/config.toml` (user-global), both
  `[_STORAGE]`-shaped at the root level including `_HOST` sections. Ladder, first match
  wins: `DATAMANIFEST_<NAME>` env → checkout config (`_HOST`, then base) → manifest
  `[_STORAGE._HOST]` → manifest `[_STORAGE]` → user config (`_HOST`, then base) → built-in
  defaults. The committed manifest sits between the two config files; machine-specific
  directives belong in config files, and a tool SHOULD NOT write built-in defaults into
  the manifest (a written-out default would shadow the user's machine-wide preference).
- **New default `datasets_pools`.** Absent the field: `$repo/datasets` (pre-v5 repo-local
  data keeps being found and adopted, never re-downloaded), then
  `$user_data_dir/datamanifest/shared/datasets` (the shared store doubles as the default
  read pool, so it self-populates), then the legacy `$user_data_dir/datamanifest/datasets`
  and `~/.cache/Datasets`. `datacache_pools` stays opt-in.
- **State file relocation.** Canonical path: **`.datamanifest/state.toml`**; the
  `.datamanifest/` directory is entirely git-ignored (tools drop a
  `.datamanifest/.gitignore` containing `*` on first write), so the manifest is the only
  committed file. The legacy `.datamanifest-state.toml` and `cached.toml` paths are still
  read; the first write relocates the file to the canonical path.

## spec-v4.4 (schema `_META.schema = 1`)

**Checksums carry their algorithm.** A new `checksum` field replaces the bare `sha256`
field with a pooch-style **`<algo>:<hex>`** value (`sha256:…`, `md5:…`; a bare hex string
is read as `sha256`). Additive and backward-compatible — no `_META.schema` change.

- **`checksum` (new field).** Used for **both** fetch-time verification and change
  detection, in the algorithm it names. Empty ⇒ a tool computes the digest (as `sha256:`)
  on first download/adoption and writes it back. A tool MUST NOT silently rewrite a
  declared non-`sha256` digest to `sha256`. New *Checksums* section in `SCHEMA.md`.
- **Why an algorithm prefix.** Data repositories publish digests in different algorithms
  (Zenodo/PANGAEA/DVC commonly **md5**). Carrying `md5:…` lets a tool verify the published
  digest directly instead of declaring no checksum and re-hashing after download.
- **`sha256` is now a legacy alias.** Readers MUST accept `sha256 = "<hex>"` and treat it
  as `checksum = "sha256:<hex>"`; writers SHOULD emit `checksum`. A tool upgrades a
  manifest in place the next time it writes the file (replacing `sha256` with `checksum`).

## spec-v4.3 (schema `_META.schema = 1`) — unreleased

**Remote sources** — object-store download schemes, a `lazy_access` mode for never-materialized
in-place access, and fail-loud identifier resolution. Additive (no `_META.schema` change); two
new optional dataset fields.

- **Object-store `uri` schemes are normative.** `s3://`, `gs://`, `gcs://`, `az://`, `abfs://`,
  `abfss://`, `adl://`, `gdrive://` mean "fetch the named object, then verify `sha256` as usual."
  The spec fixes the **scheme set and semantics, not the mechanism** — a tool fetches with any
  backend (the Python tool via `fsspec`; a peer tool via its own packages), and a tool that
  cannot serve a scheme **`delegate`s** it or errors *unsupported scheme* — never silently skips
  it. HTTP/HTTPS keep their dedicated GET path and are deliberately **not** in this set. New
  *Download schemes* section; `manifest.v3.json` documents the `uri` schemes.
- **`lazy_access` (new bool) — an *access* mode.** Open the `uri` in place via a loader instead
  of materializing a local copy: **no copy, no checksum, no state-file record**; a loader is
  required (a bare `lazy_access` is an error). The mechanism — streaming, an sshfs/FUSE **mount**,
  an object-store filesystem — is implementation-defined; this **subsumes the former deferred
  standalone `mount` store** (one materialization axis: download vs. in-place), so no `mount`
  capability is added. The "no materialization axis" / deferred-`mount` spec text is rewritten
  accordingly.
- **`skip_download` clarified — a *management* mode (unchanged behavior, sharpened wording).** It
  marks a *passive, externally-managed dependency*: not downloaded, **not verified**, never
  touched by maintenance (e.g. a large user-maintained archive). It is **orthogonal** to
  `lazy_access` (who manages the bytes vs. how they are read) and the two are not meant to
  combine. This **un-overloads** `skip_download`: in-place/on-the-fly access is now `lazy_access`,
  not `skip_download` + a loader.
- **Identifier resolution is exact-or-error.** Resolving a single dataset by `name` / `alias` /
  `doi` to **more than one** match is a fail-loud error naming the candidates, never a silent
  first-match — a `doi` may be shared across split datasets. New *Identifier resolution* rule; the
  sync addressing contract now references it.

## spec-v4.2 (schema `_META.schema = 1`) — unreleased

**Read pools** — reuse a dataset or `@cached` result that already exists elsewhere on the
machine instead of fetching or recomputing it — plus two resolution/maintenance
clarifications. Additive: no `_META.schema` change.

- **`[_STORAGE].datasets_pools` / `datacache_pools`.** Optional lists of **read-only
  locations** added to read-resolution: probed after the recorded and directive-derived
  location and **before** downloading/producing. A `datasets_pools` hit is **checksum-verified**
  against the declared `sha256` (mismatch skipped), **recorded in the state file**, and used
  **in place — no copy** (a genuine download still goes to `datasets_dir`; gold standard).
  `datacache_pools` is symmetric (`<pool>/<cachetype>[/<version>]/<hash>`, `config.toml`-gated).
  Defaults differ by **trust**: `datasets_pools` absent ⇒ built-in well-known pools
  (`~/.cache/Datasets`, `$user_data_dir/datamanifest/datasets`), since a fetched dataset is
  checksum-verifiable; `datacache_pools` absent ⇒ **no pools** (opt-in), since produced
  artifacts have no de-facto shared location and no content checksum. An explicit list is used
  verbatim, an empty list disables. Host-composable via `[_STORAGE._HOST]`; env
  `DATAMANIFEST_DATASETS_POOLS` / `DATAMANIFEST_DATACACHE_POOLS`. `manifest.v3.json` types both.
- **Single recorded location (multiple locations decided *out*).** The state file keeps **one**
  `storage_path` per object — the last location it was found at or written to, refreshed by
  self-heal, never grown into a set. Resolution only needs to find one copy; a stray second copy
  reads as `untracked` and is cleaned up explicitly, and a shared copy elsewhere is found via a
  read pool. (Reclassifies the spec-v4.1 ROADMAP deferral as out-of-scope.)
- **Maintenance applies on the explicit selection.** A filtered `list … --delete` / `--move` is
  itself the explicit user selection, so a tool MAY apply directly and SHOULD offer a
  `--dry-run` preview (the spec-v4.1 "default to a dry run" wording is relaxed; the hard rules —
  never delete everything by default, never as a side effect — stand).

## spec-v4.1 (schema `_META.schema = 1`) — unreleased

**Unify the produced-only `cached.toml` index into a single git-ignored state file,
`.datamanifest-state.toml`.** Splits the committed **spec** (`datasets.toml` = *what* to
track and *how* — the expectation) from **regenerable local state** (where each object
actually landed — the ground truth). The manifest's `_META.schema` is unchanged (still 1);
this is a structural change to the sibling index format (its own `_META.schema = 5`).

- **One inventory for both kinds.** The state file records fetched datasets *and* produced
  artifacts under two top-level namespaces, parallel to the two storage folders:
  - `datasets`: storage key ⇒ resolved `storage_path` + actual `sha256` (omitted under
    `skip_checksum`);
  - `datacache`: `cachetype[@version]` ⇒ a `ref`/`format` recipe + an `instances` table
    mapping each parameter `hash` to its full artifact directory (`@` is the reserved version
    separator). **Params leave the index** — they live in each artifact's `config.toml`.
- **Read-only inventory; the directive is the gold standard.** The state file records *where
  things are* and is consulted to *find* an existing object — it **never directs a write**.
  Every (re)materialization follows the current directive (`datasets_dir` / `datacache_dir` /
  per-dataset `storage_path` / `@cached(storage_path=…)`). Read-resolution checks the recorded
  location **first**, ahead of any derivation rule, so a moved object is found at its new home.
- **Git-ignored by default.** Artifacts are local, often outside the repo, and not
  re-fetchable, so the inventory is regenerable per-machine state — not a committed
  reproducibility lock. (A shared-drive project MAY track it, but that is a user's setup, not
  the design intent.) The `Manifest.toml`-analogue / "applications commit it" framing is dropped.
- **Self-heal additive, removal explicit-only.** Active resolution refreshes a *relocated*
  record, registers an *untracked* object, and re-materializes a *missing* one — but **never
  deletes**. A tool MAY label each object `clean` / `missing` / `relocated` / `untracked` /
  `modified`; passive listing only labels. Two explicit user actions reconcile: `--refresh`
  (fix the state file only — re-point relocated, drop stale) and `--delete` (remove bytes +
  entry, the sole byte remover). Maintenance (`--delete` / `--move`) now spans fetched datasets
  too, with the user-managed-path / `skip_download` skip-guard generalized to both kinds.
- **Concurrency.** Every write re-reads + merges (additive union, last-writer-wins per object) +
  atomic-renames, so parallel downloads/produces don't clobber each other.
- **Schema.** New `state.v4.json` validates the state file (`datasets` + `datacache`,
  `_META.schema = 5`), superseding `cached.v3.json` (kept for the legacy `cached.toml` shapes,
  `_META.schema` 1–4, which conforming readers migrate forward; `cached.toml` is the recognized
  legacy name). `metadata-sidecar.v3.json` renames the `cached_toml` back-pointer to
  `state_file`.
- **Spec vs. state — same fields, two meanings.** A dataset's `storage_path` and `sha256` live
  in *both* files on purpose: in `datasets.toml` they are the expectation (directive / contract),
  in the state file the ground truth (resolved / actual). Intentional, harmless duplication;
  fully separating them (expected-vs-actual `sha256`, resolved `storage_path`, multiple recorded
  locations, the `modified` state) is deferred — see `ROADMAP.md`.

## spec-v4 (schema `_META.schema = 1`) — unreleased

A **breaking storage-layout revision** that radically simplifies storage to **two paths** and
makes everything **local by default**. The TOML *shape* stays additive (`_META.schema` = 1);
the break is in *where bytes land on disk* (versioned on the spec-tag axis, as spec-v3 was).
Existing stores need migration or a clean re-fetch. The machinery of the earlier spec-v4
drafts — scope, content prefixes, the `datamanifest` appname, project-name derivation,
`DATAMANIFEST_DIR`, and the scope/prefix ladders — is **removed** in favor of letting the user
write the two paths directly.

- **Two folder fields, local by default.** `[_STORAGE].datasets_dir` (fetched) and
  `datacache_dir` (produced) are the whole model. They default to the relative paths
  `"datasets"` / `"cached"` ⇒ repo-relative ⇒ visible `./datasets/`, `./cached/`. A fetched
  dataset lands at `<datasets_dir>/<key>`, a produced artifact at
  `<datacache_dir>/<cachetype>/[<version>/]<hash>/` — no scope, no prefix, no derived name in
  between. Adding a `pyproject.toml` no longer moves anything.
- **`$`-symbols.** Predefined **`$user_data_dir`** / **`$user_cache_dir`** (straight from
  `platformdirs`, **bare** — no app name) and **`$repo`**; any other bare `[_STORAGE]` key is a
  user-defined symbol, made host-specific in `[_STORAGE._HOST."<glob>"]`. `$USER`/env and `~`
  expand. Centralize/share with one edit, e.g. `datasets_dir = "$user_data_dir/myproj"`.
- **Per-dataset `storage_path`** replaces both the former `store` and `local_path`. Default
  `$datasets_dir/$key`; contains `$key` ⇒ tool-managed/keyed, an exact path without `$key` ⇒
  user-managed and never touched by maintenance. (Named `storage_path`, not `path` — `path` is
  the URI's parsed component.)
- **Two environment variables**, `DATAMANIFEST_DATASETS_DIR` / `DATAMANIFEST_DATACACHE_DIR`
  (user symbols override as `DATAMANIFEST_<NAME>`); `$user_data_dir` / `$user_cache_dir` keep
  per-OS resolution. `DATAMANIFEST_DIR`, `DATAMANIFEST_SCOPE`, `DATAMANIFEST_PREFIX_*` are gone.
- **Partition-local staging.** Materialization stages within the target folder's partition (a
  `$scratch` dataset stages on `$scratch`) — required for an atomic rename and so voluminous
  data never transits a small `~/.cache`. A tool's app-internal files live alongside, never in
  a separate global folder.
- **`cached.toml` drops `scope` (and the recipe `store`).** Recipes are keyed by
  `(cachetype, version)`; the on-disk location is the manifest's `datacache_dir`, and
  reachability is `(cachetype, version, hash)`. (Schema-2 nested structure, hit self-healing,
  and the index lifecycle are unchanged from spec-v3.7.)
- **In-memory & multiple manifests (library use).** A manifest is a logical structure that MAY
  be built in memory and **several MAY be live at once**, each resolving independently (the API
  is per-language — Python / Julia `Database`; whether/where it persists is the author's
  choice). **Recommended:** a library shipping data dependencies owns them this way — its own
  manifest with explicit `datasets_dir` / `datacache_dir` (e.g. under `$user_data_dir/<library>`)
  — rather than touching the end user's `datasets.toml`; without explicit folders its data falls
  back to the end user's project, who owns the location.
- `manifest.v3.json` types `[_STORAGE].datasets_dir` / `datacache_dir` and the dataset
  `storage_path`; `cached.v3.json` drops the recipe `scope` / `store`. README and the reference
  guide carry the storage recipe (shared downloads pool + per-project versioned cache, per-host
  roots).


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
