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

## Deployment model: cross-language fetch without shipping a Julia CLI

The cross-language fetch **mechanisms** are now in the spec (`SCHEMA.md` §Cross-language
fetch, §Peer-CLI contract). This section is the high-level rationale; the per-tool *default
policy* (whether the rung fires by default) is a deployment choice the spec leaves to each
implementation, with the reference deployment described below.

- **Python is the primary driver and orchestrator.** It fetches `python` / `shell` / `uri`
  recipes natively and owns materialization (store, lock, atomic publish, `sha256`, marker).
  It is also the normative reference for paths and byte-identity.
- **Foreign fetchers run via the interpreter, not a shipped CLI (preferred).** When the
  only available fetcher is in another language (e.g. `[ds._LANG.julia].fetcher`), the
  driver spawns that language's **interpreter against the repo's project env** —
  `julia --project=<env> -e 'using MyPkg; MyPkg.fetch_foo(; download_path=…)'` — and
  materializes the bytes itself. This is a language-aware `shell` fetcher. It needs only the
  `julia` binary (system-wide) + the repo's `Project.toml` + the package — **no Julia
  `datamanifest` CLI to compile/ship**. This is the practical answer to the Julia-CLI
  packaging problem.
- **Peer-CLI delegation is the heavier alternative.** Where a peer tool should *own*
  materialization (it has store/index logic the caller lacks), the driver calls the peer
  `datamanifest` CLI instead; the **Python CLI** is the reference peer (e.g. a thin
  non-Python client that delegates all fetching to Python and loads natively).
- **The rung fires by default when its toolchain is present**, else it falls through to
  `uri` via the mandatory probe — so a missing `julia` (or peer CLI) never breaks plain-`uri`
  datasets. **Load is always native** (load never crosses languages).

**Caveat — produced (`@cached`) datasets are out of scope.** Cross-language fetch moves
*fetching* only. A dataset whose bytes are *produced* by a project function in a given
language (the companion produce-or-load layer) is not cross-language — each language
produces and caches its own. The fetch model and the companion layer pull in opposite
directions here; keep them distinct.

**Status in the spec.** `SCHEMA.md` now defines the `delegate` field, the §Cross-language
fetch subsection (interpreter-subprocess preferred, peer-CLI alternative), and makes the
on/off *default* a documented per-tool deployment choice rather than hard-coding "off".
Remaining work is in the implementations, not the spec.

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
