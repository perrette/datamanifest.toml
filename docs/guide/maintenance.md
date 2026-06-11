# Maintenance (inspect)

Both fetched and produced objects accumulate, so a tool with the `inspect` capability can
enumerate the store, filter it, and act on an explicit selection: **delete** (remove the
bytes and the state-file entry), **refresh** (reconcile the state file only — re-point
relocated entries, drop missing ones; no downloads, no file moves), and optionally
**move**. Each object exposes `kind` (`data`/`cached`), `key`/`hash`, `location`,
`referenced` (rooted by a present `.toml` — a dataset key listed in a `datasets.toml`, a
produced artifact recorded in the state file — or else an **orphan**), `format`, `size`,
`created`, and a best-effort `last-access`.

Maintenance is **user-driven, never automatic** — there is no garbage collector; deletion is
always an explicit selection (dry-run/confirm by default). It never touches data the user
manages: a dataset whose `storage_path` is an exact path (no `$key`) or that sets
`skip_download` is reported as skipped, never moved or deleted. `referenced` and `last-access` are
**advisory** filter inputs, not deletion authorities. `last-access` is read from the
filesystem (`stat`) at inspect time and **never written on read**, so it is coarse and may be
unknown (`noatime`/`relatime`); `created` is the always-available age signal.

*Normative: [SCHEMA.md §Maintenance](../schema.md#maintenance-inspect-filter-delete).*
