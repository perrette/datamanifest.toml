# Quickstart

`datamanifest.toml` is the **manifest**: a hand-authored TOML file that declares a
project's data dependencies — the `Project.toml` / `pyproject.toml` analogue for data.
One file is read by tools in different languages
([Python](https://github.com/perrette/datamanifest) and
[Julia](https://github.com/awi-esc/DataManifest.jl)).

## Quick look

Declare a dataset — its source and checksum — in `datasets.toml`:

```toml
["jesstierney/lgmDA"]
uri      = "https://github.com/jesstierney/lgmDA/archive/refs/tags/v2.1.zip"
checksum = "sha256:da5f85235baf7f858f1b52ed73405f5d4ed28a8f6da92e16070f86b724d8bb25"
extract  = true
```

A tool downloads it, verifies the checksum, unpacks the archive, and hands your code the
local path — re-fetching only when it's missing. Add a `format` and it loads the data into a
native object too; the same file is read unchanged by tools in different languages.

## A fuller manifest

A manifest declares each dataset's source, checksum, format, and how each language loads
it. Below is a representative `datasets.toml`; the full, runnable file lives at
[`examples/datasets.toml`](https://github.com/perrette/datamanifest.toml/blob/main/examples/datasets.toml)
(both implementations can load it directly).

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
checksum    = "sha256:4e40e43ac0f1ddea125cb5314eee46e332aacbcb18aff7efbf59f1d8b1d84a13"
doi         = "10.1594/PANGAEA.930512"
format      = "zip"
extract     = true
description = "Pollen-based climate reconstructions (Herzschuh et al., 2023)"

# A per-dataset loader override. A binding is a "module:function" string …
[ocean_temp]
uri      = "https://example.com/argo_ocean_temp.nc"
checksum = "sha256:c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
format   = "nc"

[ocean_temp._LANG.python]
loader = "myclimate.loaders:load_argo"        # string form (no arguments)

# … or a { ref, args, kwargs } table when the call needs arguments.
[esm_5x5]
uri      = "https://example.com/esm_5x5.nc"
checksum = "sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
format   = "nc"

[esm_5x5._LANG.julia.loader]
ref    = "MyClimate:load_esm"
args   = ["$path"]
kwargs = { grid = "5x5", skip_models = ["CESM.*"] }

# No public URI: built by a shell command. `shell` is the language-agnostic
# fetcher — the same command for every tool — and uses $var substitutions.
[model_output]
checksum = "sha256:e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
format   = "nc"
shell    = "make model_output OUTPUT=$download_path"

# A re-fetchable input parked on the OS-reclaimable cache folder.
[reanalysis]
uri          = "https://example.com/era5_slice.nc"
checksum     = "sha256:f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1"
format       = "nc"
storage_path = "$user_cache_dir/$key"
```

`checksum` takes an `<algo>:<hex>` digest (`sha256` recommended); a bare hex value, or
the legacy `sha256 = "<hex>"` key, is read as a sha256 digest. Leave it empty and the
tool fills it in on the first successful download.

A binding (a `fetcher`/`loader`, or a `[_LANG.<lang>.loaders]` entry) is either a
`module:function` **string** or a `{ ref, args, kwargs }` **table** — the string being a
shorthand for a ref with no arguments. See [Language bindings](guide/bindings.md).

Single-language projects can drop the `_LANG.<lang>` wrapper entirely: a **bare**
`fetcher`/`loader` on the dataset (or a top-level `[_LOADERS]` map) is read as the running
tool's own language.

```toml
[sea_ice]
uri    = "https://example.com/sea_ice.nc"
format = "nc"
loader = "myclimate.loaders:load_sea_ice"   # no [._LANG.python] — own language assumed
```

## Implementations

The Python package [`perrette/datamanifest`](https://github.com/perrette/datamanifest) is
the **reference implementation** and ships the `datamanifest` command-line tool. A Julia
port, [`DataManifest.jl`](https://github.com/awi-esc/DataManifest.jl), tracks the same spec
and shares the [conformance fixtures](fixtures.md) — a common test suite of manifest files
with machine-checked expected outcomes — so both read the same `datamanifest.toml`.

| Language | Repository | Description |
|---|---|---|
| Python *(reference)* | [perrette/datamanifest](https://github.com/perrette/datamanifest) | **The reference implementation.** Download, verify, extract, and load datasets declared in a manifest; uses entry-point loader references instead of inline code execution. Provides the **`datamanifest` command-line tool**. |
| Julia | [awi-esc/DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) | Download, verify, extract, and load datasets declared in a manifest, with a Julia-native API. |

## Next steps

- [The manifest in one minute](guide/manifest.md) — structural keys and the top-level layout.
- [Declaring datasets](guide/datasets.md) — every contract field.
- [Language bindings](guide/bindings.md) — `fetcher`/`loader`/`shell` references.
- [Storage](guide/storage.md) — where datasets and the cache live.
