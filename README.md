<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="design/logo/lockup-dark.svg">
    <img src="design/logo/lockup.svg" alt="datamanifest.toml" height="76">
  </picture>
</p>

A small, normative specification for the **`datamanifest.toml`** manifest format — a
TOML file that declares the data dependencies of a scientific project (each dataset's
source URI, checksum, version, format, and how to fetch and load it).

One `datasets.toml` is read by tools in different languages — today
[Python](https://github.com/perrette/datamanifest) and
[Julia](https://github.com/awi-esc/DataManifest.jl) — and covers fetching (download,
checksum, extract, load), portable storage, per-language bindings, and an optional
produce-or-load cache layer. The data model is `_META.schema = 1`; behavioural revisions
are tracked by spec tags (currently `spec-v3.6`).

➡️ **[Reference guide: `docs/guide.md`](docs/guide.md)** — readable walkthrough of every aspect  
➡️ **[Normative spec: `SCHEMA.md`](SCHEMA.md)**  
➡️ **[Conformance fixtures: `tests/fixtures/`](tests/fixtures/README.md)**  
➡️ **[Changelog: `CHANGELOG.md`](CHANGELOG.md)**

## Quick look

Declare a dataset — its source and checksum — in `datasets.toml`:

```toml
["jesstierney/lgmDA"]
uri     = "https://github.com/jesstierney/lgmDA/archive/refs/tags/v2.1.zip"
sha256  = "da5f85235baf7f858f1b52ed73405f5d4ed28a8f6da92e16070f86b724d8bb25"
extract = true
```

A tool downloads it, verifies the checksum, unpacks the archive, and hands your code the
local path — re-fetching only when it's missing. Add a `format` and it loads the data into a
native object too; the same file is read unchanged by tools in different languages.

## Example

A manifest declares each dataset's source, checksum, format, and how each language loads
it. Below is a representative `datasets.toml`; the full, runnable file lives at
**[`examples/datasets.toml`](examples/datasets.toml)** (both implementations can load it
directly).

```toml
[_META]
schema = 1

# Project-wide default loaders, per language: format -> module:function.
[_LANG.python.loaders]
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"

[_LANG.julia.loaders]
csv = "CSV:read"
nc  = "NCDatasets:Dataset"

# A DOI archive: downloaded, checksum-verified, then unpacked.
[herzschuh2023]
uri         = "https://doi.pangaea.de/10.1594/PANGAEA.930512?format=zip"
sha256      = "4e40e43ac0f1ddea125cb5314eee46e332aacbcb18aff7efbf59f1d8b1d84a13"
doi         = "10.1594/PANGAEA.930512"
format      = "zip"
extract     = true
description = "Pollen-based climate reconstructions (Herzschuh et al., 2023)"

# A per-dataset loader override. A binding is a "module:function" string …
[ocean_temp]
uri    = "https://example.com/argo_ocean_temp.nc"
sha256 = "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
format = "nc"

[ocean_temp._LANG.python]
loader = "myclimate.loaders:load_argo"        # string form (no arguments)

# … or a { ref, args, kwargs } table when the call needs arguments.
[esm_5x5]
uri    = "https://example.com/esm_5x5.nc"
sha256 = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
format = "nc"

[esm_5x5._LANG.julia.loader]
ref    = "MyClimate:load_esm"
args   = ["$path"]
kwargs = { grid = "5x5", skip_models = ["CESM.*"] }

# No public URI: built by a shell command. `shell` is the language-agnostic
# fetcher — the same command for every tool — and uses $var substitutions.
[model_output]
sha256 = "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
format = "nc"
shell  = "make model_output OUTPUT=$download_path"

# A re-fetchable input parked on the OS-reclaimable cache folder.
[reanalysis]
uri    = "https://example.com/era5_slice.nc"
sha256 = "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1"
format = "nc"
store  = "$cache"
```

A binding (a `fetcher`/`loader`, or a `[_LANG.<lang>.loaders]` entry) is either a
`module:function` **string** or a `{ ref, args, kwargs }` **table** — the string being a
shorthand for a ref with no arguments.

Single-language projects can drop the `_LANG.<lang>` wrapper entirely: a **bare**
`fetcher`/`loader` on the dataset (or a top-level `[_LOADERS]` map) is read as the running
tool's own language. A bare binding is *present* for that language, so a failure to resolve
is an error (not a silent fallback); use explicit `[_LANG.<lang>]` for multi-language
manifests, which other languages correctly skip.

```toml
[sea_ice]
uri    = "https://example.com/sea_ice.nc"
format = "nc"
loader = "myclimate.loaders:load_sea_ice"   # no [._LANG.python] — own language assumed
```

## Storage layout

Where files land is composed as `<root>/<scope>/<prefix>/<key>` — a **folder**
(`$data`/`$cache`/`$repo` or a user-defined one), the project **scope** (defaults to the
project name, so each project is isolated by default), and the per-kind **prefix**
(`datasets/` / `cached/`). All three are set in `[_STORAGE]`. For example — downloads in one
flat shared pool, caches per-project under a versioned work dir, with the **roots resolved
per host** (laptop vs cluster):

```toml
[_STORAGE]
# defaults (e.g. your laptop)
data  = "~/Data/all-project-data"
cache = "~/.cache/work"

[_STORAGE._HOST."login*.hpc.edu"]  # on the cluster login nodes, different roots
data  = "/data/all-project-data"
cache = "/work/$USER"              # $USER from the environment

[_STORAGE._SCOPE]
datasets = ""                      # shared: no per-project segment for downloads
# cached scope is left to default — the project name (pyproject.toml / Project.toml)

[_STORAGE._PREFIX]
datasets = ""                      # no 'datasets/' subfolder — straight under the root
cached   = "2025.1"                # a generic code/release version level for the cache
```

On the cluster this gives:

- fetched  → `/data/all-project-data/<key>`
- produced → `/work/<user>/<project-name>/2025.1/<cachetype>/<hash>/…`

and on the laptop the same layout under `~/Data/all-project-data/<key>` and
`~/.cache/work/<project-name>/2025.1/…`. The host-independent parts (the shared datasets
scope, the empty datasets prefix, the cache version) stay in the base tables; only the
**roots** vary per host via `[_STORAGE._HOST.<glob>]`. The cache's `2025.1` is your own
version label (set it dynamically with `DATAMANIFEST_PREFIX_CACHED` if it changes per build);
it is distinct from datamanifest's per-recipe `version`, which nests deeper at
`<cachetype>/<version>/<hash>`. Scope is never guessed: if there is no
`pyproject.toml`/`Project.toml` name, set `[_STORAGE].scope` (or `DATAMANIFEST_SCOPE`).
See [SCHEMA.md §Storage](SCHEMA.md#storage).

## Implementations

Two implementations track the spec in parallel and on equal footing. Julia was the
initial reference, but they now evolve together, sharing the same conformance fixtures
(`tests/fixtures/`); the **command-line tool ships with the Python package**.

| Language | Repository | Description |
|---|---|---|
| Python | [perrette/datamanifest](https://github.com/perrette/datamanifest) | Download, verify, extract, and load datasets declared in a manifest; uses entry-point loader references instead of inline code execution. Provides the **`datamanifest` command-line tool**. |
| Julia | [awi-esc/DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) | Download, verify, extract, and load datasets declared in a manifest, with a Julia-native API. |

## License

MIT — see [LICENSE](LICENSE).
