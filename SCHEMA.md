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
level, the defined structural tables are `_META`, `_LANG`, and the legacy `_LOADERS`.
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

Capabilities are independent — a partial implementation may ship `lang-read` and
`lang-write` without `shell-fetch` or `delegation`. The spec and its fixture suite are
never forked per language package; divergent per-language pace is expressed by each
implementation declaring its supported capability set and pinning to a spec tag.

`_META.schema` (the integer stored in the file) is the data-model compatibility version
and is bumped only on breaking structural changes. The spec-document version (git tag,
e.g. `spec-v1.0`) tracks prose and fixture evolution independently. An implementation
conforms to "schema N, spec ≥ vX" — these two axes are independent.

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
