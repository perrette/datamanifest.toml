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
- **`[_STORAGE]`** — optional storage configuration: each named store's root location
  (`data`, `cache`, `repo`), with `_HOST` / `_PROFILE` override sub-tables. See Storage.
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
| `local_path` | string | `""` | User-managed location. If absolute, used verbatim; if relative, resolved against the project root. Bypasses download. |
| `store` | string | `"data"` | Named store the dataset is materialized into — `data` (persistent, default), `cache` (disposable), `repo` (project-tracked), or `mount` (transient, not materialized). See Storage. Honored under the `storage` capability (`mount` additionally requires `mount`); other tools preserve it verbatim. |
| `sha256` | string | `""` | Expected SHA-256 of the downloaded file/folder. Auto-filled on first successful download; verified thereafter. |
| `skip_checksum` | bool | `false` | Disable checksum verification for this dataset. |
| `skip_download` | bool | `false` | Treat the dataset as externally provided; the documented `uri` is returned as the path and no download is attempted. |
| `extract` | bool | `false` | After download, extract the archive (`zip` / `tar` / `tar.gz`) and use the extracted directory as the dataset path. |
| `format` | string | `""` | Data format hint used to pick a default loader (`csv`, `parquet`, `nc`, `json`, `yaml`, `toml`, `md`, `txt`, `zip`, `tar`, `tar.gz`, …). Inferred from the URI when absent. |
| `requires` | array of string | `[]` | Names of datasets that must be downloaded before this one; defines a dependency graph resolved in topological order. |

## Language bindings (`_LANG`)

Executable bindings live under a structural `_LANG` namespace, keyed by language tag
(`python`, `julia`, `r`, `shell`, …). The dataset table itself stays fully agnostic.

All executable references are **`module:function` references** — never inline code, in
any language. A local module is importable because the manifest's directory (the project
root) is on the language tool's import path by convention. There are no `includes` or
`modules` fields in v1.

### Per-dataset bindings

`[<dataset>._LANG.<lang>]` holds singular bindings for a specific dataset in language
`<lang>`. Both keys are optional.

| Key | Type | Semantics |
|---|---|---|
| `fetcher` | string | `module:function` ref called to produce the dataset bytes, instead of (or in addition to) downloading the `uri`. |
| `loader` | string | `module:function` ref called to load the dataset into memory, overriding the format default. |

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
3. **(opt-in)** delegate to a peer-language `datamanifest` CLI — the peer resolves its
   own `[<dataset>._LANG.<lang>].fetcher`, populates the shared cache, and exits
   non-zero on failure. Peer delegation is **off by default**; enable per-run with
   `--delegate` or per-file with `delegate = true`;
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

## Storage

A dataset's bytes are materialized into one of several named **stores**. The `store`
field selects which; the optional top-level `[_STORAGE]` table configures where each
store lives. Storage is a portable *policy* layer: a `store` value carries the same
meaning in every implementation, and default root locations are language-independent so
peer tools share the same on-disk store without configuration.

### Stores and policies

Every store has two policy axes:

- **Materialization** — `local` (bytes are copied to `<root>/<key>`) or `mount` (the
  dataset is accessed in place through a mounted/remote filesystem and is never copied).
- **Retention** (meaningful only for `local`) — how long the materialized bytes persist.

Four stores are defined; `store` defaults to `data`. A dataset's storage **key** (see
`key`) is independent of its store, so the same dataset resolves to `<root>/<key>` under
whichever store is selected.

| `store` | materialization | retention | semantics |
|---|---|---|---|
| `data` *(default)* | local | persistent | Protected, long-lived data; not subject to automatic deletion. |
| `cache` | local | disposable | Reconstructible cache; MAY be reclaimed by the OS or by a tool's garbage collector. |
| `repo` | local | tracked | Lives inside the project tree; its lifetime is the repository's. |
| `mount` | mount | transient | Accessed in place via a mounted/remote filesystem; never materialized. Requires the `mount` capability. |

An implementation with the `storage` capability MUST apply the materialization and
retention semantics above for the stores it honors.

### Root locations and `[_STORAGE]`

The optional top-level structural table `[_STORAGE]` configures each store's root. Keys
are store names; values are paths (`~` and `$VAR` expanded). A `repo` value is resolved
relative to the project root; absolute values are used verbatim. Per-host and per-profile
overrides are expressed as sub-tables:

```toml
[_STORAGE]
data  = "~/data/Datasets"
cache = "~/.cache/Datasets"
repo  = "datasets"

[_STORAGE._HOST."login*.hpc.edu"]   # matched against the hostname (glob/regex)
data  = "/scratch/$USER/Datasets"

[_STORAGE._PROFILE.cluster]          # selected by an implementation-defined profile signal
data  = "/work/proj/Datasets"
```

Normative rules:

- `[_STORAGE]` and its `_HOST` / `_PROFILE` sub-tables are **defined structural keys**:
  every conforming tool MUST parse them identically and preserve them verbatim on write
  (a tool without the `storage` capability treats the whole table as a preserved unknown).
- **Default root locations are language-independent.** When a store's root is not set
  explicitly, a conforming tool MUST resolve it to the OS-convention path below and MUST
  NOT substitute a language-native location (e.g. a package depot), so that Python and
  Julia resolve the same dataset to the **same path**:
  - `data` → OS user *data* dir (`$XDG_DATA_HOME`, default `~/.local/share`, on Linux;
    `~/Library/Application Support` on macOS; `%LOCALAPPDATA%` on Windows) + `/datamanifest/Datasets`;
  - `cache` → OS user *cache* dir (`$XDG_CACHE_HOME`, default `~/.cache`, on Linux;
    `~/Library/Caches` on macOS; `%LOCALAPPDATA%\…\Cache` on Windows) + `/datamanifest/Datasets`;
  - `repo` → `<project_root>/datasets`.

  (These follow the `platformdirs` `user_data_dir` / `user_cache_dir` conventions.)
- **Read resolution MUST cover these canonical locations** (and any explicit `[_STORAGE]`
  / `_HOST` / `_PROFILE` paths), so a dataset materialized by one tool is found by a peer
  tool. An explicit path, where given, replaces the corresponding default and MUST be
  honored identically by every tool.
- The precedence by which `_HOST` / `_PROFILE` / environment overrides combine is
  implementation-defined; the explicit and default paths they resolve to are not.

> **Note — the `cache` *store* is not the `@cached` *mechanism*.** `store = "cache"` is a
> storage tier (a disposable location) and is independent of *how* a dataset is produced.
> In particular it is unrelated to a tool's produce-or-load (`@cached`) caching of
> *function results* — a separate, non-normative mechanism that registers
> function-computed datasets in their own index (e.g. a `cached.toml`). Any dataset,
> fetched or produced, may use any store.

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
| `delegation` | Opt-in peer-CLI delegation in the fetch ladder (rung 3). |
| `storage` | Honor the `store` field and `[_STORAGE]` resolution; materialize datasets into the selected local store at its canonical or configured root (see Storage). |
| `mount` | Support the `mount` store — transient, non-materialized in-place access via a mounted/remote filesystem. |

Capabilities are independent — a partial implementation may ship `lang-read` and
`lang-write` without `shell-fetch` or `delegation`. The spec and its fixture suite are
never forked per language package; divergent per-language pace is expressed by each
implementation declaring its supported capability set and pinning to a spec tag.

`_META.schema` (the integer stored in the file) is the data-model compatibility version
and is bumped only on breaking structural changes. The spec-document version (git tag,
e.g. `spec-v1.0`) tracks prose and fixture evolution independently. An implementation
conforms to "schema N, spec ≥ vX" — these two axes are independent.

## Peer-CLI contract

The `delegation` capability (fetch-ladder rung 3) requires an agreed invocation
interface between peer tools. This section is normative for any implementation that
ships delegation.

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
`datamanifest` (Python), `DataManifest` or `datamanifest-julia` (Julia). Before
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
- Writers SHOULD sort dataset tables alphabetically.
- `uri` and `uris` are mutually exclusive on a single dataset.
- A file with no `[_META]` section is read as schema v0 (legacy flat), leniently.
