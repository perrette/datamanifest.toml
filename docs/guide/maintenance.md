# Maintenance (inspect)

Both fetched and produced objects accumulate, so a tool with the `inspect` capability can
enumerate the store, filter it, and delete an explicit selection. Each object exposes
`kind` (`data`/`cached`), `key`/`hash`, `location`, `referenced` (rooted by a present
`.toml`, or an **orphan**), `format`, `size`, `created`, and a best-effort
`last-access`.

Maintenance is **user-driven, never automatic** — there is no garbage collector; deletion is
always an explicit selection (dry-run/confirm by default). `referenced` and `last-access` are
**advisory** filter inputs, not deletion authorities. `last-access` is read from the
filesystem (`stat`) at inspect time and **never written on read**, so it is coarse and may be
unknown (`noatime`/`relatime`); `created` is the always-available age signal.

*Normative: [SCHEMA.md §Maintenance](../schema.md#maintenance-inspect-filter-delete).*
