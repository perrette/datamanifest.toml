# Roadmap

High-level direction for the `datamanifest.toml` spec and its implementations. The
normative spec is `SCHEMA.md` (versioned by git tags, e.g. `spec-v1.1`, `spec-v2`).
Detailed, dated design rationale lives under `design/`. This file is the general,
forward-looking view: what is specified, what is built, and what is deferred.

## Status

- **Spec.** `SCHEMA.md` is at **spec-v3**: storage uses **top-level folder roots** with
  layer-applied `datasets/` / `cached/` prefixes and an optional `scope` partition
  (`DATAMANIFEST_DIR` app base; `_PROFILE` shelved); produce-or-load is a companion layer;
  store maintenance is the user-driven `inspect` capability; and cross-machine `sync` is
  specified. `_META.schema` stays **1**.
- **Implementations.** Python core is at spec-v1.1; Julia core's v1.1 is not yet merged.
  Neither core implements the spec-v3 storage revision yet, and the produce-or-load layer,
  `inspect`, and `sync` are not yet built.

## Planned

- **Implement the spec-v3 storage revision** in both cores (top-level folder roots,
  `datasets/`/`cached/` prefixes + `_PREFIX`, `scope` + `_SCOPE`, `DATAMANIFEST_DIR`, the
  resolution ladder, hard migration off bare `store` names). Spec: `SCHEMA.md` §Storage.
- **Build the produce-or-load layer** (one per language) over the core engine —
  parameter-hash keying + sidecars + recipe `version`, then the state file inventory
  (`.datamanifest-state.toml`, `datacache` namespace). Whether
  it ships as a separate package or an optional submodule is the implementation's call
  (spec-v2.1). Rationale and build order: `design/cached-layer-handoff.md`; packaging:
  `design/package-architecture.md`.
- **Implement `inspect`** (the field-oriented `list … --delete` store maintenance) and
  **`sync`** (`push`/`pull` over SSH/rsync). Spec: `SCHEMA.md` §Maintenance, §Cross-machine
  sync.
- **Merge Julia core v1.1** before any Julia spec-v3 work.

## Cross-language fetch (a rare case)

Nearly all datasets are `uri` downloads (or native/`shell` fetchers), so each
implementation is self-sufficient on its own. Cross-language fetch (`SCHEMA.md` §rung 3)
only matters when a dataset's bytes can be produced *only* by a fetcher in another language
— rare. The spec leaves the mechanism open: a tool may call the other language's runtime
directly, or fall back to the **Python CLI**, which is the reference implementation and aims
to cover every language. It does not extend to produced (`@cached`) datasets, which
originate in their host language.

## Deferred / reserved

- **In-place / mounted access** (the former `mount` store). Deferred, not abandoned: the
  spec-v2 storage model is locations-only and has no home for never-materialized in-place
  access. A future revision is expected to reintroduce it as a distinct concept alongside
  folders. Until then it is not part of the spec and tools must not advertise it.

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
  to record a pulled object in the local state file (`.datamanifest-state.toml`, so it shows as
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
- **Finish the spec/state separation.** The state file (`.datamanifest-state.toml`) already
  splits *expectation* (the committed `datasets.toml`) from *ground truth* (resolved location +
  actual digest). Today a dataset's `storage_path` and `sha256` still live in **both** files
  with different meanings (directive/contract vs. resolved/actual) — an intentional, harmless
  duplication. Deferred cleanups: a defined **expected-vs-actual `sha256`** relationship and
  re-verification policy (with `skip_checksum`); moving the *resolved* `storage_path` / *actual*
  `sha256` fully into the state file so `datasets.toml` is pure recipe; **multiple recorded
  locations** for one object (synced to two places); and the **`modified`** dirty state in full.
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
