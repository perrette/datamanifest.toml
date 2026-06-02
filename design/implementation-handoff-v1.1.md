# Implementation hand-off → spec-v1.1

**To:** an agent implementing spec-v1.1 in the tool repos (`~/Projects/datamanifest`
Python, `~/Projects/DataManifest.jl` Julia).
**Spec:** `SCHEMA.md` at tag `spec-v1.1` (this repo). Fixtures: `tests/fixtures/`.
**Design rationale (read for context, not as spec):** `design/caching-and-dataset-storage.md`.

This release is **additive**; `_META.schema` stays **1**. Old readers preserve the new
field/table verbatim. Implement against the fixtures (test-driven) — they are the
executable spec.

## In scope

1. **Canonical key ordering / `byte-identity`.** Emit *all* keys, at every level (top-level
   tables, within-table fields, and keys inside inline `{ }` tables), in Unicode
   code-point lexicographic order. No `_LOADERS`/`_META`-first special case.
   - Python: `Database.write()` must drop the `_LOADERS`-first case and sort
     **recursively** (within-entry too) before `tomli_w.dump` (tomli_w does not sort).
     Today within-entry order is dataclass field order.
   - Julia: already alphabetical via `TOML.print(; sorted=true)`; confirm byte-identity
     against Python's new output.
2. **Storage model (`storage` capability).** The `store` field (`data` default | `cache` |
   `repo`) and the `[_STORAGE]` table (`_HOST` / `_PROFILE` overrides). Resolver:
   - **`platformdirs` is the normative reference** for default roots:
     `data` = `user_data_dir("datamanifest")/Datasets`,
     `cache` = `user_cache_dir("datamanifest")/Datasets`, `repo` = `<project_root>/datasets`.
     **Julia MUST resolve to the same paths `platformdirs` produces** — do not use the
     Julia depot.
   - Per-store root precedence: env (`DATAMANIFEST_DATA_DIR`/`_CACHE_DIR`) → `_PROFILE`
     (when `DATAMANIFEST_PROFILE` set) → first matching `_HOST` glob → `[_STORAGE]` base →
     default.
   - Read resolution searches stores in fixed order `repo → data → cache`, first hit wins.
   - **Safe-materialization primitive** (shared by fetch / extract / produce): write to
     `<key>.tmp` → atomic rename → create `.complete` marker; hold a `<key>.lock` pidfile
     while writing. Readers treat a missing marker as absent (re-fetch).
3. **Parameterized bindings (`binding-args` capability).** A per-dataset `fetcher`/`loader`
   may be a `{ ref, args }` table. `args` is a keyword table (plain data) passed in
   addition to the standard call kwargs; arg keys must not collide with standard ones;
   string values support shell-style `$var` substitution. **Keyword-only — no positional
   args.** If a tool executes the language but does not implement `binding-args`, it MUST
   **error** on an `args` table, never call without it.
4. **Theme A integrity behavior** (implementation, not format): verify `sha256` once at
   fetch; do **not** re-hash on every load (re-verify is opt-in). Decide whether to land
   this in this pass or a follow-up.

## Explicitly OUT of scope (do not implement — will cause flailing)

- **`mount` store** — capability is reserved but its mechanics are unspecified in v1.1.
  Parse/preserve `store = "mount"` and `[_STORAGE]`, but do not implement mounting.
- **`@cached` / produce-or-load decorator, `cached.toml`, GC** — sketched in the design
  doc only; needs a separate API-design pass.
- **Cloud / fsspec backends.** Built-in fetchers only (HTTP via native `httpx` /
  `Downloads.download`; git/rsync subprocess).

## Migration (Python only)

The maintainer's single `datasets.toml` uses the v0 inline form
`julia = "Module.f(\"x\", grid=\"4x5\")"`. **Do not build an eval-based parser.** This file
is being hand-migrated to the `{ ref, args }` form directly (one file, one user). Also:
both tools' `migrate` currently leave a flat `shell = "<cmd>"` instead of converting it to
`[<ds>._LANG.shell].fetcher` — fix that (the v1 shell fetcher *is* a command template).

## Acceptance

- `python3 tests/validate_fixtures.py` passes (fixture self-consistency).
- Each tool's conformance runner passes every fixture whose capabilities it declares,
  re-pinned to tag `spec-v1.1`.
- **Cross-tool byte-identity:** the same logical manifest serializes byte-for-byte
  identically from Python and Julia.

## Suggested order

① safe-materialization primitive → ② resolver + `store=` / `[_STORAGE]` → ③ canonical
ordering / byte-identity → ④ parameterized bindings. Do Python first (the `platformdirs`
reference), then make Julia match and verify byte-identity.
