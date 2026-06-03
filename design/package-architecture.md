# Package architecture — layers, the import rule, and per-language packaging

> **Status (2026-06-03):** resolved. Promoted to the spec as the **spec-v2.1** reframe
> (CHANGELOG → `spec-v2.1`). This doc records *why* the spec stops mandating a separate
> companion package, and how the layering maps onto Python and Julia.

## The problem

`datamanifest` started as a tool for **external data dependencies** (a hand-authored
`datasets.toml`: uri + checksum + fetch/load bindings). A second need then appeared:
caching **intermediate results of computation** to skip recomputation — the `@cached`
produce-or-load layer. The question was how the two should relate: one package, two
packages, three? spec-v2 answered "the cache layer is a **separate companion package** that
depends on the core." This doc supersedes that *packaging* decision (the *capability*
decision it made is kept).

## The two axes people conflate

1. **Import namespace** — how code refers to it (`datamanifest.cache` vs `datacache`).
2. **Distribution unit** — what you install as one versioned thing (one `pip install` /
   one `Pkg.add`).

In **Python** these are loosely coupled (a wheel can expose submodules *or* multiple
top-level names, plus `extras` as a third lever). In **Julia** they are tightly coupled
(a package = one module = one registry entry = one version; no `extras`). So the right
*structure* differs by language. The invariant is the **layering**; the packaging idiom
is per-language. The spec must therefore not mandate packaging.

## The layers (the real seam)

There are three, not two. The genuinely reusable, cross-cutting thing both features need —
host-aware storage location resolution + safe materialization (atomic write + pidfile lock
+ completion marker) + loader dispatch — is a **substrate** that both fetch and cache
*consume*. The substrate is the seam that matters.

```
  spec repo (datamanifest.toml) — language-neutral formats + conformance fixtures
  ───────────────────────────────────────────────────────────────
  Layer 0  STORE (substrate)
           · host/profile location resolution  ($data / $cache / $repo)
           · atomic write + pidfile lock + completion marker
           · loader dispatch · canonical TOML round-trip
  ───────────────────────────────────────────────────────────────
        ▲ consumes                              ▲ consumes
  Layer 1a  FETCH (manifest)            Layer 1b  CACHE (produce-or-load)
   · datasets.toml (hand-authored)       · @cached, cached.toml (machine-gen)
   · uri/shell fetch                     · param-hash key
   · identity = source (uri+sha256)      · identity = hash(args)
```

The own-language `fetcher` (fetch ladder rung 1) is structurally a *production*
mechanism, not a fetch one — it is `@cached` with a different identity model (a declared
name vs a parameter hash). So rung 1 belongs conceptually with Layer 1b; the irreducible
"fetch external dependency" core is rung 4 (uri) plus rung 2 (shell). Rung 3 (cross-
language delegate) is reserved/YAGNI for a niche tool — keep it spec-only.

## The invariant: a one-way import arrow

```
store/      imports ONLY stdlib + platformdirs + (lazy) format readers
fetch (1a)  imports store              — never cache
cache (1b)  imports store              — never fetch
```

As long as the arrow points up, extracting `store` (or `cache`) into a standalone package
later is a `git mv` + a manifest file, decided whenever — not now. This is the whole
discipline; everything else is reversible.

## Dependencies do **not** cleave along the fetch/cache line

The data-science stack (pandas / xarray / netcdf / …) belongs to **loaders**, which live
in Layer 0 and are shared by both consumers, and are already gated **per-format** (the
existing `[csv]` / `[nc]` / … extras). The cache layer adds essentially no new hard
dependency (TOML + SHA + a canonical-JSON serializer for the param hash). So there is no
dependency seam between fetch and cache to exploit — which removes the last argument for a
forced package split, and means **no `[cache]` extra is needed**.

## Recommendation (and what spec-v2.1 encodes)

Start with the **"inside" form** in both languages; keep packaging free to change later.

| | Layer 0 substrate | Fetch (1a) | Cache (1b) | install |
|---|---|---|---|---|
| **Python** | `datamanifest/store/` | `datamanifest` | `datamanifest.cache` | `datamanifest` (no `[cache]` extra) |
| **Julia** | `DataManifest/src/Storage.jl` | `DataManifest` | `DataManifest.Cache` | weakdep extension for heavy readers |

Why not three wheels now: premature for a mostly-solo, niche project — three release
cycles, inter-package pins, "which repo do I file this in." You get ~80% of the benefit
from clean internal modules + the import rule. **Trigger to actually split:** someone
wants the substrate (or the cache) *without* the manifest, or the dep footprints diverge.
The natural standalone, if it ever happens, is **Layer 0** (`datastore` / `DataStore`) —
it's the most generally useful and least datamanifest-specific piece.

### Julia's forcing function

Julia can't depend on a *submodule* of another package. So the moment cache becomes its
own package, the substrate **must** also become its own package (`DataStore`), giving the
three-package monorepo (`packages/` folder, à la LGMRecons). There is no "one package +
optional cache" middle ground in Julia as there is in Python — the closest analogue to
Python's per-format extras is **weakdeps + package extensions** for the heavy readers.

## Python file-move sketch (when implemented)

`storage.py` is already a pure leaf. The only mis-filed code is the materialize/lock block
living inside `pipelines.py` next to the fetch logic.

```
datamanifest/
  store/
    locations.py   ← today's storage.py (verbatim rename)
    materialize.py ← LIFTED from pipelines.py (materialize, is_complete,
                      _acquire_lock, _pid_alive, _read_lock_pid, remove_path)
    loaders.py     ← today's default_loaders.py
  database.py      ← Layer 1a (imports store)
  pipelines.py     ← Layer 1a fetch ladder, minus the materialize block (imports store)
  cache/           ← Layer 1b, NEW (imports store; never database/pipelines)
```

~95 lines relocate (the materialize block + two renames); the fetch logic, the `Database`
model, and the public `__init__` surface are unchanged. Two public facades: the existing
manifest exports, and `from datamanifest.cache import cached`.

## Relation to the spec

None of the *code* structure touches `SCHEMA.md` — the spec governs on-disk TOML formats
and resolution ladders, not module layout or distribution. The layering is already
expressed at the **conformance-capability** level (`storage` is independent of
`cache-produce` / `cache-gc`); spec-v2.1 only corrects the prose that had over-specified
this independence as a *separate package*.
