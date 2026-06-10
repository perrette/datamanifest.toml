# Roadmap

High-level direction for the `datamanifest.toml` spec and its implementations. The
normative spec is `SCHEMA.md` (versioned by git tags, e.g. `spec-v1.1`, `spec-v2`).
Detailed, dated design rationale lives under `design/`. This file is the general,
forward-looking view: what is specified, what is built, and what is deferred.

## Status

- **Spec.** `SCHEMA.md` is at **spec-v5**: flat two-folder storage with machine-global
  defaults (a shared keyed dataset store + a per-project produced cache under `$project`),
  scoped per-machine configuration (`.datamanifest/config.toml`, user config) on a
  git-style resolution ladder, the state file at `.datamanifest/state.toml`,
  produce-or-load as a companion layer, user-driven `inspect`, and cross-machine `sync`.
  `_META.schema` stays **1**.
- **Implementations.** The Python reference implements spec-v5 plus the surrounding
  tooling (the `config` command, generalized `push`/`pull` operands, git-remote targets,
  `normalize`, `export`); the Julia port tracks the spec-normative surface.

## Planned

- **Tooling around storage v5** (per-implementation conventions, not spec-normative): the
  generalized push/pull operand grammar and git-remote targets, `normalize` / `list
  --out-of-place`, and the `export` bundle verb in the Julia port. Rationale: the Python
  repo's `design/design-storage-v5.md`.

## Cross-language fetch (a rare case)

Nearly all datasets are `uri` downloads (or native/`shell` fetchers), so each
implementation is self-sufficient on its own. Cross-language fetch (`SCHEMA.md` §rung 3)
only matters when a dataset's bytes can be produced *only* by a fetcher in another language
— rare. The spec leaves the mechanism open: a tool may call the other language's runtime
directly, or fall back to the **Python CLI**, which is the reference implementation and aims
to cover every language. It does not extend to produced (`@cached`) datasets, which
originate in their host language.

## Deferred / reserved

- **In-place / mounted access** — **shipped** (spec-v4.3) as the **`lazy_access`** dataset
  mode: a never-materialized dataset opened where it lives by a loader. The mechanism
  (streaming, sshfs/FUSE **mount**, an object-store filesystem) is implementation-defined, so
  the former standalone `mount` store is subsumed rather than reintroduced as a separate
  concept. What remains open is per-mechanism ergonomics (e.g. a tool managing the lifecycle of
  an actual FUSE mount) — a tooling concern, not a spec one.

## Possible future directions

- **Unified documentation site (tabbed, multi-language).** A static docs site
  (MkDocs + Material — its built-in content tabs give the Python/Julia code switcher), built
  from the reference guide (`docs/guide.md`) with per-language inline examples and deployed to
  GitHub Pages. Better UX and more impressive than scattered per-repo READMEs, but it pulls
  implementation-specific code into the family docs — a deliberate trade against "each client
  owns its own docs." Deferred (mkdocs not yet set up; `pip install mkdocs-material`).
- **Register-on-arrival for `sync`, and at-rest content verification.** `sync` (spec-v3) is
  deliberately symmetric and manifest-untouching, so a transferred object arrives as an
  orphan and integrity rests on rsync's per-file check. Optional later additions: an opt-in
  to record a pulled object in the local state file (`.datamanifest/state.toml`, so it shows as
  `referenced`), and a content checksum (e.g. a Merkle digest over a directory's files) for
  at-rest verification beyond the transport.
- **Task-first "cookbook" docs.** The spec is a precise rulebook, but users shouldn't have to
  hold the scope ladder or path composition in their heads. Add a recipe-oriented section
  (in `docs/guide.md` or a new `docs/cookbook.md`): host-resolved heavy archive (`$cmip` via
  `_HOST` + `local_path`), project-isolated caches, share-one-heavy-dataset (`scope = ""`),
  `local_path` vs `store`, per-project cleanup (`list --scope … --delete`). Several recent
  design exchanges are already draft entries.
- **Scoped datasets without duplicating the heavy ones (hardlinks / reflink clones).** With
  per-dataset `scope` in place, a project can isolate its fetched datasets for clean per-project
  maintenance — but a genuinely shared heavy archive (CMIP, reanalysis) scoped per project would
  duplicate gigabytes. A storage-layer (not format) enhancement could keep **one physical copy**
  and expose per-scope **hardlinks or reflink/CoW clones** (Linux `cp --reflink`, APFS clones),
  so scoping stays cheap for large inputs. Pairs with the open question of whether the *datasets*
  default scope should flip from empty/shared to project-id. Deferred.
- **Finish the spec/state separation.** The state file (`.datamanifest/state.toml`) already
  splits *expectation* (the committed `datasets.toml`) from *ground truth* (resolved location +
  actual digest). Today a dataset's `storage_path` and `sha256` still live in **both** files
  with different meanings (directive/contract vs. resolved/actual) — an intentional, harmless
  duplication. Deferred cleanups: a defined **expected-vs-actual `sha256`** relationship and
  re-verification policy (with `skip_checksum`); moving the *resolved* `storage_path` / *actual*
  `sha256` fully into the state file so `datasets.toml` is pure recipe; and the **`modified`**
  dirty state in full. (**Decided out of scope, not deferred:** *multiple recorded locations*
  per object — `storage_path` stays a single value, the last location the object was found at or
  written to. Resolution only needs to find one copy; a stray second copy reads as `untracked`
  and is cleaned up explicitly. A shared copy elsewhere on the machine is found via a read
  pool, not by growing the record into a set.)
- **Cloud / `fsspec` / CAS backends** — optional per-language extras behind the recipe
  interface, never a core spec contract.

## Delivered tooling

- **Machine-readable JSON Schemas** (`schemas/`, spec-v2.1). Declarative
  [JSON Schema](https://json-schema.org/) (draft 2020-12) for all four TOML document types
  (`manifest`, the `state` file, `config`/`metadata` sidecars), one file per spec version
  (`*.v2.1.json`) so older versions stay alongside new ones. They complement — do not
  replace — the prose `SCHEMA.md` and the fixture suite (`tests/`): behavioural rules
  (resolution ladders, hash reproduction, round-trip) stay in the prose and fixtures. See
  `schemas/README.md`.
