# Cross-machine sync

A tool with the `sync` capability moves a stored object between two machines instead of
re-downloading or recomputing it. Each object has a machine-independent address — a fetched
dataset by `name`/`alias`/`doi`, a produced artifact by `cachetype[/version]/hash` — so only
the physical root differs per host.

- Transport is **rsync over SSH**; the SSH target is both transport and host identity (no
  remote registry).
- The remote root is resolved best-effort from the remote's own configuration ladder
  (environment, config files, `_HOST` rules), then the shared default. `$repo`
  (project-relative) is not syncable — the machine-global default locations are.
- Sync **writes no manifest** — a transferred object lands as an orphan (present,
  unreferenced) and is immediately usable; it is **idempotent**.

*Normative: [SCHEMA.md §Cross-machine sync](../schema.md#cross-machine-sync).*
