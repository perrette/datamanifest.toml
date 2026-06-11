# The manifest in one minute

`datasets.toml` (Python) / `Datasets.toml` (Julia) is a hand-authored TOML file that
declares a project's data dependencies — the `Project.toml` / `pyproject.toml` analogue for
data. It is committed, language-agnostic, and never machine-rewritten beyond auto-filled
checksums. Produced (cached) datasets are **not** listed here; they are inventoried in the
git-ignored state file `.datamanifest/state.toml` (see
[Produced datasets and caching](caching.md)).

```toml
[_META]
schema = 1                       # data-model version (currently 1)

[sea_surface_temp]               # one table per dataset, keyed by name
uri      = "https://example.com/sst.nc"
checksum = "sha256:…"            # auto-filled on first download, verified at fetch
format   = "nc"
```

Top-level keys beginning with `_` are **structural** (`_META`, `_LANG`, `_STORAGE`,
`_LOADERS`); every other top-level table is a dataset. Readers preserve unknown `_*` keys
verbatim. On write, keys are sorted: the structural `_*` tables come first, then the
dataset tables, each group in code-point order.

*Normative: [SCHEMA.md §Structural keys / §Top-level layout](../schema.md#structural-keys).*

A complete, mostly-runnable manifest is in
[`examples/datasets.toml`](https://github.com/perrette/datamanifest.toml/blob/main/examples/datasets.toml).
