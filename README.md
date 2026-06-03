<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="design/logo/lockup-dark.svg">
    <img src="design/logo/lockup.svg" alt="datamanifest.toml" height="76">
  </picture>
</p>

A small, normative specification for the **`datamanifest.toml`** manifest format — a
TOML file that declares the data dependencies of a scientific project (each dataset's
source URI, checksum, version, format, and how to fetch and load it).

The spec is at **schema v1** (`_META.schema = 1`). The key change from v0 is the
**`_LANG` namespace**: language-specific bindings (`fetcher`/`loader` as
`module:function` references) live under `[<dataset>._LANG.<lang>]` and
`[_LANG.<lang>.loaders]`, keeping the language-agnostic contract fields separate.
Each implementation reads its own `_LANG` entries and preserves the rest verbatim,
enabling lossless round-trips in multi-language projects.

➡️ **[Read the schema: `SCHEMA.md`](SCHEMA.md)**
➡️ **[Conformance fixtures: `tests/fixtures/`](tests/fixtures/README.md)**
➡️ **[Changelog: `CHANGELOG.md`](CHANGELOG.md)**

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
tool's own language. A bare binding that doesn't resolve in that language warns and falls
through rather than erroring.

```toml
[sea_ice]
uri    = "https://example.com/sea_ice.nc"
format = "nc"
loader = "myclimate.loaders:load_sea_ice"   # no [._LANG.python] — own language assumed
```

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
