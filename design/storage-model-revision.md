# Storage model revision + caching scope — design notes (2026-06-03)

**Status:** **promoted to `SCHEMA.md` (spec-v2).** The Storage section now describes the
`$`-folder-variable model below, and the produce-or-load section is reframed as a
companion-layer format. Open questions in §9 are resolved (see the resolutions inline).
Still pending: the implementations (Python / Julia cores + companion packages) and the
fixture suite kept in sync (the `storage` fixture + validator were updated alongside the
spec). Supersedes parts of `caching-and-dataset-storage.md` §6 (C/D/E) and the "in-core"
framing in `cached-layer-handoff.md`.

**Decisions locked in when promoting (see §9 for the reasoning):**
- The new `[_STORAGE]` default-selector knob is named **`default`** (`default_store` would
  be redundant under `[_STORAGE]`).
- Built-in folders resolve to **dataset-root** locations: `$data` =
  `user_data_dir("datamanifest")/Datasets`, `$cache` = `user_cache_dir("datamanifest")/Datasets`,
  `$repo` = `<project_root>/datasets`; `default` defaults to bare `$data`. This keeps
  `default = "$data"` clean and preserves the exact v1.1 on-disk paths (no re-download).
- Selectors **accept a sub-path** (`store = "$cache/sub"` → `<cache_root>/sub/<key>`).
- Legacy bare `store = "data"|"cache"|"repo"` is **hard-migrated**: a spec-v2 `storage`
  tool MUST reject bare selectors; only `$`-form is valid. (`_META.schema` stays **1** —
  this is a spec-document/capability-level break, gated by the `storage` capability, not a
  data-model structural change.)
- The former `mount` store is **deferred, not abandoned**: a locations-only model has no
  home for never-materialized in-place access, so the `mount` capability stays **reserved**
  (mechanics unspecified, not advertised) for a future revision to define alongside folders.

## 1. Scope — caching becomes a companion package

The produce-or-load (`@cached`) layer **leaves the core** for a **companion package**
(one per language) that *depends on* datamanifest and reuses its engine
(safe-materialization, store/folder resolution, loaders). The cross-tool **format**
spec (parameter hash, `config.toml`/`metadata.toml`, `cached.toml`) **stays in this
spec repo**, reframed as a companion produce-or-load layer; the `cache-produce` /
`cache-gc` capabilities are declared by the companion tool, not the core fetch tool.
**The core keeps no GC and no disposability policy.**

## 2. The core knows a few folders — *locations only, no policy*

Built-in folders are exactly the ones with an unambiguous OS convention:

| Folder | Location | Nature |
|---|---|---|
| `data` | platformdirs `user_data_dir` | persistent, protected |
| `cache` | platformdirs `user_cache_dir` | OS-reclaimable **location** — no core policy attached |
| `repo` | `<project_root>/datasets` | project-relative; travels with the repo (not an OS dir) |

- `cache` is just the reclaimable *location*. The core attaches **no** disposability
  semantics to it. (datamanifest may use this dir for its **own** internal caches —
  HTTP request metadata, small non-dataset files — which is app-internal and separate
  from any datasets stored under it. Disposability/GC of *produced* datasets is the
  companion's concern.)
- **Not built-in:** `temp`/scratch/state/etc. "temp" has no single canonical home
  (`/tmp` vs `$TMPDIR` vs `/scratch/$USER` vs the runtime dir) — too host-dependent to
  hardcode; express it as a *user-defined* folder variable instead. A folder is
  built-in **only** if its location is genuinely conventional.
- App-internal state (the companion's usage log, etc.) is **not** a dataset store and
  is out of this model.

## 3. Folders are a `$`-variable namespace (host-aware), referenced with `$` only

- **Built-in variables:** `$data`, `$cache`, `$repo`.
- **User-defined:** any key under `[_STORAGE]` (e.g. `scratch = "…"` defines `$scratch`).
- **Definition vs reference:** `[_STORAGE]` keys are **bare** (`scratch = "…"`);
  references always use **`$`** (`$scratch`) — same convention as the existing `$var`
  binding substitution.
- **References use `$` only.** No bare folder names anywhere (selectors included). This
  removes the ambiguity between "a folder alias" and "a literal string."
- **Host-aware resolution.** Every variable resolves through the existing ladder —
  `DATAMANIFEST_<NAME>_DIR` env → `[_STORAGE._PROFILE.<name>]` → `[_STORAGE._HOST.<glob>]`
  → `[_STORAGE].<name>` base → built-in default (platformdirs, or project-relative for
  `repo`). **Host-specificity lives in resolving the variable** — defined once, centrally.

## 4. Two field kinds

- **Selectors** — `default` (project-wide; **new**) and a dataset's `store`. The value is
  a `$`-folder reference, optionally with a sub-path: `default = "$data"`,
  `store = "$scratch"`, `store = "$cache/sub"`. The dataset is keyed under it:
  `<resolved>/<key>`. `store` defaults to `default`; `default` defaults to `$data`.
- **Path expressions** — `[_STORAGE]` root values and `local_path`. Full paths that
  interpolate folder variables plus `$USER`/`~`/env. `local_path` bypasses the keyed
  `<root>/<key>` layout (it is an exact location).

## 5. Host-specific `local_path` — via variables, not per-dataset host maps

A machine-specific exact path is `local_path = "$scratch/exact/file.nc"`, with
`$scratch` host-resolved. **No** per-dataset `_HOST` table. This covers the
"`local_path` that does not point to the repo" case, portably across machines.

## 6. Hard guardrails (the things that keep this from sprawling)

1. **Host-specificity is *always* a property of a folder variable's resolution** —
   never a per-dataset host map. The `$`-scheme makes this hold for `store` and
   `local_path` alike.
2. **The built-in folder set stays exactly {`data`, `cache`, `repo`}.** Everything else
   is a user-defined variable. Built-in ⇔ genuinely conventional location.

## 7. Delta vs spec-v1.1

- Drop the data/cache retention-**policy** tiers — folders are *locations* only (`data`
  and `cache` remain distinct *places*, but the core enforces nothing about lifetime).
- `repo` recast as just a built-in folder variable (project-relative default), not a
  special store class.
- **New** `[_STORAGE].default` — the project-wide default-store selector.
- Folder references are **`$`-only**; selectors no longer accept bare names.
- `local_path` gains host-specificity for free through `$`-variable interpolation (no new
  field — just allow folder variables inside `local_path`).
- Produce-or-load / `cache-produce` / `cache-gc` / GC **leave the core** for the
  companion package; the `SCHEMA.md` spec-v2 section is to be reframed accordingly.

## 8. Example

```toml
[_STORAGE]
default = "$data"                       # project-wide default folder (reference, $-form)
scratch = "$TMPDIR/datasets"            # user-defined folder variable (host-independent here)

[_STORAGE._HOST."login*.hpc.edu"]
scratch = "/scratch/$USER/datasets"     # same variable, host-specific resolution
data    = "/work/$USER/datasets"        # override a built-in's location, host-specific

[big]
uri   = "https://…"
store = "$scratch"                      # keyed under the host-resolved scratch root

[pinned]
local_path = "$scratch/exact/file.nc"   # explicit path, host-specific via the variable
```

## 9. Open questions — resolved on promotion (2026-06-03)

- **Name of the default knob** → **`default`**. It lives under `[_STORAGE]`, so
  `[_STORAGE].default` is already unambiguous; `default_store` would be redundant.
- **Sub-path in selectors** → **allowed**. `store = "$cache/sub"` resolves to
  `<cache_root>/sub/<key>`; the literal sub-path sits between the resolved folder root and
  the key. (Folder *definitions* stay separate; the sub-path is just selector sugar.)
- **Back-compat for bare `store`** → **hard-migrate**. Bare `data`/`cache`/`repo` selectors
  are invalid in spec-v2; a `storage` tool MUST reject them and only accept `$`-form. No
  legacy-alias read. `_META.schema` stays **1** — the `store` value-grammar change is a
  spec-document/capability-level break (gated by `storage`), not a structural data-model
  change, consistent with spec-v2 caching keeping schema 1. (The separate legacy *on-disk
  path* read-probe is unchanged — it softens the v1.1 folder-location move, not the
  selector syntax.)
- **Resolution ladder reuse** → **confirmed.** One ladder for *all* folder variables
  (built-in and user-defined): `DATAMANIFEST_<NAME>_DIR` env → `_PROFILE.<name>` →
  `_HOST.<glob>.<name>` → `[_STORAGE].<name>` → built-in default (data/cache/repo only;
  a user-defined name unresolved on every rung is an error). The `DATAMANIFEST_<NAME>_DIR`
  env form applies to user-defined names too (`DATAMANIFEST_SCRATCH_DIR`).

### Still open (companion-package, out of this spec promotion)

- **Where the companion package keeps its own state** (its own app dir vs under
  datamanifest's `$cache`). App-internal state is not a dataset store; deferred to the
  companion package design, not the cross-tool format spec.
