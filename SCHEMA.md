# `datamanifest.toml` — manifest schema specification

This document is the normative description of the TOML manifest format shared by the
[DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) (Julia) and
[datamanifest](https://github.com/perrette/datamanifest) (Python) tools. A manifest
declares the data dependencies of a project: each dataset's source URI, checksum,
version, format, and how to load it. Either implementation can read and write a
conforming file; each reads the common fields plus its own language-specific
extension keys and ignores the others.

Field names and semantics below are derived from the Julia reference
(`DataManifest.jl/src/Databases.jl`, the `DatasetEntry` struct).

## Top-level layout

A manifest is a TOML document with:

- **One table per dataset**, keyed by the dataset *name* (an arbitrary string the user
  chooses, e.g. `[herzschuh2023]`). The table's fields are the common `DatasetEntry`
  fields documented below plus any language-specific extension fields.
- **An optional `[_LOADERS]` table** mapping a loader *name* to an entry-point-style
  reference (`"pkg.mod:func"`) or to another loader name (an alias). Datasets reference
  a named loader through their `loader` field, or rely on a format-default loader.

When a tool serializes a manifest it sorts the dataset tables alphabetically and emits
the `_LOADERS` table first, so that diffs are reproducible. Comments are not preserved;
per-dataset documentation belongs in the `description` field.

Example:

```toml
[_LOADERS]
mycsv = "pandas.io.parsers:read_csv"

[herzschuh2023]
uri = "https://download.pangaea.de/dataset/930512/files/LegacyClimate_1_0.zip"
doi = "10.1594/PANGAEA.930512"
format = "zip"
extract = true
sha256 = "…"

[CMIP6_lgm_tos]
uri = "https://esgf.example/…/tos_lgm.nc"
format = "nc"
```

## Common fields

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
| `shell` | string | `""` | Shell-command template run to produce the dataset instead of downloading a URI. Supports `$download_path`, `$project_root`, `$uri`, `$key`, `$version`, `$doi`, `$format`, `$branch`, `$path_<ref>`, `$path_<i>`, `$requires_paths`. |
| `loader` | string | `""` | Name of a `_LOADERS` entry (or an entry-point reference) used to load this dataset, overriding the format default. |
| `requires` | array of string | `[]` | Names of datasets that must be downloaded before this one; defines a dependency graph resolved in topological order. Their resolved paths are exposed to `shell` / code hooks. |

## Extensions

Beyond the common fields, each implementation defines language-specific keys for the
optional *download-phase code hook* — a user function run instead of (or in addition to)
a URI download. A conforming tool reads only its own extension keys and ignores the
others, which is what lets one manifest serve a cross-language project.

### Julia — `DataManifest.jl`

| Field | Type | Semantics |
|---|---|---|
| `julia` | string | Inline Julia source compiled and run during the download phase (`Base.include_string`). |
| `julia_modules` | array of string | Module names pre-imported into the execution context for the inline `julia` code. |

### Python — `datamanifest`

The Python port deliberately **rejects inline code execution** (no `exec`/`eval` of
TOML-sourced strings). Anything more than a `pkg.mod:func` reference must live in a real
importable module.

| Field | Type | Semantics |
|---|---|---|
| `python` | string | Entry-point reference `"pkg.mod:func"`, resolved via `importlib`, called during the download phase with keyword args `(download_path, project_root, entry, uri, key, version, doi, format, branch, requires_paths)`. Replaces Julia's `julia`. |
| `callable` | string | Read-only alias for `python`. Accepted on read and normalized into `python`; only `python` is ever written back. Lets a single-language project use a language-neutral key. |
| `python_includes` | array of string | Directory paths prepended to `sys.path` while resolving loaders and `python` hooks, so modules next to the manifest are importable (e.g. `"local_mod.sub:func"`). The analogue of `julia_modules` without inline execution. *(Stored at the database/`_LOADERS` configuration level rather than per dataset.)* |

**Rationale.** `julia_modules` is dropped on the Python side because, without inline
`exec`, there is no execution context to pre-import modules into; `python_includes`
instead makes user-local modules importable by path. `callable` is a convenience alias
so that a Python-only project need not name the key after a specific language. Cross-language
manifests should use `julia=` / `python=` / `r=` so that each tool picks up only its own.

## Conformance notes

- Readers MUST ignore unknown top-level tables and unknown fields rather than erroring,
  so that new datasets, new `_LOADERS` entries, and other tools' extension keys do not
  break an older reader.
- Writers SHOULD omit derived fields (`host`, `path`, `scheme`) and any field left at its
  default value, and SHOULD sort dataset tables alphabetically with `_LOADERS` first.
- `uri` and `uris` are mutually exclusive on a single dataset.
