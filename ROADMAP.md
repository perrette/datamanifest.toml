# Roadmap

High-level direction for the `datamanifest.toml` spec and its implementations. The
normative spec is `SCHEMA.md` (versioned by git tags, e.g. `spec-v1.1`, `spec-v2`).
Detailed, dated design rationale lives under `design/`. This file is the general,
forward-looking view: what is specified, what is built, and what is deferred.

## Status

- **Spec.** `SCHEMA.md` is at **spec-v2**: the storage model is the `$`-folder-variable
  model (locations only), and produce-or-load is specified as a companion-layer format.
- **Implementations.** Python core is at spec-v1.1; Julia core's v1.1 is not yet merged.
  Neither core implements the spec-v2 storage revision yet, and the companion
  produce-or-load packages are not yet built.

## Planned

- **Implement the spec-v2 storage revision** in both cores (`$`-folder variables,
  selectors vs path expressions, the unified resolution ladder, the hard migration off
  bare `store` names). Spec: `SCHEMA.md` §Storage; rationale:
  `design/storage-model-revision.md`.
- **Build the companion produce-or-load packages** (one per language) over the core
  engine — parameter-hash keying + sidecars first, then the `cached.toml` index + GC.
  Rationale and build order: `design/cached-layer-handoff.md`.
- **Merge Julia core v1.1** before any Julia spec-v2 work.

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

- **A proper JSON validator, one file per spec version.** Today a `datasets.toml` is
  validated by the prose spec plus the fixture suite (`tests/`). A declarative
  machine-readable schema (e.g. JSON Schema) — **one file per spec version** (`spec-v1.1`,
  `spec-v2`, …), since older versions stay in use — would let dedicated tools validate a
  manifest mechanically. This is a separate artifact from the prose `SCHEMA.md` (present),
  the `CHANGELOG.md` (which documents prior versions), and the git tags.
- **Cloud / `fsspec` / CAS backends** — optional per-language extras behind the recipe
  interface, never a core spec contract.
