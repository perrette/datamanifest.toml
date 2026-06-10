# Migration and deprecations

Legacy v0 forms are still **read** but should not be **written** by current tools: the flat
language-named fields `julia=` / `python=` / `callable=` (which historically held inline
code, now forbidden) are tolerated on read and rewritten into `[<ds>._LANG.<lang>]` by an
opt-in `migrate` command; `julia_modules` / `python_includes` are retired. Note that bare
`fetcher`/`loader`, bare `shell`, and `[_LOADERS]` are **supported** forms, not deprecated.

Since spec-v5, a migration/setup flow SHOULD write machine-specific storage directives to
the checkout config (`.datamanifest/config.toml`) rather than the committed manifest, and
SHOULD NOT write built-in defaults into `[_STORAGE]` (a written-out default would
permanently shadow the user's machine-wide configuration). The state file relocates from
the sibling `.datamanifest-state.toml` to `.datamanifest/state.toml` on its first write.

*Normative: [SCHEMA.md §Deprecations](../schema.md#deprecations).*
