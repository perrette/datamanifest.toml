# `datamanifest.toml` — manifest schema specification

This document is the normative description of the TOML manifest format shared by the
[DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) (Julia) and
[datamanifest](https://github.com/perrette/datamanifest) (Python) tools. A manifest
declares the data dependencies of a project: each dataset's source URI, checksum,
version, format, and how to fetch and load it. Either implementation can read and write a
conforming file; each reads the language-agnostic contract fields plus its own
`_LANG`-namespaced bindings, and preserves the rest verbatim.

## Versioning

Two independent version axes govern this format:

- **`_META.schema`** (integer, stored inside the file) is the **data-model compatibility
  version**. It increments only on a breaking structural change. A file without `[_META]`
  is treated as schema v0 (legacy flat) and read leniently. Current value: **1**.
- **Spec-document version** (a git tag such as `spec-v1.0`) versions the prose,
  examples, and fixture suite. An implementation conforming to "schema 1, spec ≥ v1.0"
  pins to a spec tag; the spec may advance without retroactively breaking a pinned
  implementation. The spec is never forked per language package: one normative document,
  one fixture suite, multiple implementations at varying capability levels.

## Structural keys

Keys beginning with `_` are **structural** — they are not dataset tables. At the top
level, the defined structural tables are `_META`, `_LANG`, `_STORAGE`, and the legacy `_LOADERS`.
Within a dataset table, the only defined structural sub-table is `_LANG`. Readers MUST
preserve unknown `_*` keys verbatim and MUST NOT treat them as datasets or drop them on
write.

## Top-level layout

A v1 manifest is a TOML document with:

- **`[_META]`** — schema metadata (`schema = 1`).
- **`[_LANG.<lang>]`** — project-wide execution-context configuration for language
  `<lang>`. The sub-key `loaders` is a `format → ref` map of default loaders for that
  language.
- **One table per dataset**, keyed by the dataset name. Dataset tables hold the
  language-agnostic contract fields and an optional `_LANG` sub-table for per-dataset
  bindings.
- **`[_STORAGE]`** — optional storage configuration: a host-aware namespace of **folder
  variables** (built-in `data`, `cache`, `repo` plus user-defined keys) and the
  project-wide `default` selector, with `_HOST` / `_PROFILE` override sub-tables. See Storage.
- **Legacy `[_LOADERS]`** — preserved for backward compatibility; see Deprecations.

Example:

```toml
[_META]
schema = 1

[_LANG.python.loaders]
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"

[_LANG.julia.loaders]
csv = "CSV:read"
nc  = "NCDatasets:Dataset"

[foo]
uri    = "https://example.com/foo.csv"
sha256 = "abc123"
format = "csv"

[bar]
sha256 = "def456"
format = "nc"

[bar._LANG.julia]
fetcher = "MyPkg:build_bar"
loader  = "MyPkg:load_bar"

[bar._LANG.python]
fetcher = "mypkg.build:bar"
loader  = "mypkg.load:bar"

[bar._LANG.shell]
fetcher = "make-bar -o $download_path"
```

## Language-agnostic contract (common fields)

Every field is optional and defaults to the empty string / empty list / `false` shown.
Types are TOML types (`string`, `array of string`, `bool`).

| Field | Type | Default | Semantics |
|---|---|---|---|
| `uri` | string | `""` | Single source URI. HTTP(S), `git`/`ssh+git`/`*.git`, `ssh`/`sshfs`/`rsync`, or `file://`. Mutually exclusive with `uris`. |
| `uris` | array of string | `[]` | Batch of source URIs written into a single dataset folder under disambiguated relative paths. Mutually exclusive with `uri`. |
| `host` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `path` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `scheme` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `version` | string | `""` | Dataset version; participates in the storage key so multiple versions coexist on disk. |
| `branch` | string | `""` | For git sources: branch/tag to clone (`--branch`). |
| `doi` | string | `""` | DOI of the dataset; also usable as a search key. |
| `aliases` | array of string | `[]` | Alternative names this dataset can be looked up by. |
| `description` | string | `""` | Human-readable description (replaces TOML comments). |
| `key` | string | `""` | Storage key (relative path under the datasets folder). Derived from host + path + version when absent. |
| `local_path` | string | `""` | **Path expression** for a user-managed exact location; may interpolate `$`-folder variables, `$USER`/env, and `~`. After interpolation: absolute → used verbatim; relative → resolved against the project root. Bypasses the keyed `<root>/<key>` layout and download. See Storage. |
| `store` | string | `default` | **Selector** choosing the folder the dataset is materialized into: a `$`-folder reference, optionally with a sub-path (`$data`, `$scratch`, `$cache/sub`). The dataset is keyed under it as `<resolved-folder>/<key>`. Omitted ⇒ the project-wide `[_STORAGE].default` selector (itself `$data`). See Storage. Honored under the `storage` capability; other tools preserve it verbatim. |
| `sha256` | string | `""` | Expected SHA-256 of the downloaded file/folder. Auto-filled on first successful download and verified at fetch time; **not** re-verified on every load (re-verification is opt-in). |
| `skip_checksum` | bool | `false` | Disable checksum verification for this dataset. |
| `skip_download` | bool | `false` | Treat the dataset as externally provided; the documented `uri` is returned as the path and no download is attempted. |
| `delegate` | bool | *(run default)* | Force the cross-language fetch rung (rung 3) on (`true`) or off (`false`) for this dataset. When omitted, the tool's run-level default applies (`--delegate` / configuration). Honored under the `delegation` capability; other tools preserve it verbatim. See Cross-language fetch. |
| `extract` | bool | `false` | After download, extract the archive (`zip` / `tar` / `tar.gz`) and use the extracted directory as the dataset path. |
| `format` | string | `""` | Data format hint used to pick a default loader (`csv`, `parquet`, `nc`, `json`, `yaml`, `toml`, `md`, `txt`, `zip`, `tar`, `tar.gz`, …). Inferred from the URI when absent. |
| `requires` | array of string | `[]` | Names of datasets that must be downloaded before this one; defines a dependency graph resolved in topological order. |

## Language bindings (`_LANG`)

Executable bindings live under a structural `_LANG` namespace, keyed by language tag
(`python`, `julia`, `r`, `shell`, …). The dataset table itself stays fully agnostic.

All executable references are **`module:function` references** — never inline code, in
any language. A local module is importable because the manifest's directory (the project
root) is on the language tool's import path by convention. There are no `includes` or
`modules` fields in v1. A binding may additionally carry **arguments as data**
(`args` / `kwargs`); these are passed to the referenced function and are never
interpreted as code (see Parameterized bindings).

### Per-dataset bindings

`[<dataset>._LANG.<lang>]` holds singular bindings for a specific dataset in language
`<lang>`. Both keys are optional. Each binding is either a **string** — a bare
`module:function` ref — or a **table** carrying the ref plus arguments (see Parameterized
bindings).

| Key | Type | Semantics |
|---|---|---|
| `fetcher` | string \| table | `module:function` ref (or `{ ref, args }` table) called to produce the dataset bytes, instead of (or in addition to) downloading the `uri`. |
| `loader` | string \| table | `module:function` ref (or `{ ref, args }` table) called to load the dataset into memory, overriding the format default. |

#### Parameterized bindings (`ref` + `args` / `kwargs`)

A binding may be written as a table so one function is reused across datasets that differ
only in arguments — the same loader called with `grid = "5x5"` for one dataset and
`grid = "10x10"` for another:

```toml
[esm_5x5._LANG.julia.loader]
ref    = "MyPkg:load_esm"
args   = ["$path"]                                     # positional, in order
kwargs = { grid = "5x5", skip_models = ["CESM.*"] }    # keyword

[esm_10x10._LANG.julia.loader]
ref    = "MyPkg:load_esm"
args   = ["$path"]
kwargs = { grid = "10x10" }
```

| Key | Type | Semantics |
|---|---|---|
| `ref` | string | The `module:function` reference (required). |
| `args` | array | Positional arguments, in order (optional). |
| `kwargs` | table | Keyword arguments (optional). |

- `args` and `kwargs` are **plain data** (string, number, bool, array, table) — never
  code. `args` is an ordered list of positional values; `kwargs` keys become keyword
  parameters. Values map to each language's native types.
- The table form is **explicit**: the tool calls `ref(*args; kwargs...)` and does **not**
  auto-inject any standard value. Runtime values are referenced by **`$var` substitution**
  in string values — the same variables the `shell` fetcher exposes (`$key`, `$version`,
  `$doi`, `$format`, `$branch`, `$uri`, `$project_root`; `$download_path` for fetchers,
  `$path` — the resolved dataset path — for loaders). (The bare-string form keeps the
  tool's conventional call: a loader receives the dataset path, a fetcher the standard
  fetch kwargs.)
- **Type mapping is language-neutral.** A value with no TOML type — e.g. a Julia `Symbol`
  — is written as its plain string form (`weighting_method = "model"` for `:model`); the
  target function accepts the string (or coerces it at its boundary). A binding's
  arguments MUST be representable as TOML data.
- A tool that executes `<lang>` bindings but does not implement the `binding-args`
  capability MUST **error** when it encounters `args`/`kwargs`, rather than silently
  calling the function without them (which would change results). The bare-string form
  requires no such capability.
- For canonical serialization, `kwargs` keys are emitted in lexicographic order like all
  other keys (including inside an inline `{ }` table); `args` is an **ordered array**, so
  its element order is preserved as data (arrays are never reordered). Both therefore carry
  the same key order and element order across tools — **semantically identical** (and
  byte-identical via the canonical reference form; see the `byte-identity` capability).

### `shell` execution context

`shell` is an execution context with a `fetcher` only — there is no `loader` for
`shell`, because a subprocess cannot return a live in-memory object. The `fetcher`
value is a command template that supports variable substitutions: `$download_path`,
`$project_root`, `$uri`, `$key`, `$version`, `$doi`, `$format`, `$branch`,
`$path_<ref>`, `$path_<i>`, `$requires_paths`.

### Project-wide loaders

`[_LANG.<lang>.loaders]` is a `format → ref` map of project-wide default loaders for
language `<lang>`. It applies when a dataset has no per-dataset `loader` for that
language. Note the singular `loader` key per dataset vs. the plural `loaders` format
map at the top level.

## Resolution semantics

At runtime, each language tool collapses the `_LANG` tree to a single effective
**fetcher** and **loader** for each dataset. The full `_LANG` tree is retained
internally for lossless round-trip.

### Fetch ladder

The tool tries each rung in order, using the first that applies:

1. `[<dataset>._LANG.<self>].fetcher` — in-process call (own language, fastest);
2. `[<dataset>._LANG.shell].fetcher` — run the command template (cheap subprocess);
3. **cross-language fetch** — the rare case: run a fetcher defined in another language
   (mechanism implementation-defined; the Python CLI can serve as a fallback), controlled
   by `delegate` / `--delegate`; see Cross-language fetch below;
4. plain `uri` download (if `uri` is set);
5. else error.

### Load ladder

The tool tries each rung in order:

1. `[<dataset>._LANG.<self>].loader`;
2. `[_LANG.<self>.loaders][<dataset>.format]` — manifest-configured format default;
3. the tool's built-in default loader for `<dataset>.format`;
4. else error.

**Load never delegates.** A loader returns a live in-memory native object, which cannot
cross a process boundary. Cross-language data preparation is modeled as one language's
*fetcher* writing a normalized artifact (Arrow/parquet/netcdf) that another language
then loads with its own format default.

### Cross-language fetch (rung 3)

Reached **only** in the rare case that a dataset has no fetcher in the running tool's own
language, no `shell` fetcher, and no `uri` — its bytes can be produced only by a fetcher
defined in another language (`[<ds>._LANG.<other>].fetcher`). Native / `shell` / plain
`uri` cases never reach here, so each implementation is self-sufficient for nearly all
datasets.

**How a tool runs a foreign fetcher is implementation-defined.** It MAY invoke that
language's runtime directly (e.g. `julia --project=<env> -e '…'`, writing to
`$download_path` and materializing the result itself), MAY delegate to a peer-language
`datamanifest` CLI (see Peer-CLI contract), or MAY skip the rung. The **Python
implementation is the reference** and aims to cover every language, so a tool with no
native way to run a foreign fetcher can simply **call the Python CLI as a fallback**.

Either way it moves bytes on disk only (load never crosses languages); a tool MUST fall
through to `uri` when the needed toolchain is absent; and it applies to fetched datasets
only — produced (`@cached`) datasets are not cross-language. Gated by the `delegation`
capability; the `delegate` field / `--delegate` toggles it.

## Storage

A dataset's bytes are materialized at `<resolved-folder>/<key>`. A dataset's `store`
**selector** chooses the folder; the optional top-level `[_STORAGE]` table is a host-aware
namespace of **folder variables** that resolve those selectors to concrete paths. Storage
is a portable *location* layer: a selector carries the same meaning in every
implementation, and the built-in folders resolve to language-independent default paths so
peer tools share the same on-disk location without configuration.

The core knows **locations only — no lifetime policy.** `data` and `cache` are distinct
*places* (one persistent, one on the OS-reclaimable cache dir), but the core enforces
nothing about how long bytes persist. Disposability and garbage collection of *produced*
datasets are the concern of the companion produce-or-load layer (see *Produced datasets and
caching*), not of the core fetch engine.

### Folder variables

A **folder** is a named location, referenced as a `$`-variable. There is one namespace,
with three built-in members and any number of user-defined ones:

| Folder | Default location | Nature |
|---|---|---|
| `$data` | `platformdirs.user_data_dir("datamanifest")` + `/Datasets` | persistent, protected |
| `$cache` | `platformdirs.user_cache_dir("datamanifest")` + `/Datasets` | OS-reclaimable *location* — no core lifetime policy |
| `$repo` | `<project_root>/datasets` | project-relative; travels with the repo |

- **Built-in folders** are exactly those with an unambiguous OS convention. Temp / scratch
  / state directories have no single canonical home (`/tmp` vs `$TMPDIR` vs
  `/scratch/$USER` vs the runtime dir) and are therefore **not** built-in; express them as
  user-defined folder variables instead.
- **User-defined folders** are any other key under `[_STORAGE]` (e.g. `scratch = "…"`
  defines `$scratch`). The reserved keys `default`, `_HOST`, and `_PROFILE` are not folder
  variables.
- **Definition vs reference.** A folder is *defined* with a **bare** key in `[_STORAGE]`
  (`scratch = "/scratch/$USER/datasets"`); it is *referenced* with **`$`**
  (`store = "$scratch"`). References always use `$` — there are no bare folder names
  anywhere (selectors included), which removes any ambiguity between a folder alias and a
  literal string.

**Default root locations are language-independent.** A conforming tool MUST resolve the
built-in folders to the OS-convention paths above and MUST NOT substitute a language-native
location (e.g. a package depot), so Python and Julia resolve the same dataset to the
**same path**. **Python's `platformdirs` is the normative reference**: `$data` =
`platformdirs.user_data_dir("datamanifest")` + `/Datasets`, `$cache` =
`platformdirs.user_cache_dir("datamanifest")` + `/Datasets`. `user_data_dir` already
appends the `datamanifest` app segment — `$XDG_DATA_HOME/datamanifest` (default
`~/.local/share/datamanifest`) on Linux, `~/Library/Application Support/datamanifest` on
macOS, `%LOCALAPPDATA%\datamanifest` on Windows — and likewise `user_cache_dir`
(`$XDG_CACHE_HOME/datamanifest`, default `~/.cache/datamanifest`, on Linux). Every other
implementation MUST resolve to the identical path `platformdirs` produces for that OS.
(Datasets thus live under `<app-dir>/Datasets/<key>`, leaving the rest of `<app-dir>` free
for a tool's own app-internal files — e.g. HTTP request metadata — without collision.)

### Two field kinds

Every storage-related value is one of two kinds:

- **Selectors** — `[_STORAGE].default` (project-wide; **new in spec-v2**) and a dataset's
  `store`. A selector is a `$`-folder reference, optionally followed by a literal sub-path:
  `default = "$data"`, `store = "$scratch"`, `store = "$cache/sub"`. A selector
  `$<folder>[/<subpath>]` resolves to `<resolved-folder>[/<subpath>]`, and the dataset's
  bytes land at `<resolved-folder>[/<subpath>]/<key>`. A dataset's `store` defaults to the
  project's `default`; `default` itself defaults to `$data`. The dataset's storage **key**
  (see `key`) is independent of its selector, so the same dataset resolves to
  `<root>/<key>` under whichever folder is selected.
- **Path expressions** — `[_STORAGE]` folder-variable values and `local_path`. A path
  expression is a full path that may interpolate `$`-folder variables, `$USER`/env vars,
  and `~`. `local_path` bypasses the keyed `<root>/<key>` layout (it is an exact location).

Selectors reference a *folder variable* only (so the `<root>/<key>` layout is
well-defined); path expressions may interpolate anything. In a path expression `$NAME` /
`${NAME}` expands to the folder variable `NAME` if one is defined, otherwise to the
environment variable `NAME`; `~` expands to the home directory. A user-defined folder
variable MUST NOT reference itself.

### Host-aware resolution (`[_STORAGE]`)

`[_STORAGE]` defines folder variables and the `default` selector; per-host and per-profile
overrides are expressed as sub-tables:

```toml
[_STORAGE]
default = "$data"                       # project-wide default selector ($-form)
scratch = "$TMPDIR/datasets"            # user-defined folder variable (host-independent here)

[_STORAGE._HOST."login*.hpc.edu"]       # matched against the hostname (glob/regex)
scratch = "/scratch/$USER/datasets"     # same variable, host-specific resolution
data    = "/work/$USER/Datasets"        # override a built-in's location, host-specific

[_STORAGE._PROFILE.cluster]             # selected by an implementation-defined profile signal
data = "/work/proj/Datasets"
```

Normative rules:

- `[_STORAGE]` and its `_HOST` / `_PROFILE` sub-tables are **defined structural keys**:
  every conforming tool MUST parse them identically and preserve them verbatim on write
  (a tool without the `storage` capability treats the whole table as a preserved unknown).
- **Selectors MUST be `$`-references.** A bare folder name (the spec-v1.1 form,
  `store = "data"`) is **not** a valid selector; a spec-v2 `storage` tool MUST reject it.
  This is a hard migration — there is no legacy-alias read of bare names. (Bare keys appear
  only as folder *definitions* in `[_STORAGE]`.)
- **Host-specificity is always a property of a folder variable's resolution**, never a
  per-dataset host map. A machine-specific exact path is a `local_path` that interpolates a
  host-resolved variable (`local_path = "$scratch/exact/file.nc"`); there is **no**
  per-dataset `_HOST` table.
- **Resolution ladder (normative).** Every folder variable — built-in and user-defined
  alike — resolves through the same ladder; the first rung that applies wins:
  1. the `DATAMANIFEST_<NAME>_DIR` environment variable (`<NAME>` upper-cased:
     `DATAMANIFEST_DATA_DIR`, `DATAMANIFEST_CACHE_DIR`, `DATAMANIFEST_SCRATCH_DIR`, …);
  2. the `[_STORAGE._PROFILE.<profile>].<name>` entry when `DATAMANIFEST_PROFILE` is set;
  3. the first matching `[_STORAGE._HOST.<pattern>].<name>` entry (hostname glob/regex);
  4. the base `[_STORAGE].<name>` definition;
  5. the built-in default (the table above) for `data` / `cache` / `repo`. A user-defined
     name with no definition on any rung is an error.

  Host-specificity therefore lives entirely in *resolving the variable* — defined once,
  centrally — and applies uniformly to `store` selectors and `local_path` interpolation.
  Every tool MUST honor these variable names and this precedence, so a single environment
  moves all tools to the same path.
- **Read resolution.** A dataset is materialized at, and read from, its resolved `store`
  selector (`<resolved-folder>[/<subpath>]/<key>`). If the entry is absent there, a tool
  SHOULD additionally probe the **built-in** folders in the fixed order `repo`, `data`,
  `cache` and use the first where `<root>/<key>` exists, so a dataset materialized under a
  different folder (or by a peer tool) still resolves. Explicit paths, where given, replace
  the corresponding default and MUST be honored identically by every tool.
- **Legacy read-only location (non-normative, transitional).** Implementations whose
  pre-spec-v1.1 default datasets folder was the un-namespaced `$XDG_CACHE_HOME/Datasets`
  (i.e. without the `datamanifest/` segment that `platformdirs` adds) SHOULD probe that
  path **last** and **read-only**, so datasets downloaded by older versions still resolve.
  New writes MUST go to the resolved folder, never to the legacy path; the probe is skipped
  when `DATAMANIFEST_DATA_DIR` is set (an explicit user choice). A tool SHOULD warn once
  when it reads from the legacy path. This is a back-compat aid, not part of the normative
  cross-tool contract.

> **Note — the `$cache` *folder* is not the `@cached` *mechanism*.** `store = "$cache"`
> selects a *location* (the OS-reclaimable cache dir) and is independent of *how* a dataset
> is produced. In particular it is unrelated to the companion produce-or-load (`@cached`)
> layer that caches *function results* and registers them in its own `cached.toml` index
> (see *Produced datasets and caching*). Any dataset, fetched or produced, may use any
> folder.

### Concurrent access and completeness

A folder may be shared between tools and between concurrent processes (e.g. HPC jobs), so
materialization MUST be safe under concurrency, and peer tools sharing a folder MUST agree
on these conventions:

- **Atomic publish.** Materialize into a temporary path within the folder and atomically
  rename it into place (`<key>.tmp` → `<key>`), so a killed process never leaves a partial
  entry that looks complete.
- **Completion marker.** An entry is *complete* iff its marker exists —
  `<key>/.complete` for a directory, `<key>.complete` for a file. Readers MUST treat an
  entry without its marker as absent (re-fetch); a writer MUST create the marker only
  after a successful, verified materialization.
- **Lock.** A writer SHOULD hold an exclusive lock `<key>.lock` (a pidfile; a lock whose
  PID is dead and older than a grace period MAY be reclaimed) while materializing, so
  concurrent workers neither recompute nor clobber the same entry.

## Produced datasets and caching (spec-v2.1, companion layer)

> **Spec-v2.1 — a companion *layer*, not a core capability.** The produce-or-load
> (`@cached`) layer sits **outside the core fetch engine** as a distinct capability layer
> built on the shared substrate it reuses (safe-materialization, folder resolution,
> loaders). This section is the cross-tool **format** spec for that layer — it stays in
> this document so both languages agree on the on-disk shape.
>
> **Packaging is not constrained by this spec.** Whether an implementation ships the layer
> as a **separate package** that depends on the core, or as an **optional module of the
> same package**, is the implementation's choice (spec-v2 over-specified this as a separate
> package; spec-v2.1 relaxes it). What the spec fixes is the **boundary**: the
> `cache-produce` / `cache-gc` capabilities are **never declared by the core fetch
> capability**, and **the core fetch engine keeps no garbage collection and no disposability
> policy**.
>
> The format is **additive over a `datasets.toml`**: it adds **no field to the
> hand-authored `datasets.toml`** and does not change its `_META.schema` (still **1**). A
> produced dataset reuses the existing **engine** — the storage model, the
> safe-materialization primitive, and the load ladder — but is **not declared in
> `datasets.toml`**; its only on-disk record is the machine-generated `config.toml` /
> `metadata.toml` sidecars and the `cached.toml` index, each carrying its own
> `_META.schema = 1`. The format is gated by two independent capabilities, `cache-produce`
> and `cache-gc`, so a companion may ship neither, one, or both.

A **produced dataset** is one whose bytes come from running a project function rather
than downloading a `uri`. It is the same "recipe + key + store + policy" object as a
fetched dataset; the distinction is purely two slots:

- the **recipe** — a `uri`/`shell`/`git` recipe with a source-identity key, versus a
  *function* recipe with a *parameter-hash* key;
- the **authorship** — a fetched dataset is **hand-authored** in `datasets.toml`; a
  produced dataset is **machine-generated**.

Everything else — stores, `store=`, the safe-materialization primitive, loaders, the
preservation contract — is recipe-agnostic and applies unchanged. The only new
normative axis is **parameter-hash keying** and its on-disk bookkeeping.

**A produced dataset has no entry in `datasets.toml`.** It originates from a function
that a tool exposes through its produce-or-load surface (the `@cached` decorator /
macro — per-language and non-normative; see below), and is recorded only after it
runs. `cachetype` is therefore **not** a `datasets.toml` field; it is a namespace that
appears solely in the machine-generated records — the `cached.toml` index entry, the
`config.toml` `[_META]` block, and the on-disk path. A conforming fetch path
(`download_dataset` and the fetch ladder) **never encounters a produced dataset**: the
two concerns share the *engine*, not the *manifest*. This keeps `datasets.toml` clean
(the `Project.toml` analogue) and confines produced, parameter-hash-keyed churn to
`cached.toml` (the `Manifest.toml` analogue).

A produced dataset is identified **by its keyword parameters**, not by content: its
storage **key** is `<cachetype>/<param-hash>`, its parameters *are* the hash inputs,
and the `config.toml` sidecar is the re-checkable record of those inputs (it is not
content-pinned by a manifest `sha256`). It defaults to **`store = "$cache"`** (the
producing mechanism sets the default; an explicit override still wins), because a
produced artifact is the textbook reconstructible cache.

> **Keyword-only.** Because the parameters double as identity, the producing function
> is **keyword-only** for hashing: an ordered positional argument list has no stable
> name→value identity to hash, so a `cache-produce` tool MUST derive the key table from
> keyword parameters only. This is a property of the produce-or-load *surface*, not a
> `datasets.toml` rule — fetched datasets keep their positional `args` per spec-v1.1.

### Parameter-hash keying

A produced dataset's identity is `(cachetype, hash-of-its-parameters)`. The
**hash inputs** are the producing function's hash-affecting keyword parameters as a
**key table**: a mapping parameter name → value. Parameters split three ways
(normative — the split, not the exact source mapping):

| Class | In the hash? | Stored where | Example |
|---|---|---|---|
| **hash-affecting params** | yes | `config.toml` sidecar | `grid = "5x5"` |
| **runtime knobs** (`_`-prefixed keys) | no | nowhere (transient) | `_parallel = true` |
| **audit-only extras** | no | `metadata.toml` sidecar | producing git commit |

How a tool derives the key table from a function's declared keyword parameters
(signature introspection, an explicit key selector like LGMIO's `key=(args -> (;…))`,
etc.) is **implementation-defined**; the **serialization and hash are normative** so
the same parameters yield the same key everywhere:

1. Build the key table from the hash-affecting keyword parameters, **excluding every
   key whose name begins with `_`** (those are runtime knobs).
2. Serialize it to **canonical JSON** (JCS, [RFC 8785]): object members sorted by
   Unicode code point at every nesting level, no insignificant whitespace
   (member separator `,`, name separator `:`), UTF-8 output with minimal JSON
   string escaping. To keep canonicalization unambiguous, **hash-input values are
   restricted to strings, integers, booleans, and arrays/objects composed of
   those** — floats and nulls are disallowed in hash inputs (a float-valued knob
   must be passed as a string, which is also more hash-stable). Array element
   order is significant (arrays are data); object key order is not (sorted).
3. The parameter hash is the lowercase hex **SHA-256** of those canonical UTF-8
   bytes.
4. The storage **key** is `"<cachetype>/<hash>"`. (Tools MAY *display* a short
   hash prefix, but the on-disk directory and all references use the full 64-hex
   digest.)

Canonical JSON (rather than TOML) is the hash input precisely because it has a
fully-pinned byte form that Python (`json.dumps(obj, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)`) and Julia produce **identically
today**, independent of the cross-tool TOML `byte-identity` work. So a produced
dataset resolves to the same `<cache_root>/<cachetype>/<hash>` path under either
tool (even though the artifact *bytes* a given tool writes there may be
language-specific; cross-tool *loading* of a produced artifact is not implied,
only cross-tool *addressing* and *garbage collection*). The `config.toml` sidecar
stores the same key table in human-readable TOML; the hash is over its canonical
**JSON** projection, not over the TOML bytes.

[RFC 8785]: https://www.rfc-editor.org/rfc/rfc8785

### Cache layout and sidecars

A produced artifact is materialized at `<cache_root>/<key>` =
`<cache_root>/<cachetype>/<hash>/`, via the same safe-materialization primitive
(atomic publish, `.complete` marker, `.lock` pidfile) as any other store write.
The directory is **self-describing** through two sidecars written next to the
artifact:

```
<cache_root>/<cachetype>/<hash>/
├── <basename>.<ext>      # the produced artifact (format-determined)
├── config.toml           # the re-hashable hash inputs (the key table)
├── metadata.toml         # provenance / audit (never hashed)
└── .complete             # completion marker (file form: <hash>.complete alongside)
```

**`config.toml`** (`cache-produce`) — the key table verbatim plus a `[_META]`
block, so any tool can recompute the hash and confirm the directory's identity. The
key table is written at the **root** and **first** (TOML requires root-table keys to
precede any table header), so `[_META]` comes last; reading back, the key table is
every root key except the `[_META]` block:

```toml
# --- hash-affecting parameters (the key table) ---
grid        = "5x5"
skip_models = ["CESM.*", "FGOALS.*"]

[_META]
schema    = 1
cachetype = "esm_20c_anomaly"
# hash = SHA-256( {"grid":"5x5","skip_models":["CESM.*","FGOALS.*"]} ), canonical JSON:
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
```

(`83425a3…` is a verifiable reference vector: it is the SHA-256 of the canonical
JSON `{"grid":"5x5","skip_models":["CESM.*","FGOALS.*"]}`. Every conforming
`cache-produce` implementation MUST reproduce it.)

A tool with `cache-produce` MUST be able to recompute the hash from `config.toml`'s
key table and MUST treat a directory whose recomputed hash ≠ `_META.hash` as
**not** a valid cache hit (re-produce).

**`metadata.toml`** (`cache-produce`) — provenance only, never an input to the
hash and never an authority for cache validity:

```toml
[_META]
schema = 1

created = "2026-06-02T15:04:05Z"        # RFC 3339 UTC
tool    = "datamanifestpy 0.17.0"        # producing tool + version
host    = "login3.hpc.edu"
user    = "mahe"

[git]
commit = "1f8839c…"
branch = "main"
dirty  = false

[origin]
cached_toml = "/home/mahe/proj/cached.toml"   # the index that roots this artifact
```

### The `cached.toml` index

Produced datasets are **not** written into the hand-authored `datasets.toml`
(which stays clean — the `Project.toml` analogue). They are registered in a
sibling **`cached.toml`** (the `Manifest.toml` analogue), by default alongside
the manifest. `cached.toml` is the *liveness* root for produced artifacts: it
lists them by **portable key** (`cachetype` + `hash`), never by absolute path.

```toml
[_META]
schema = 1

[load_20c_esm_anomaly]
cachetype = "esm_20c_anomaly"
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
ref       = "lgmpre.data:load_20c_esm_anomaly"   # the producing function
format    = "nc"
store     = "$cache"
```

- `cached.toml` is a **defined structural sibling format**, with its own
  `_META.schema = 1`. A tool that does not implement `cache-gc` need not read it.
- **Commit policy:** `cached.toml` is **gitignored per-machine state by default**
  (it indexes machine-local produced artifacts); a project that wants
  reproducible shared produced-caches MAY opt in to committing it (the
  `Manifest.toml` convention — libraries ignore, applications commit).
- A produced dataset is registered in exactly one `cached.toml`; the
  `metadata.toml` `[origin].cached_toml` back-pointer names it (audit only).

### Garbage collection

Because produced artifacts accumulate, the **cache layer** MAY implement a `gc`
command (`cache-gc`). GC is a property of the cache layer, **not the core**, and is a
**root-reachability** collector (cf. Julia depot `Pkg.gc`, Nix GC roots, Hugging Face
cache refs):

- **Roots are the two index files.** A still-existing `datasets.toml` roots every
  *declared/fetched* dataset it lists, including `store = "$cache"` entries (they
  are re-fetchable, rooted by their manifest entry). A still-existing
  `cached.toml` roots every *produced* dataset it lists.
- **A depot-level usage log** (the known set of `datasets.toml` / `cached.toml`
  paths + a last-seen timestamp for each, analogous to Julia's
  `manifest_usage.toml`) lets `gc` discover the live root set without scanning
  the whole filesystem. The companion records a manifest/index path in the usage log
  whenever it reads it.
- **Collectable rule (normative).** An artifact under the `$cache` folder is
  collectable **iff** no still-existing root references its key, **and** it is
  older than a configurable grace age. The per-artifact `metadata.toml`
  back-pointer is **audit only** — never the deletion authority (it goes stale
  and cannot express multiple references).
- A dataset under the `$data` or `$repo` folder is never collected by `gc` (only the
  `$cache` folder is reclaimable). GC never deletes from `datasets.toml`-declared
  locations; it only reclaims unreferenced produced artifacts under `$cache`.

### What spec-v2 does not specify

- **The `@cached` macro / decorator API** (Julia macro, Python decorator) is the
  *ergonomic surface* over this model and is **per-language, not normative** — a
  tool exposes it however fits the language. Only the on-disk formats (key hash,
  `config.toml`, `metadata.toml`, `cached.toml`) and the GC rule are normative.
- **The artifact serialization format** (`jls`/`jld2`/`pickle`/…) is a per-tool,
  per-`format` choice (the existing `format` + loader concern); produced
  artifacts are not assumed cross-language-loadable.
- **In-place / mounted access** (the former `mount` store) is out of scope: spec-v2 folders
  are *locations only*, with no materialization axis. It is deferred to a future revision —
  see `ROADMAP.md` — not part of this spec; no `mount` capability is defined.
- **Cloud / `fsspec` / CAS backends** are not a core model; if a tool adds them,
  they are optional per-language extras behind the recipe interface, not a spec
  contract.

## Preservation contract

A conforming writer of language `L` MUST:

- Regenerate its own `[<dataset>._LANG.L]` from its internal state;
- Copy every other `[<dataset>._LANG.X]` (X ≠ L) **verbatim**, without parsing or
  reordering;
- Regenerate its own top-level `[_LANG.L]` (config and `loaders` map);
- Copy every other top-level `[_LANG.X]` (X ≠ L) verbatim;
- Preserve any `_`-prefixed structural table that it does not own (`_META`, unknown
  future `_*`) verbatim;
- Preserve legacy `[_LOADERS]` verbatim if present and not explicitly migrated.
- Preserve `[_STORAGE]` verbatim unless it implements the `storage` capability, in which
  case it MAY regenerate its own `_STORAGE` entries (a shared, non-language-namespaced
  table).

Implementation pattern: a `DatasetEntry` keeps foreign `_LANG.X` subtrees and unknown
scalar keys in its `extra`; the `Database` keeps foreign top-level `[_LANG.X]` and
unknown `_*` tables in a database-level `extra`. Both splice back on write.

## Conformance levels

A *capability* is a named feature that an implementation may support independently of
others. An implementation declares the capability set it supports and runs only the
fixture-suite tests tagged for those capabilities.

| Capability | Description |
|---|---|
| `lang-read` | Parse `[<ds>._LANG.<lang>]` and `[_LANG.<lang>.loaders]`; apply the load ladder. |
| `lang-write` | Regenerate own `_LANG.<self>` and preserve foreign `_LANG.*` verbatim on write (full lossless round-trip). |
| `shell-fetch` | Execute the `[<ds>._LANG.shell].fetcher` command template in the fetch ladder. |
| `delegation` | Cross-language fetch (rung 3, the rare case): run a fetcher defined in another language — mechanism implementation-defined (call the language's runtime, or a peer `datamanifest` CLI), with fall-through to `uri` — controlled by `delegate` / `--delegate` (see Cross-language fetch, Peer-CLI contract). |
| `storage` | Honor the `store` / `default` `$`-folder selectors and `[_STORAGE]` folder-variable resolution; materialize datasets into the selected folder at its canonical or configured root (see Storage). |
| `byte-identity` | Emit the canonical lexicographic key ordering so the same logical manifest is **semantically identical** across tools — same keys, same values, same order at every level (verified by the cross-tool fixture). This is the *guaranteed* constraint. Literal **byte-for-byte** identity is **not** assured by default: current TOML writers differ in cosmetic formatting (indentation, blank lines, inline-vs-multiline arrays), so a one-to-one byte match is not always achievable. The **Python tool is the normative reference** for the canonical byte form; tools MAY offer an opt-in path to it (e.g. `datamanifest format`, or Julia `write(...; canonical=true)`). |
| `binding-args` | Execute the table form of a binding (`{ ref, args, kwargs }`): call `ref(*args; kwargs...)` with `$var` substitution in string values. |
| `cache-produce` | **Cache-layer** produce-or-load: function-backed (produced) datasets with parameter-hash keying, the `config.toml` / `metadata.toml` sidecars, and `store = "$cache"` defaulting (spec-v2.1 §Produced datasets). Declared by the cache layer, never by the core fetch capability (packaging — separate package or submodule — is unconstrained). |
| `cache-gc` | **Cache-layer** `cached.toml` produced-dataset index, the depot-level usage log, and root-reachability `gc` (spec-v2.1 §Garbage collection). Declared by the cache layer; the core keeps no GC. |

Capabilities are independent — a partial implementation may ship `lang-read` and
`lang-write` without `shell-fetch` or `delegation`. The spec and its fixture suite are
never forked per language package; divergent per-language pace is expressed by each
implementation declaring its supported capability set and pinning to a spec tag.

`_META.schema` (the integer stored in the file) is the data-model compatibility version
and is bumped only on breaking structural changes. The spec-document version (git tag,
e.g. `spec-v1.0`) tracks prose and fixture evolution independently. An implementation
conforms to "schema N, spec ≥ vX" — these two axes are independent.

## Peer-CLI contract

One way to do cross-language fetch (rung 3) is to call a peer-language `datamanifest` CLI.
This section is the normative invocation interface for any tool that does so. (A tool that
instead runs the foreign language's runtime directly does not use this contract.)

### Invocation

```
datamanifest fetch <name> --datasets-toml <path> [--datasets-folder <dir>]
```

- `<name>` — the dataset key as it appears in the manifest.
- `--datasets-toml <path>` — absolute or project-relative path to the manifest file.
- `--datasets-folder <dir>` — (optional) directory that holds the shared download
  cache. If omitted, the tool's default cache location applies.

The peer tool resolves its own `[<dataset>._LANG.<lang>].fetcher` (using its own
fetch ladder), writes the result into the shared cache, verifies `sha256` if
present, and **exits non-zero on any failure**. It produces **no dataset bytes on
stdout** — the artifact lands in the cache on disk and the calling tool reads it
from there.

### Discovery and availability

Each language's CLI is discoverable on `PATH` under a language-specific name, e.g.
`datamanifest` (Python), `DataManifest` or `datamanifest-julia` (Julia). The Python
`datamanifest` CLI is the **reference peer** (the fallback target for cross-language fetch).
Before
delegating, a tool MUST probe that the peer CLI (and its runtime) is installed and
usable; if the probe fails, the delegation rung is silently skipped and the ladder
advances to rung 4 (`uri` download). Probe commands and PATH names are left to each
implementation to document.

## Deprecations

The following v0 forms are still read for backward compatibility but SHOULD NOT be
written by conforming v1 tools:

- **`[_LOADERS]`** (top-level) — replaced by `[_LANG.<lang>.loaders]`.
- **Per-dataset `julia=` / `python=` / `callable=` / `shell=` / `loader=`** — replaced
  by `[<dataset>._LANG.<lang>].fetcher` / `.loader`. These legacy keys are kept verbatim
  in the dataset's `extra` on read (no auto-rewrite to avoid touching another language's
  data). A tool MAY emit a one-time deprecation notice.
- **`julia_modules` / `python_includes`** — retired; the manifest's directory is on the
  tool's import path by convention. Legacy `*_includes` values are still read as extra
  import-path entries for back-compat.

An opt-in `datamanifest migrate` command (not normative in this spec) may rewrite a v0
flat file to v1 `_LANG` form for the tool's own language.

## Conformance notes

- Readers MUST ignore unknown top-level tables and unknown fields rather than erroring,
  so that new datasets, new `_LANG` entries, and other tools' extension keys do not break
  an older reader.
- Readers MUST preserve unknown `_*` structural keys verbatim — not treat them as
  datasets, not drop them on write.
- Writers SHOULD omit derived fields (`host`, `path`, `scheme`) and any field left at
  its default value.
- Writers MUST emit all keys, at every nesting level — top-level tables (structural `_*`
  and datasets alike) and the fields within each table, including keys nested in inline
  `{ }` tables — sorted by **Unicode code-point lexicographic order** (the shared default of Python `sorted()` and Julia
  `TOML.print(sorted=true)`). No table is special-cased (no `_LOADERS`/`_META`-first). This
  guarantees **semantic identity** across tools — the same logical manifest round-trips to
  the same keys, values, and ordering through either tool (the weaker constraint that is
  always met). It does **not**, by itself, guarantee **byte-for-byte** identity: the Python
  (`tomli_w`) and Julia (`TOML.print`) serializers differ in cosmetic formatting
  (indentation, blank lines, inline-vs-multiline arrays), and current tooling does not
  always permit a one-to-one byte match. For literal byte-identity the **Python tool is the
  normative reference** for the canonical form, and a tool MAY route its output through it
  opt-in (`datamanifest format`, or Julia `write(...; canonical=true)`). Note:
  because `_` (U+005F) sorts after uppercase but before lowercase ASCII letters, an
  uppercase dataset name sorts *before* the `_*` structural tables and a lowercase one
  *after* — intended; the canonical *ordering* is the requirement, not structural-table
  placement.
- `uri` and `uris` are mutually exclusive on a single dataset.
- A file with no `[_META]` section is read as schema v0 (legacy flat), leniently.
