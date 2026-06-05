# DataManifest reference guide

A readable, language-agnostic walkthrough of every part of the `datamanifest.toml`
format. It complements the two other layers of documentation:

- **[`SCHEMA.md`](../SCHEMA.md) is normative.** When this guide and the spec disagree, the
  spec wins. Each section here links to its normative counterpart.
- **Implementation READMEs are language-specific.** API calls, CLI verbs, install steps —
  see [Python `datamanifest`](https://github.com/perrette/datamanifest) and
  [Julia `DataManifest.jl`](https://github.com/awi-esc/DataManifest.jl). This guide covers
  only what is shared across them.

**Copy freely.** This guide is a *guideline*, not a dependency. An implementation is
welcome to copy or adapt any of it into its own documentation (it is MIT-licensed, like the
rest of this repo) — there is no obligation to link back or defer to it. Each
implementation's docs should stay self-contained and authoritative about what *that package*
actually does (the spec tag it targets, the capabilities it implements, any deviations);
this guide describes the shared contract those docs can build on.

A complete, mostly-runnable manifest is in [`examples/datasets.toml`](../examples/datasets.toml).

## Contents

1. [The manifest in one minute](#the-manifest-in-one-minute)
2. [Declaring datasets](#declaring-datasets)
3. [Language bindings](#language-bindings)
4. [Resolution: the fetch and load ladders](#resolution-the-fetch-and-load-ladders)
5. [Storage](#storage)
6. [Produced datasets and caching](#produced-datasets-and-caching)
7. [Maintenance (inspect)](#maintenance-inspect)
8. [Cross-machine sync](#cross-machine-sync)
9. [Conformance and versioning](#conformance-and-versioning)
10. [Migration and deprecations](#migration-and-deprecations)

---

## The manifest in one minute

`datasets.toml` (Python) / `Datasets.toml` (Julia) is a hand-authored TOML file that
declares a project's data dependencies — the `Project.toml` / `pyproject.toml` analogue for
data. It is committed, language-agnostic, and never machine-rewritten beyond auto-filled
checksums. Produced (cached) datasets are **not** listed here; they live in a sibling
`cached.toml` (see [Produced datasets](#produced-datasets-and-caching)).

```toml
[_META]
schema = 1                       # data-model version (always 1 today)

[sea_surface_temp]               # one table per dataset, keyed by name
uri    = "https://example.com/sst.nc"
sha256 = "…"                     # auto-filled on first download, verified thereafter
format = "nc"
```

Top-level keys beginning with `_` are **structural** (`_META`, `_LANG`, `_STORAGE`,
`_LOADERS`); every other top-level table is a dataset. Readers preserve unknown `_*` keys
verbatim. *Normative: [SCHEMA.md §Structural keys / §Top-level layout](../SCHEMA.md#structural-keys).*

---

## Declaring datasets

A dataset table holds language-agnostic **contract fields**. All are optional; the common
ones:

| Field | Meaning |
|---|---|
| `uri` | Source to download (`https`, `git`/GitHub, `ssh`, …). `uris` for mirrors. |
| `sha256` | Expected digest; auto-filled on first download, verified at fetch. |
| `format` | Format hint (`csv`, `nc`, `parquet`, `zip`, …) that picks a default loader; inferred from the URI when absent. |
| `extract` | After download, unpack the archive and use the extracted directory as the path. |
| `doi` | DOI of the dataset (also a lookup key). |
| `aliases` | Alternative names to look the dataset up by. |
| `version` | Dataset version; part of the storage key, so versions coexist on disk. |
| `requires` | Names of datasets to fetch first (a dependency graph, resolved in order). |
| `description` | Human-readable note (replaces TOML comments). |
| `storage_path` | Where the dataset lives on disk (overrides the default `$datasets_dir/$key`) — see [Storage](#storage). |
| `skip_checksum` / `skip_download` | Disable verification / treat as externally provided. |
| `fetcher` / `loader` / `shell` | How to obtain/load it — see [Language bindings](#language-bindings). |

```toml
# A DOI archive: downloaded, checksum-verified, then unpacked.
[herzschuh2023]
uri         = "https://doi.pangaea.de/10.1594/PANGAEA.930512?format=zip"
sha256      = "4e40e43ac0f1ddea125cb5314eee46e332aacbcb18aff7efbf59f1d8b1d84a13"
doi         = "10.1594/PANGAEA.930512"
format      = "zip"
extract     = true
description = "Pollen-based climate reconstructions (Herzschuh et al., 2023)"
```

A dataset key may contain a slash if quoted: `["jesstierney/lgmDA"]`.
*Normative: [SCHEMA.md §Language-agnostic contract](../SCHEMA.md#language-agnostic-contract-common-fields).*

---

## Language bindings

By default a dataset is fetched by downloading its `uri` and loaded by its `format`'s
built-in loader. To customize either, attach **bindings**. All executable references are
`module:function` references — **never inline code**, in any language.

### Binding forms: string or table

Every binding takes one of two interchangeable forms:

```toml
loader = "mypkg.loaders:load_sst"                       # string
loader = { ref = "mypkg.loaders:load_sst",             # table (parameterized)
           args = ["$path"], kwargs = { decode = false } }
```

The string is an **alias** for the ref-only table (`"M:f"` ≡ `{ ref = "M:f" }`). Call
semantics follow the *arguments*, not the syntax: with no `args`/`kwargs` the tool makes its
**conventional call** (a loader receives the dataset path; a fetcher the standard fetch
context); with `args`/`kwargs` the call is **explicit** — `ref(*args; kwargs...)`, nothing
auto-injected, runtime values passed via `$var` substitution (`$path`, `$download_path`, …).
A writer emits the **string** whenever there are no arguments. *Normative:
[SCHEMA.md §Binding forms](../SCHEMA.md#binding-forms-string-or-table).*

### Where bindings live

```toml
# Per-dataset, language-explicit:
[ocean_temp._LANG.python]
loader = "mypkg.loaders:load_argo"
[ocean_temp._LANG.julia]
loader = "MyPkg:load_argo"

# Project-wide format defaults, per language (format -> binding):
[_LANG.python.loaders]
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"
```

`shell` is the **language-agnostic** fetcher — a command template (the *same* command for
every tool), so it sits directly on the dataset:

```toml
[model_output]
format = "nc"
shell  = "make model_output OUTPUT=$download_path"
```

### Language-implicit (bare) bindings

A single-language project can skip the `_LANG.<lang>` wrapper entirely. A **bare**
`fetcher`/`loader` on the dataset, and a top-level `[_LOADERS]` format map, are read as
bindings in the **running tool's own language**:

```toml
[ocean_temp]
uri    = "https://example.com/argo.nc"
format = "nc"
loader = "mypkg.loaders:load_argo"     # bare = own language; no [._LANG.python]
```

Precedence: an explicit `[<ds>._LANG.<self>]` binding overrides the bare one, and
`[_LANG.<self>.loaders]` overrides `[_LOADERS]`. Bare bindings are the single-language
form; **multi-language manifests use explicit `[<ds>._LANG.<lang>]`** (which other languages
correctly skip). *Normative:
[SCHEMA.md §Language-implicit bindings](../SCHEMA.md#language-implicit-bindings-bare-fetcher--loader).*

---

## Resolution: the fetch and load ladders

At runtime each tool collapses the bindings to one effective **fetcher** and **loader** per
dataset, trying rungs in order.

**Fetch ladder:** own-language fetcher (explicit `_LANG.<self>` > bare `fetcher`) → `shell`
command → cross-language fetch (rung 3) → `uri` download → error.

**Load ladder:** own-language loader (explicit > bare) → manifest format default
(`_LANG.<self>.loaders` > `_LOADERS`) → built-in format default → error.

**Fail-loud (spec-v3.6).** A binding that is **present** for the running language (bare or
explicit `_LANG.<self>`) and fails to **resolve** is an **error**; one that resolves and
then **raises** propagates. There is no silent fall-through to a different loader/fetcher.
The ladder falls through **only** to skip rungs that are *absent* for the running language
(e.g. another language's `_LANG.<other>` fetcher). *Normative:
[SCHEMA.md §Resolution semantics](../SCHEMA.md#resolution-semantics).*

**Cross-language fetch (rung 3)** is the rare case: a dataset whose bytes can be produced
only by a fetcher in another language. The running tool delegates (mechanism
implementation-defined; the Python CLI is the reference peer), controlled by `delegate` /
`--delegate`. Loading never delegates — a live object can't cross a process boundary.
*Normative: [SCHEMA.md §Cross-language fetch](../SCHEMA.md#cross-language-fetch-rung-3).*

---

## Storage

Storage is **two paths**: where fetched datasets go and where the produced cache goes. Both
are set in `[_STORAGE]` and **default to local, repo-relative folders**, so a casual user gets
`./datasets/` and `./cached/` with no configuration.

```toml
[_STORAGE]
datasets_dir  = "datasets"        # fetched datasets (default; relative -> <repo>/datasets/)
datacache_dir = "cached"          # produced cache   (default; relative -> <repo>/cached/)
scratch       = "/scratch/$USER"  # a reusable $-symbol -> $scratch

[_STORAGE._HOST."login*.hpc.edu"]
scratch       = "/work/$USER"     # host-specific symbol value (glob on hostname)
datacache_dir = "$scratch/cache"  # a field, host-specific

[big]
uri        = "https://example.com/big.nc"
storage_path = "$scratch/$key"      # this dataset, parked on scratch ($key => tool-managed)
```

- **Paths default local.** Relative ⇒ relative to the project root (`$repo`). A fetched
  dataset lands at `<datasets_dir>/<key>`, a produced artifact at
  `<datacache_dir>/<cachetype>/[<version>/]<hash>/`. No scope, no prefix, no derived name —
  the folder you set **is** the location.
- **Symbols.** A path may use `$`-symbols: predefined **`$user_data_dir`** / **`$user_cache_dir`**
  (the machine's data/cache dirs, straight from `platformdirs`) and **`$repo`**; any other
  bare `[_STORAGE]` key is a user-defined symbol, made host-specific in `[_STORAGE._HOST]`.
  `$USER`/env and `~` also expand.
- **Centralize / share** across clones or projects with one edit:
  `datasets_dir = "$user_data_dir/myproj"`, `datacache_dir = "$user_cache_dir/myproj"`.
- **Per-dataset `storage_path`** overrides where one dataset lives (default `$datasets_dir/$key`):
  contains `$key` ⇒ tool-managed/keyed; an exact path without `$key` ⇒ user-managed and never
  touched by maintenance. (It is *not* called `path` — that is the URI's parsed component.)
- **Environment:** two overrides — `DATAMANIFEST_DATASETS_DIR` / `DATAMANIFEST_DATACACHE_DIR`
  (user symbols override as `DATAMANIFEST_<NAME>`); `$user_data_dir`/`$user_cache_dir` keep
  their per-OS resolution.
- **Concurrency:** writes are atomic (temp + rename) under a `.lock` pidfile with a
  `.complete` marker, so concurrent readers never see a half-materialized dataset.

*Normative: [SCHEMA.md §Storage](../SCHEMA.md#storage).*

---

## Produced datasets and caching

Beyond *fetching* declared datasets, a tool with the `cache-produce` capability can
*produce-or-load*: cache the result of a project function on disk, keyed by its parameters
(the `@cached` decorator/macro in both implementations).

- **Parameter-hash keying.** The cache key is the lowercase-hex **SHA-256 of the canonical
  JSON** (JCS / RFC 8785) of the function's hash-affecting keyword parameters. Canonical JSON
  is cross-tool reproducible. Hash inputs are strings, integers, **finite floats**, booleans,
  and arrays/objects of those — finite floats use the normative Python `json.dumps` form
  (`1.0`→`1.0`); `NaN`/`±Inf` and nulls are disallowed.
- **Self-describing artifacts.** Alongside each artifact sit two sidecars:
  `config.toml` (the re-hashable key table plus a `[_META]` block with `cachetype` and
  `hash`) and `metadata.toml` (provenance — timestamp, tool, git, host/user; never hashed,
  never an authority for validity). A tool MUST recompute the hash from `config.toml` and
  treat a mismatch as **not** a cache hit.
- **Layout:** `<datacache_dir>/<cachetype>/[<version>/]<hash>/<basename>.<ext>`.
  The optional **`version`** is a human-set recipe/code version — a path segment that does
  **not** enter the hash, used to prevent a stale cross-branch hit.
- **The `cached.toml` index** registers each produced dataset by its portable
  `cachetype` + `hash` key (never an absolute path) — the `Manifest.toml` analogue. It is
  gitignored per-machine by default; a project wanting reproducible shared caches may commit it.

```toml
# config.toml — written next to the artifact
grid        = "5x5"
skip_models = ["CESM.*", "FGOALS.*"]

[_META]
schema    = 1
cachetype = "esm_20c_anomaly"
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
```

*Normative: [SCHEMA.md §Produced datasets and caching](../SCHEMA.md#produced-datasets-and-caching-companion-layer).*

---

## Maintenance (inspect)

Both fetched and produced objects accumulate, so a tool with the `inspect` capability can
enumerate the store, filter it, and delete an explicit selection. Each object exposes
`kind` (`data`/`cached`), `key`/`hash`, `location`, `referenced` (rooted by a present
`.toml`, or an **orphan**), `format`, `size`, `created`, and a best-effort
`last-access`.

Maintenance is **user-driven, never automatic** — there is no garbage collector; deletion is
always an explicit selection (dry-run/confirm by default). `referenced` and `last-access` are
**advisory** filter inputs, not deletion authorities. `last-access` is read from the
filesystem (`stat`) at inspect time and **never written on read**, so it is coarse and may be
unknown (`noatime`/`relatime`); `created` is the always-available age signal.

*Normative: [SCHEMA.md §Maintenance](../SCHEMA.md#maintenance-inspect-filter-delete).*

---

## Cross-machine sync

A tool with the `sync` capability moves a stored object between two machines instead of
re-downloading or recomputing it. Each object has a machine-independent address — a fetched
dataset by `name`/`alias`/`doi`, a produced artifact by `cachetype[/version]/hash` — so only
the physical root differs per host.

- Transport is **rsync over SSH**; the SSH target is both transport and host identity (no
  remote registry).
- The remote root is resolved best-effort from the remote's own environment, then its
  `[_STORAGE._HOST]` rules, then the shared default. `$repo` (project-relative) is not syncable.
- Sync **writes no manifest** — a transferred object lands as an orphan (present,
  unreferenced) and is immediately usable; it is **idempotent**.

*Normative: [SCHEMA.md §Cross-machine sync](../SCHEMA.md#cross-machine-sync).*

---

## Conformance and versioning

Two version axes (see [SCHEMA.md §Versioning](../SCHEMA.md#versioning)):

- **`_META.schema`** — the data-model version (always **1** today). A reader rejects a
  schema it doesn't understand.
- **Spec tag** (`spec-v4`, …) — the document/behavior revision. Carried by git tags and by
  the JSON Schema filenames in [`schemas/`](../schemas/); older versions stay alongside.

A tool advertises **capabilities** and runs only the shared conformance fixtures whose
capability set it supports:

| Capability | What it adds |
|---|---|
| `lang-read` / `lang-write` | Read/regenerate own `_LANG` bindings, preserve foreign ones verbatim |
| `shell-fetch` | Execute the `shell` command template |
| `delegation` | Cross-language fetch (rung 3) |
| `storage` | `datasets_dir`/`datacache_dir` + `$`-symbols + `[_STORAGE]` host-aware resolution |
| `byte-identity` | Canonical key ordering across tools |
| `binding-args` | The `{ ref, args, kwargs }` table binding form |
| `cache-produce` | Produced datasets + `config.toml`/`metadata.toml` sidecars |
| `inspect` | Store enumeration, filter, delete/move |
| `sync` | Cross-machine `push`/`pull` |

The machine-checkable fixtures live in [`tests/fixtures/`](../tests/fixtures/); both
implementations pin and run them. *Normative:
[SCHEMA.md §Conformance levels](../SCHEMA.md#conformance-levels).*

---

## Migration and deprecations

Legacy v0 forms are still **read** but should not be **written** by current tools: the flat
language-named fields `julia=` / `python=` / `callable=` (which historically held inline
code, now forbidden) are tolerated on read and rewritten into `[<ds>._LANG.<lang>]` by an
opt-in `migrate` command; `julia_modules` / `python_includes` are retired. Note that bare
`fetcher`/`loader`, bare `shell`, and `[_LOADERS]` are **supported** forms, not deprecated.
*Normative: [SCHEMA.md §Deprecations](../SCHEMA.md#deprecations).*
