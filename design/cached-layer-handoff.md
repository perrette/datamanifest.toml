# `@cached` / produce-or-load layer — resolved design + implementation hand-off (spec-v2)

> **Update 2026-06-03 — scope revised (read first).** The produce-or-load layer is
> moving **out of the core** into a **companion package** (one per language) that
> *depends on* datamanifest and reuses its engine; the cross-tool format spec stays
> in this repo, reframed. The "in-core, thin layer" framing below is **superseded** —
> see `design/storage-model-revision.md`. The reuse analysis, the LGMIO reference, the
> resolved open questions, and the salvageable `cache.py` all still stand; only the
> *home* of the implementation changes (core → companion). The materialized in-core
> `cached-layer` roadmaps are **on hold** pending re-targeting at the companion packages.

**Status:** **design resolved.** This supersedes the earlier "paused, take-2"
hand-off. The scope question ("does the caching layer belong in `datamanifest`
at all?") has been answered, the residual conflation in the first spec-v2 attempt
has been identified and corrected in `SCHEMA.md`, and the open design questions
are settled (mostly by `design/caching-and-dataset-storage.md` §6.D plus the
salvageable code on the paused Python branch). What remains is **implementation**,
not design.

---

## 1. The scope verdict (why this layer belongs here)

The worry was that produce-or-load caching might be a *parallel branch of code
with no overlap* — in which case it would not belong in this package. The opposite
is true. Measured against the merged Python `main` engine, the caching layer is a
**thin skin** that reuses almost everything:

| Concern | Existing engine (Python `main`) | Reused by `@cached`? |
|---|---|---|
| Atomic publish + lock + completion marker | `materialize()` / `is_complete()` / `_acquire_lock()` (`pipelines.py`) | **100% — same primitive** (LGMIO hand-rolls this with `_atomic_write` + `Pidfile`; we already generalized it). |
| Multi-root storage (`data`/`cache`/`repo`, `[_STORAGE]`, env/host/profile) | `store_root()` (`storage.py`) | reused; `@cached` just defaults `store="cache"`. |
| `<root>/<key>` path scheme | `get_dataset_path()` / `resolve_existing_path()` | reused; the `key` is just a string. |
| Loader / format dispatch | the 5-rung loader ladder + `default_loaders` | reused as the "load" step. |
| Canonical TOML round-trip | the `datasets.toml` reader/writer | reused by the `cached.toml` reader/writer. |

The **only genuinely new machinery** is **parameter-hash keying** (canonical JSON →
SHA-256, ~10 lines), plus the two small sidecars and the `cached.toml` registry. The
decorator/macro itself is an ergonomic, **non-normative**, per-language surface.

**Unifying frame (now in `SCHEMA.md`):** *an addressable object = a recipe + a key +
a store + a cache policy.* Fetched and produced datasets differ in exactly two slots:

- **recipe:** `uri`/`shell`/`git` fetch  ↔  a project function;
- **key:** content `sha256` + source key  ↔  `param_hash` of keyword parameters.

Everything else (store, materialize, load, GC roots) is recipe-agnostic. So the
overlap is structural and large — this layer earns its place precisely because a
standalone caching package would have to re-implement materialize/lock/store/loaders.

**Decision: keep the layer; maximize overlap at the *engine* layer; keep the *files*
separate.** Share the primitives; do **not** merge the manifests.

---

## 2. The mistake that was corrected (read before touching code)

The first spec-v2 attempt "maximized overlap" at the **wrong layer** — the
schema/file layer — by making a produced artifact *literally a `datasets.toml`
entry*. Concretely, on the paused Python branch `autonomous/spec-v2`:

- `cachetype` was added as a field on the `DatasetEntry` dataclass (`database.py`);
- `init_dataset_entry()` grew a branch deriving `<cachetype>/<param_hash>` keys for
  "produced" entries;
- `download_dataset()` grew a `_produce_dataset()` branch gated on `is_produced()`.

This pollutes the hand-authored, `Project.toml`-like `datasets.toml` with
machine-generated, parameter-hash churn — collapsing the **one** distinction that
must survive: **authorship** (hand-written external deps vs machine-written cache),
i.e. the `Project.toml` ↔ `Manifest.toml` split.

**The corrected model:** a produced dataset has **no hand-authored TOML
representation at all.** It originates from a `@cached`-decorated function (in code).
Its only on-disk TOML footprint is **machine-generated**: the `cached.toml` index
entry + the per-artifact `config.toml` / `metadata.toml` sidecars. `cachetype` is a
field of *those* (and of the on-disk path) — **never** a field a human writes in
`datasets.toml`, and `download_dataset()` never sees a produced dataset.

---

## 3. The reference implementation (LGMIO `@cached`)

`~/Projects/LGMRecons/packages/LGMIO/src/Cache.jl` — the production Julia macro this
layer standardizes. Key features (all confirmed read):

- `@cached cachetype="…" key=(args -> (;…)) [ext=] [basename=] [kind=]` wraps a
  function; injects a `cached::Bool=true` escape hatch; on miss takes a
  `Pidfile.mkpidlock` (stale-age 30s) and re-checks, then computes + saves.
- On-disk layout `<cache_dir>/<cachetype>/<hash>/<basename>.<ext>` + `config.toml`
  (re-hashable hash inputs) + `metadata.toml` (timestamp / version / host / user /
  `[git]`). `metadata.toml` is **write-if-absent** (cache hits don't re-stamp).
- **Three-way arg split:** hash-affecting params (in the key) / `_`-prefixed runtime
  knobs (excluded from the hash, still visible in the body) / a dedicated
  `_metadata_extras` channel (audit-only, merged into `metadata.toml`).
- `_atomic_write` (`.tmp` before the extension → rename) so a killed process never
  leaves a corrupt file.
- Note: LGMIO's own `cache_key` is **SHA-1 over Julia `Serialization`/sorted-dict**
  (`Serialization.jl`) — a *Julia-internal legacy* scheme. It is **not** the
  cross-language normative hash. spec-v2 adopts **canonical JSON → SHA-256** instead
  (portable, byte-pinned across Python and Julia today); the Julia port must move to
  it. The LGMIO macro is the *ergonomic* reference, not the *hash* reference.

---

## 4. The seven open questions — resolved

These are no longer open. Each answer is grounded in §6.D and/or the salvageable code.

1. **Key derivation.** Default key table = **all keyword parameters minus
   `_`-prefixed keys**. An optional explicit `key` selector (LGMIO's `key=(args -> …)`
   closure, or a Python list of names) MAY narrow it — *how* a tool derives the table
   is **implementation-defined**; the **serialization + hash are normative**.
   Produced datasets are **keyword-only**: positional `args` are rejected (no stable
   name→value identity to hash). Fetched datasets are unaffected and keep `args`.
2. **Hash serialization.** **Canonical JSON (RFC 8785 / JCS) → lowercase-hex
   SHA-256.** Hash-input values restricted to strings / integers / booleans / arrays /
   objects-of-those; **floats and nulls disallowed** (a float knob is passed as a
   string). Reference vector: `{"grid":"5x5","skip_models":["CESM.*","FGOALS.*"]}` →
   `83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b`. (Not LGMIO's
   SHA-1 scheme — see §3.)
3. **Sidecar contents.** Lift LGMIO's split: `config.toml` = the key table + a
   `[_META]` block (`schema`, `cachetype`, `hash`); `metadata.toml` = provenance
   (`created`, `tool`, `host`, `user`, `[git]`) + an `[origin].cached_toml`
   back-pointer (audit only). `metadata.toml` is **write-if-absent**.
4. **`cached.toml` scope + location.** Sibling of `datasets.toml`, one per project.
   **Gitignored per-machine state by default; opt-in commit** for shared
   reproducibility (the `Manifest.toml` convention). Lists produced datasets by
   **portable key** (`cachetype` + `hash`), never absolute path.
5. **Decorator/macro surface — what graduates to the normative spec.**
   - *Normative (cross-tool, on-disk/identity):* the param-hash algorithm; the
     "all-non-`_`-kwargs" default + the `_`-exclusion rule; the keyword-only rule for
     produced datasets; the `<cachetype>/<hash>` key; the `config.toml` /
     `metadata.toml` / `cached.toml` schemas; the `<cachetype>/<hash>/<basename>.<ext>`
     layout; `store="cache"` default; the safe-materialization conventions.
   - *Per-language / non-normative (ergonomic):* the decorator/macro spelling; the
     `key` selector form; `ext`/`format` inference; `kind`; `basename`; `cache_dir`
     override; the `cached=`/escape-hatch name; the `_metadata_extras` plumbing.
6. **Serialization format.** Per-tool, per-`format` (the existing `format` + loader
   concern). Produced artifact **bytes are NOT assumed cross-language-loadable** —
   spec-v2 pins cross-tool *addressing* (the hash/key) and *GC*, not the blob format.
   This is the one place the unification is genuinely looser; it narrows the normative
   surface but does not reduce code reuse.
7. **GC.** Root-reachability collector. Roots = the two index files (`datasets.toml`
   roots fetched datasets incl. `store="cache"` ones; `cached.toml` roots produced
   ones). A depot-level **usage log** (known index paths + last-seen) discovers the
   live root set. **Collectable iff** no still-existing root references the key **and**
   older than a grace age. `data`/`repo` stores are never collected. CLI: `datamanifest
   gc`. **Phase 2** (ship sidecars first; add the index + usage-log + `gc` once the
   cache accumulates cruft).

---

## 5. Current artifact status

- **`SCHEMA.md` spec-v2 section** — present, and **now corrected**: the
  "a dataset declares `cachetype` in the manifest / is produced iff it declares a
  `cachetype`" framing has been replaced with the `@cached`-originated,
  `cached.toml`-native model. The param-hash spec, sidecar schemas, `cached.toml`
  schema, GC rule, capabilities (`cache-produce`, `cache-gc`), and the reference
  vector are kept. Schema stays **1**; spec-v2 is **additive**.
- **Fixtures** — the conflated `produced.toml` / `produced.expected.json` (a produced
  dataset declared inside a `datasets.toml`) have been **replaced** with a
  `config.toml` *sidecar* fixture exercising the param-hash with **no `datasets.toml`
  entry**. `cached_index.toml` (a real `cached.toml`) is kept. The fixtures `README.md`
  is updated to match.
- **`spec-v2` git tag (local only, not pushed)** — commit `44148f4` still embeds the
  flawed framing in its diff. **Recommend: after these corrections land, re-promote a
  clean spec-v2 commit and move/recut the tag.** (Left for the maintainer.)
- **Python `~/Projects/datamanifest`** — v1.1 merged to `main`. Paused branch
  `autonomous/spec-v2` (worktree `.worktrees/spec-v2`): **keep** `cache.py`
  (`param_hash`, `key_table_from_kwargs`, sidecar I/O, `CachedIndex`, the `@cached`
  decorator — all recipe-agnostic and clean); **drop** the conflation
  (`cachetype` on `DatasetEntry`; `is_produced()` / `resolved_store()`; the produced
  branches in `init_dataset_entry()` and `download_dataset()` / `_produce_dataset()`).
  Re-roadmap per §6 below.
- **Julia `~/Projects/DataManifest.jl`** — v1.1 is **NOT yet merged** (11 commits on
  `autonomous/spec-v1.1`; `main` at a docs commit; leftover worktree
  `.worktrees/spec-v1.1`). **Julia v1.1 MUST merge before any Julia v2 work.**

---

## 6. Implementation roadmap (post-design)

Build order (per `caching-and-dataset-storage.md` §6.D "Still open / next", refined):

**Phase 1 — `@cached` + sidecars (no index, no GC).**

1. **Python.** On a fresh branch off `main` (not the conflated one), cherry-pick the
   clean half of `cache.py`:
   - keep `param_hash`, `key_table_from_kwargs`, `write_config`/`read_config`/
     `config_is_valid`, `write_metadata`/`read_metadata`, the `@cached` decorator;
   - wire `@cached` to the **existing** `materialize()` / `store_root("cache")` /
     loader ladder — do **not** route through `download_dataset()`;
   - do **NOT** add `cachetype` to `DatasetEntry`; do **NOT** add `is_produced()` /
     `resolved_store()` / a produced branch anywhere in the fetch path.
2. **Julia.** Merge v1.1 first. Then port `@cached` from LGMIO, swapping its SHA-1
   `cache_key` for the canonical-JSON SHA-256 `param_hash`, and reusing
   `DataManifest.jl`'s materialization + store resolution + loaders rather than
   LGMIO's bespoke `_atomic_write` / `_resolve_cache_dir`.
3. Both: reproduce the reference vector; pass the `config.toml` sidecar fixture.

**Phase 2 — `cached.toml` index + usage log + `gc`.** Add `CachedIndex` writing on
each produce; the depot usage log; `datamanifest gc` with the root-reachability rule.
Gated behind the `cache-gc` capability; pass the `cached_index` fixture.

Follow the `autonomous-roadmap` style used for v1.1 (one roadmap per package).

---

## 7. v1.1 foundation this builds on

`store` field, `[_STORAGE]` (+ `_HOST`/`_PROFILE`), platformdirs roots, `repo→data→
cache` read order, the safe-materialization primitive (`.tmp`→rename→`.complete`+
`.lock`), parameterized `{ref, args, kwargs}` bindings + `$var` substitution,
verify-once, recursive canonical ordering. Spec at tag `spec-v1.1`. The `@cached`
layer reuses the `cache` store + the safe-materialization primitive verbatim.
