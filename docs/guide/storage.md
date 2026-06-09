# Storage

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
- **Read pools** (`datasets_pools` / `datacache_pools`) — optional lists of read-only folders
  checked *before* downloading/producing, so a dataset or `@cached` result another project
  already has is reused **in place** (checksum-verified for datasets, recorded in the state
  file, never copied). `datasets_pools` defaults to well-known shared folders; `datacache_pools`
  is opt-in. An empty list disables them. See [SCHEMA.md §Storage](../schema.md#storage).
- **Environment:** overrides for the folders — `DATAMANIFEST_DATASETS_DIR` /
  `DATAMANIFEST_DATACACHE_DIR` (user symbols override as `DATAMANIFEST_<NAME>`; pools as
  `DATAMANIFEST_DATASETS_POOLS` / `DATAMANIFEST_DATACACHE_POOLS`); `$user_data_dir`/`$user_cache_dir`
  keep their per-OS resolution.
- **Concurrency:** writes are atomic (temp + rename) under a `.lock` pidfile with a
  `.complete` marker, so concurrent readers never see a half-materialized dataset.

*Normative: [SCHEMA.md §Storage](../schema.md#storage).*
