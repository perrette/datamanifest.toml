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

## Deployment model (direction): Python as the reference fetch orchestrator

Intended cross-language deployment, **not yet normative** — it would revise the spec's
current "delegation off by default" stance (see below) when adopted.

- **The Python CLI is the main fetch orchestrator.** It is the canonical
  download/materialization engine — easy to install system-wide (pip `entry_points`, fast
  startup) and already the normative reference for paths and byte-identity. Anything not
  already handled by a **native** (own-language) or **shell** fetcher is delegated to it.
- **`delegate` defaults to *true* for non-Python tools** (e.g. the Julia tool), targeting
  the Python CLI — **unless the Python CLI is not installed**. The fetch ladder becomes:
  native → shell → **delegate to Python (default on, if present)** → `uri` download. The
  existing probe-and-fall-through makes this safe: if Python is absent, delegation is
  skipped and plain `uri` datasets still download natively.
- **Python is the target, not a delegator** — it does not default-delegate to a peer; it
  *is* the peer everyone else delegates to. **Load is always native** (load never delegates).
- This lets a non-Python tool ship as a **plain library** (no Julia CLI to compile /
  sysimage): it shells out to Python for fetch and loads natively. It is the practical
  answer to the Julia-CLI packaging / startup-latency problem.

**Caveat — produced (`@cached`) datasets are out of scope of this model.** Delegation can
only hand off work Python can actually do. A dataset whose bytes are *produced* by a
non-Python project function (the companion produce-or-load layer), or a genuinely
Julia-only fetcher, **cannot** be delegated to Python — the bytes originate in that
language by definition. So "delegate everything to Python" covers *fetched* (uri / shell /
python-fetcher) datasets; each language still produces and caches its own `@cached`
datasets natively. The orchestrator model and the companion layer pull in opposite
directions here — keep them distinct.

**Spec implication.** Adopting this flips the normative default in `SCHEMA.md` §Fetch
ladder (delegation is currently *off* by default) to *on toward Python* for non-Python
tools. That is a deliberate future spec revision, tracked here, not yet in `SCHEMA.md`.

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
