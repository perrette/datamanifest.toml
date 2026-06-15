# Storage

Storage is **two paths**: where fetched datasets go and where the produced cache goes. Both
**default to machine-global, platform-derived folders**, so the repository holds only the
manifest and the git-ignored `.datamanifest/` directory:

```toml
datasets_dir  = "$user_data_dir/datamanifest/shared/datasets"            # fetched datasets (default)
datacache_dir = "$user_cache_dir/datamanifest/projects/$project/cached"  # produced cache (default)
```

Fetched datasets share **one keyed store across projects** (a dataset key is a globally
unique content identity, so the store deduplicates by construction); the produced cache is
**per-project**, namespaced by `$project` (the project name — basename of the project root
by default, overridable as a `project` field). Setting `datasets_dir = "datasets"` /
`datacache_dir = "cached"` restores the repo-local layout.

```toml
[_STORAGE]
scratch       = "/scratch/$USER"  # a reusable $-symbol -> $scratch

[_STORAGE._HOST."login*.hpc.edu"]
scratch       = "/work/$USER"     # host-specific symbol value (glob on hostname)
datacache_dir = "$scratch/cache"  # a field, host-specific

[big]
uri        = "https://example.com/big.nc"
storage_path = "$scratch/$key"      # this dataset, parked on scratch ($key => tool-managed)
```

- **Paths.** Relative ⇒ relative to the project root (`$repo`). A fetched dataset lands at
  `<datasets_dir>/<key>`, a produced artifact at
  `<datacache_dir>/<cachetype>/[<version>/]<hash>/`. No prefix or derived name is inserted
  in between — the configured folder is the location.
- **Symbols.** A path may use `$`-symbols: predefined **`$user_data_dir`** / **`$user_cache_dir`**
  (the machine's data/cache dirs, straight from `platformdirs`), **`$repo`**, and
  **`$project`**; any other bare `[_STORAGE]` key is a user-defined symbol, made
  host-specific in `[_STORAGE._HOST]`. `$USER`/env and `~` also expand.
- **Scoped configuration.** Per-machine settings live in two optional, `[_STORAGE]`-shaped
  config files instead of the committed manifest: **`.datamanifest/config.toml`**
  (per-checkout, git-ignored — the `.datamanifest/` directory also holds the state file)
  and **`~/.config/datamanifest/config.toml`** (user-global). Resolution ladder, first
  match wins: `DATAMANIFEST_<NAME>` env → checkout config → manifest `[_STORAGE._HOST]` →
  manifest `[_STORAGE]` → user config → built-in defaults (each file's `_HOST` glob beats
  its base). The manifest is the only committed file; `.datamanifest/` is entirely
  git-ignored.
- **Configuration is frozen at materialization.** The ladder is evaluated once, when a
  manifest is materialized into a session object; a config-file or environment change does
  not retarget an existing session. Re-resolution is an explicit action (re-materialize or
  refresh) — and each one-shot CLI invocation materializes afresh, so edits take effect on
  the next run.
- **Per-dataset `storage_path`** overrides where one dataset lives (default `$datasets_dir/$key`):
  contains `$key` ⇒ tool-managed/keyed; an exact path without `$key` ⇒ user-managed and never
  touched by maintenance. (It is *not* called `path` — that is the URI's parsed component.)
- **Read pools** (`datasets_pools` / `datacache_pools`) — optional lists of read-only folders
  checked *before* downloading/producing, so a dataset or `@cached` result another project
  already has is reused **in place** (checksum-verified for datasets, recorded in the state
  file, never copied). `datasets_pools` defaults to `$repo/datasets` (pre-existing repo-local
  data keeps being found), the shared store, and the legacy well-known folders;
  `datacache_pools` is opt-in. An empty list disables them. See
  [SCHEMA.md §Storage](../schema.md#storage).
- **Environment:** overrides for the folders — `DATAMANIFEST_DATASETS_DIR` /
  `DATAMANIFEST_DATACACHE_DIR` (user symbols override as `DATAMANIFEST_<NAME>`; pools as
  `DATAMANIFEST_DATASETS_POOLS` / `DATAMANIFEST_DATACACHE_POOLS`); `$user_data_dir`/`$user_cache_dir`
  keep their per-OS resolution.
- **Other directives on the same ladder.** Besides folders, pools, and symbols, the ladder
  resolves the configuration fields **`canonical`** (boolean, default `false` — route
  manifest writes through the reference serializer for byte-identical output; see
  [Conformance](conformance.md)) and **`lock_stale_age`** (seconds, default `30` — the lock
  staleness age, below). Both are `_HOST`-composable like any field; the environment names
  are `DATAMANIFEST_CANONICAL` / `DATAMANIFEST_LOCK_STALE_AGE`.
- **Concurrency:** writes are atomic (temp + rename) under a `.lock` pidfile with a
  `.complete` marker, so concurrent readers never see a half-materialized dataset. A
  process finding the lock held waits for it and re-checks the entry before writing; a lock
  whose age exceeds `lock_stale_age` may be reclaimed as stale (the holder heartbeats the
  lock while writing, so a live long write is not reclaimed).

*Normative: [SCHEMA.md §Storage](../schema.md#storage).*
