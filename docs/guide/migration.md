# Migration and deprecations

Legacy v0 forms are still **read** but should not be **written** by current tools: the flat
language-named fields `julia=` / `python=` / `callable=` (which held inline code — v1
forbids inline code everywhere) are tolerated on read and rewritten into
`[<ds>._LANG.<lang>]` by an opt-in `migrate` command; `julia_modules` / `python_includes`
are retired. Note that bare `fetcher`/`loader`, bare `shell`, and `[_LOADERS]` are
**supported** forms, not deprecated.

The legacy `sha256 = "<hex>"` field is the deprecated spelling of the checksum: readers
treat it as `checksum = "sha256:<hex>"`, and a tool upgrades it in place the next time it
writes the manifest. This is additive — no `_META.schema` bump.

Since spec-v5, a migration/setup flow SHOULD write machine-specific storage directives to
the checkout config (`.datamanifest/config.toml`) rather than the committed manifest, and
SHOULD NOT write built-in defaults into `[_STORAGE]` (a written-out default would
permanently shadow the user's machine-wide configuration). Earlier state-file shapes and
locations — the sibling `.datamanifest-state.toml` and the older `cached.toml` — are still
read and migrated forward; the first write relocates the file to the canonical
`.datamanifest/state.toml` (the legacy file is removed only after the canonical one is
written).

*Normative: [SCHEMA.md §Deprecations](../schema.md#deprecations).*
