# Migration and deprecations

Legacy v0 forms are still **read** but should not be **written** by current tools: the flat
language-named fields `julia=` / `python=` / `callable=` (which historically held inline
code, now forbidden) are tolerated on read and rewritten into `[<ds>._LANG.<lang>]` by an
opt-in `migrate` command; `julia_modules` / `python_includes` are retired. Note that bare
`fetcher`/`loader`, bare `shell`, and `[_LOADERS]` are **supported** forms, not deprecated.

*Normative: [SCHEMA.md §Deprecations](../schema.md#deprecations).*
