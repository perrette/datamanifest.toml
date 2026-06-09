# Produced datasets and caching

Beyond *fetching* declared datasets, a tool with the `cache-produce` capability can
*produce-or-load*: cache the result of a project function on disk, keyed by its parameters
(the `@cached` decorator/macro in both implementations).

- **Parameter-hash keying.** The cache key is the lowercase-hex **SHA-256 of the canonical
  JSON** (JCS / RFC 8785) of the function's hash-affecting keyword parameters. Canonical JSON
  is cross-tool reproducible. Hash inputs are strings, integers, **finite floats**, booleans,
  and arrays/objects of those — finite floats use the normative Python `json.dumps` form
  (`1.0`→`1.0`); `NaN`/`±Inf` and nulls are disallowed.
- **Self-describing artifacts.** Alongside each artifact sit two sidecars:
  `config.toml` (the re-hashable key table plus a `[_META]` block with `cachetype` and
  `hash`) and `metadata.toml` (provenance — timestamp, tool, git, host/user; never hashed,
  never an authority for validity). A tool MUST recompute the hash from `config.toml` and
  treat a mismatch as **not** a cache hit.
- **Layout:** `<datacache_dir>/<cachetype>/[<version>/]<hash>/<basename>.<ext>`.
  The optional **`version`** is a human-set recipe/code version — a path segment that does
  **not** enter the hash, used to prevent a stale cross-branch hit.
- **The state file (`.datamanifest-state.toml`)** inventories each produced dataset (under
  `datacache`, keyed `cachetype[@version]` ⇒ `hash` ⇒ artifact directory) alongside fetched
  datasets (under `datasets`) — a record of *where things actually landed*, never an absolute
  path you author. It is **git-ignored regenerable state by default** (the data is local and
  often outside the repo); read-resolution consults it to *find* an object but always writes to
  the current directive.

```toml
# config.toml — written next to the artifact
grid        = "5x5"
skip_models = ["CESM.*", "FGOALS.*"]

[_META]
schema    = 1
cachetype = "esm_20c_anomaly"
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
```

*Normative: [SCHEMA.md §Produced datasets and caching](../schema.md#produced-datasets-and-caching-companion-layer).*
