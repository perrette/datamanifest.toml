# Discussion seed: caching, dataset storage layout, and scope boundaries

**Status:** brainstorm — *not yet designed*. This file captures a stream of design
thoughts (verbatim intent, reorganized by theme) plus relevant prior art, to seed a
**separate discussion session**. Nothing here is decided. Treat the "Considerations"
notes as framing for that discussion, not conclusions.

**Author of the thoughts:** Mahé (maintainer of `datamanifest.toml`, the Python
`datamanifest`, and `DataManifest.jl`).

---

## 0. Context — what was just built (so a fresh session can orient)

Three repos move together (see `design/language-namespaces.md`):

- **`datamanifest.toml`** — the normative spec (this repo).
- **`datamanifest`** — Python implementation (PyPI `datamanifestpy`).
- **`DataManifest.jl`** — Julia implementation.

Just completed (schema **v1**, the `_LANG` language-namespaces work):

- Datasets now separate the **language-agnostic contract** (`uri`/`sha256`/`format`/
  `version`/`extract`/`local_path`/`requires`/…) from **per-language executable
  bindings** under a structural `_LANG` namespace: `[<ds>._LANG.<lang>].fetcher/.loader`
  (as `module:function` refs) and top-level `[_LANG.<lang>.loaders]` format maps.
- Resolution ladders: **fetch** = own → shell → (opt-in peer) → uri → error;
  **load** = own → manifest format default → built-in default → error (**load never
  delegates**). Delegation/peer-CLI runtime is deferred (a future 4th roadmap).
- Structural `_*` keys preserved verbatim; lossless round-trip of foreign `_LANG.*`.
- A shared **conformance fixture suite** lives in this repo (`tests/fixtures/`), tagged
  by **capabilities** (`lang-read`, `lang-write`, `shell-fetch`, `delegation`). Each
  implementation pins to a spec **git tag** (`spec-v1.0`) and verifies fixtures by
  **per-file content sha256** (no submodule, no vendored copy), running only the
  capabilities it implements and skipping the rest — so the two languages can diverge
  in pace without forking the spec. "Conformance" = a declared capability subset + a
  pinned spec tag, surfaced in each tool's README.

Current storage model (the starting point for everything below): a **single shared
datasets folder** (default `~/.cache/Datasets`), with a per-dataset storage **key**
derived from host + path + **version**, so multiple versions coexist on disk.
Per-dataset knobs include `extract`, `skip_download`, `skip_checksum`, `local_path`.

---

## 1. The questions raised (organized by theme)

### Theme A — On-disk cache fragility (tactical, near-term)

- The `extract` true/false flow, together with `skip_download` and checksum
  verification, feels **fragile when `extract = true`** — the checksum can break.
  - *Likely root cause:* when `extract=true`, the checksum is computed over the
    **extracted directory tree**, which is sensitive to extraction details
    (file order, timestamps, tar implementation), whereas hashing the **downloaded
    archive** would be stable. (Cf. Artifacts/DataDeps, which checksum the *download*.)
- **Large datasets** deliberately skip the checksum because hashing slows loading too
  much. Today this is a manual per-dataset choice (`skip_checksum`).
- "At the moment what I have seems to work" — so this is improvement, not a fire.

**Considerations to explore:** checksum the *archive* not the extracted tree; or adopt
a content-tree hash (à la Artifacts `git-tree-sha1`) for extracted content; make
verification **lazy / size-gated** (verify on first fetch, skip on subsequent loads, or
skip above a size threshold) rather than all-or-nothing; separate "integrity of the
fetch" from "integrity check on every load".

### Theme B — Is `~/.cache` the right home for the shared datasets folder?

- The shared datasets folder currently lives under the OS cache dir. Open question
  whether "cache" is semantically right — cache implies *disposable*, but these
  datasets may be expensive/irreplaceable to re-fetch.

**Considerations:** OS conventions distinguish *cache* (disposable) from *data*
(persistent) dirs — `platformdirs.user_cache_dir` vs `user_data_dir` (Python),
and Julia's depot/`Scratch` vs a data location. Choice signals intent and affects
whether OS cleaners may delete it.

### Theme C — Project-local vs global datasets folder (esp. for *produced* data)

- `datamanifest` is designed to fetch **external** resources, but can be adapted to
  fetch **project-specific** data.
- For project-specific datasets — **especially those produced by the project itself** —
  a single global folder is a **poor match**.
- Open question: should we **document/facilitate a local, project-specific datasets
  folder**? Especially in interaction with **versioning** — there is a versioning
  mechanism at the global level, but it feels "a bit fragile".

**Considerations:** this is arguably the *same* concern as the existing datasets folder,
just with a different **root** and lifetime. A resolver that supports a **local root**
(in-project) and a **shared root** (global) — see Theme E — likely subsumes it.
Produced data is "owned" by the project and version-controlled in spirit, so a local
root + the manifest's existing `version`/`key` may be enough; the fragility is worth
pinning down with concrete failing cases.

### Theme D — A standardized caching mechanism *inside code* (produce-or-load)

- Wish: a library that provides a **caching decorator (Python) / macro (Julia)** so a
  **function that produces a dataset** is paired with a **cache folder** — write the
  result once, reload thereafter. Today this is hand-rolled per project; a standard
  pattern would simplify projects and "solve it once and for all."
- Uncertainties the maintainer flagged:
  - Does this **enlarge the scope too much**?
  - It feels right for **local** datasets, not global ones.
  - Should it **surface in the datasets manifest** at all? Maybe a **separate
    `cached.toml`-style manifest** to make caching transparent to users *while keeping
    the concern separate* from external dependencies.
  - On a fundamental level, maybe the external-vs-produced distinction **doesn't
    matter** — as tooling becomes cloud-based, the **local/remote tension is
    vanishing**.

**Considerations:** there's a deep unification here — a "produced dataset" is already
just a dataset whose **`fetcher` is a project function**, cached under a (local) root,
optionally keyed by a **parameter hash**. That is exactly the `produce_or_load`
pattern. So this may not be new scope so much as *exposing the fetcher concept as an
ergonomic decorator/macro* and choosing where the bookkeeping lives (in-manifest vs a
sibling cache manifest vs purely in-code). The "separate `cached.toml`" instinct is a
separation-of-concerns call: keep one manifest but tag dataset **kind** (external dep
vs locally-produced), or split files. Worth weighing fragmentation vs clarity.

#### Reference implementation to standardize from: LGMIO `@cached`

The maintainer already has a **mature, production** version of this pattern — start the
design from it, don't invent anew:

- Macro: `~/Projects/LGMRecons/packages/LGMIO/src/Cache.jl` (the `@cached` macro +
  `save_cache`/`load_cache`/`has_cache`/`get_cache_filepath`).
- Example call site: `~/Projects/LGMRecons/packages/LGMPre/src/DataHelpers.jl:877`
  ```julia
  @cached cachetype="esm_20c_anomaly" ext="jls" \
          key=(args -> (; grid=args.grid, skip_models=args.skip_models)) \
  function load_20c_esm_anomaly(; grid="5x5",
          skip_models::Vector{String}=[...], cache_dir=nothing)
      ... expensive computation ...
  end
  ```

**API shape.** `@cached cachetype="…" key=(args -> (;…)) [ext=] [basename=] [kind=]`
wraps a function: it injects a `cached::Bool=true` escape-hatch kwarg, builds a
NamedTuple of all declared args, and runs the user's `key` closure to derive the
**hash-input metadata**.

**On-disk layout (self-describing).** `<cache_dir>/<cachetype>/<hash>/<basename>.<ext>`
plus two **sidecars** written automatically:
- `config.toml` — the re-hashable hash inputs (i.e. *the parameters that produced this
  artifact*);
- `metadata.toml` — audit/provenance: timestamp, Julia version, hostname, username, and
  a `[git]` block (commit / branch / dirty).

**Design lessons worth lifting into `datamanifest`:**
- **Atomic writes** (`.tmp` → rename) so a killed/OOM process never leaves a *corrupt*
  cache file — directly mitigates Theme A fragility for any cache datamanifest manages.
- **Pidfile locking** with stale-age refresh (dead-PID detected ~30s) so concurrent
  cluster workers don't recompute or clobber the same artifact — essential for HPC.
- **Hash-key hygiene:** `_`-prefixed kwargs are *excluded* from the hash (runtime knobs
  like parallel/serial), and a dedicated `_metadata_extras` channel feeds the audit
  sidecar *without* affecting the hash. The three-way split — *hash-affecting params* vs
  *runtime knobs* vs *audit-only extras* — is a subtle, valuable distinction.
- **Format dispatch:** `ext` inference (`DimStack`→`nc`, else `jld2`/`jls`) and a `kind`
  selector with package-extension hook points (`:dimstack` built-in, `:chain` via an
  ext) — this is precisely `datamanifest`'s `format` + `_LANG.loaders` concern.
- **Cache-dir resolution** via env vars (`LGM_CACHE_DIR` / `LGM_EXPERIMENT_DIR` /
  version-based path under a base) with an explicit `cache_dir` override — i.e. the
  project-scoped / versioned root resolution of Themes B/C/E, already solved in practice.
- **Versioned layout** with *no* cross-version back-compat (v0.5 vs v0.6 dirs).

**The striking convergence with `datamanifest`.** LGMIO's per-artifact `config.toml` is
essentially an **auto-generated mini-manifest entry**: `cachetype` ≈ dataset
name/namespace, `<hash>` ≈ the `key`/`version`, `config.toml` ≈ the entry's defining
parameters, `metadata.toml` ≈ provenance, the producing function ≈ a `_LANG.<lang>.
fetcher`, `ext`/`kind` ≈ `format`/`loader`. So the maintainer's floated "**`cached.toml`
to make caching transparent**" idea is *already implicitly implemented* by these
sidecars. The open question becomes whether `datamanifest` should:
1. provide the `@cached` macro (Julia) and an equivalent **decorator** (Python,
   cf. `joblib.Memory`) as a thin layer over its existing fetch/load + a **local
   storage root**, with the param-hash as `key`;
2. **standardize the sidecar/provenance format** (`config.toml` + `metadata.toml`) —
   possibly as a spec convention or a `_PROVENANCE`-style structural table — so produced
   caches are transparent and portable across the Python/Julia tools;
3. adopt the **atomic-write + lockfile** robustness as the default for any cache it owns.

This is the most concrete, highest-confidence thread to pull on in the new session:
generalize LGMIO `@cached` into the cross-language `datamanifest` story rather than
leaving every project to re-roll it.

### Theme E — Project-keyed and/or distributed (multi-root) storage

- Idea: handle the global store **like Claude Code does** — a central folder keyed by
  the **project's full path**, so different projects are separated within the cache.
- And/or support **several datasets folders inside one project** — a **distributed
  datasets folder**: at least **local + shared** (two roots), possibly more.
- Note: "distributed" is a concept in its own right (beyond just local+shared).

**Considerations:** two distinct but compatible ideas — (1) **partitioning** the shared
store by project identity (path-hash keyed subdirs, like `~/.claude/projects/<hash>` or
HuggingFace's per-repo cache dirs); (2) **multiple roots** with a search/resolution
order (read from any; write produced data to local, cached deps to shared). A
"datasets-folder resolver" abstraction could express both: an ordered list of roots,
each with a role (shared/local/readonly), plus optional project-scoping of the shared
root. This is probably the highest-leverage, most clearly in-scope improvement.

---

## 2. The overarching scope question

> Which of these belong **inside `datamanifest`**, which belong in a **companion
> library/manifest**, and which are **out of scope**?

A useful axis for the discussion:

- **Storage policy** (Themes B, C, E) — *where* datasets live and how roots resolve.
  This is plausibly the *same* concern as today's datasets folder; unifying it inside
  `datamanifest` (a multi-root, optionally project-scoped resolver) seems coherent and
  high-value.
- **Compute caching** (Theme D) — *memoizing a computation* to disk. Related (a
  produced dataset ≈ a function-backed fetcher) but ergonomically distinct. Candidate
  for a thin, optional layer or sibling package, possibly with its own manifest, so the
  core "external data dependency" story stays clean.
- **Integrity ergonomics** (Theme A) — tactical hardening, orthogonal, do regardless.

The cloud-convergence point (Theme D) is worth taking seriously: if `fsspec`-style
"local and remote are the same filesystem" is the future, then "external dep" vs
"produced local artifact" may collapse into "an addressable object with a fetch/produce
recipe and a cache policy" — which is close to what `_LANG.fetcher` + a roots resolver
already implies.

---

## 3. Prior art to study before designing (the part the maintainer asked for)

The maintainer asked how datasets here could **leverage rather than duplicate** tools
like Julia's Artifacts and the ML/Python ecosystem. The good news: several of these map
*directly* onto the themes above, and the right move is likely to **borrow patterns /
optionally interoperate**, not reinvent.

### Julia

- **`Pkg` Artifacts (`Artifacts.toml`)** — content-addressed (`git-tree-sha1`),
  immutable, deduplicated, lazily-downloaded blobs in the shared depot; platform-gated.
  *Maps to:* Themes A (content-tree hashing of extracted data), B/E (shared,
  deduplicated store). *Not* a substitute for the manifest (Julia-only, immutable
  blobs, no produce/load/versioned-source semantics) but a strong **caching-layer design
  reference**, and a possible **backend** for a Julia consumer.
- **`Scratch.jl`** — package/project-scoped **mutable** scratch spaces in the depot.
  *Maps to:* Theme C/D — exactly the home for *produced*, non-immutable, project-local
  data and caches.
- **`DrWatson.jl`** — scientific-project assistant. `datadir()`/`projectdir()` for
  layout, and crucially **`produce_or_load`** (run a function, save its output keyed by
  params, reload next time) and `@tagsave`. *Maps to:* Theme D — this **is** the
  produce-or-load pattern the maintainer wants; study its API before designing one.
- **`DataDeps.jl`** — declarative external data dependencies with checksums + post-fetch
  hooks; the Julia analog of `pooch`. *Maps to:* the current fetch side; compare
  checksum handling (it hashes the download).
- **`Memoize.jl` / `Memoization.jl` / `LRUCache.jl` / `Caching.jl`** — the
  decorator/macro caching primitives. *Maps to:* Theme D's "macro in Julia".
- **`Preferences.jl`** — package-level persistent config; *maps to:* configuring the
  datasets-folder root(s) per project/package.

### Python

- **`pooch`** — "A friend to fetch your data files." Download + cache + verify
  (sha256/md5) via a registry of URL→hash; used by SciPy/scikit-image. The closest
  direct analog to `datamanifest`'s fetch+checksum side. *Study for:* Theme A integrity
  ergonomics and registry design.
- **`joblib.Memory`** — on-disk **caching decorator** keyed by args hash. *Maps to:*
  Theme D's "decorator in Python" — the reference implementation.
- **`fsspec` (+ `filecache`/`simplecache`)** — unified local/remote filesystem
  abstraction (s3, gcs, http, …) with a caching layer. *Maps to:* Theme D's
  local/remote-convergence point — arguably the abstraction that makes the tension
  vanish.
- **`platformdirs`** — OS conventions for `user_cache_dir` vs `user_data_dir`.
  *Maps to:* Theme B.
- **`intake`** — declarative **data catalogs** (sources + loaders). *Maps to:* the
  manifest-as-catalog idea; compare its catalog/driver model.
- **Hugging Face `huggingface_hub` / `datasets`** — hash/snapshot-addressed cache under
  `~/.cache/huggingface`, per-repo dirs, revision pinning. *Maps to:* Themes A/B/E —
  a mature example of content-addressed, revision-pinned, partitioned caching for large
  ML data/models.
- **`DVC`** — git-adjacent data versioning with remote backends and pipelines. *Maps
  to:* Theme C/D versioning of produced data (heavier, pipeline-oriented).
- **`diskcache` / `cachetools`** — general disk/memory caches (lighter-weight options).

---

## 4. Concrete open questions to take into the discussion session

1. **Integrity:** checksum the archive vs the extracted tree vs a content-tree hash?
   Make verification lazy/size-gated? (Theme A)
2. **Location semantics:** cache dir vs data dir for the shared root? (Theme B)
3. **Roots model:** introduce a **multi-root resolver** (local + shared, ordered,
   role-tagged), and/or **project-scoped partitioning** of the shared root (Claude-Code
   / HF style)? Does this subsume the "project-local datasets folder" need? (Themes C, E)
4. **Produce-or-load:** ship a caching decorator/macro? In-core or sibling package?
   Surface in the datasets manifest, a separate `cached.toml`, or in-code only? Is a
   "produced dataset" just a function-backed `fetcher` + local root + param-key?
   (Theme D)
5. **Scope boundary:** what stays in `datamanifest` (storage policy, integrity) vs a
   companion (compute caching)? Does the cloud/`fsspec` convergence argue for collapsing
   the external-vs-produced distinction entirely? (Theme 2)
6. **Interop, not duplication:** should a Julia consumer be able to back a dataset with
   an **Artifact** / **Scratch** space, and a Python consumer with **pooch**/**fsspec**
   caches, behind the manifest's contract? (Theme 3)

---

## 5. Pointers

- Spec & schema: `SCHEMA.md`, `CHANGELOG.md`, `design/language-namespaces.md` (this repo).
- Conformance fixtures + capability model: `tests/fixtures/` (+ `README.md`), pinned via
  tag `spec-v1.0`.
- Implementations: `~/Projects/datamanifest` (Python), `~/Projects/DataManifest.jl`
  (Julia) — both now at schema v1.
- Current storage entry points to read first when designing: the Python `Database`
  (datasets-folder resolution, `key`/`version` derivation, `extract`/`skip_*` handling)
  and the Julia `Databases.jl`/`Config.jl` equivalents.

---

## 6. Decisions (design session, 2026-06-02)

Worked through Themes A, B, C, E and the vocabulary in discussion, grounded against
the **Python** implementation (`datamanifest/{config,database,pipelines}.py`). Theme D
(the `@cached`/produce-or-load layer) and the scope boundary (§2) are **still open**.

### A — Integrity: keep the schema, stop the redundant work

Grounded findings (correcting the brainstorm's framing):
- **TOFU auto-fill confirmed** (`verify_checksum`, `database.py:598`): an empty
  `sha256` is computed and persisted on first download. That is how a new dataset's
  hash is established — so `sha256` cannot be overloaded to mean "never verify."
- **Re-hash happens on every *load*, not just fetch** (`pipelines.py:567-570`):
  `load_dataset → download_dataset`, and the "already exists" branch calls
  `verify_checksum`. *This* is the cost `skip_checksum` was invented to avoid on
  gigabyte cluster datasets.
- **The tree hash is more robust than the doc feared.** `sha256_folder`
  (`config.py:25`) sorts dirs+files and hashes **contents only** — no mtimes, no mode,
  no order dependence. The genuine break sources are (a) **extraction-tool file-set
  differences** (`.DS_Store`, `__MACOSX/`, a wrapper top-dir) and (b) **cost** of
  reading every byte on every load.
- A db-level **`skip_checksum_folders`** knob already exists (`database.py:595`) — a
  coarse "don't hash extracted trees."

**Decisions:**
- **Keep** `sha256`, `skip_checksum`, `skip_checksum_folders`, TOFU — **no schema change.**
- **Stop re-hashing on every load.** Verify/record once at download; on the
  already-exists path, skip re-verification unless explicitly requested (e.g. a
  `verify=True` / `--check` opt-in). Removes most of the *reason* to set
  `skip_checksum` on big data, without changing its meaning.
- **Parked (future opt-in):** hash the *archive* instead of the extracted tree for
  `extract=true`. It would change what `sha256` stores (existing recorded hashes would
  need re-recording), so it is opt-in and later — not a default.

### B — Location semantics: it's all reconstructible; the axis is *control*

- **Everything datamanifest manages is reconstructible** — external data by re-fetch
  (the author's contract is to keep it remotely available), produced data by re-running
  the producer. So the cache-vs-data *semantic worry dissolves*: it is all "cache" in
  the reconstructible sense. `kind = external|produced` was rejected as the wrong concept
  (a produced artifact is the textbook cache — cf. the `@cached` macro's own name).
- **The real axis is *control over reconstruction*, not provenance or cost.** Remote
  availability is outside your control (protect the local copy); your own compute is
  under your control (safe to treat as disposable). Protect against the failure mode you
  cannot mitigate.
- **Switch path resolution from hardcoded `XDG_CACHE_HOME` to the `platformdirs`
  conventions** (`user_data_dir` / `user_cache_dir`). The default locations are
  **language-independent and normative** — Python and Julia MUST resolve the same dataset
  to the **same path** (at minimum for *reading*), so the shared store is genuinely shared.
  A tool MUST NOT substitute a language-native location (e.g. Julia's depot) for the
  defaults. (Revises an earlier note that let the tools diverge.)

### C + E — multi-root resolver (E subsumes C)

- **Three roots, each = a location + a retention policy:**

  | root (`store=`) | location | policy |
  |---|---|---|
  | `data` *(default)* | `platformdirs.user_data_dir`/Datasets | persistent, protected |
  | `cache` | `platformdirs.user_cache_dir`/Datasets | disposable, OS-cleanable |
  | `repo` | `<project_root>/datasets` | travels with the repo |

- **One new schema field: `store = "data" | "cache" | "repo"`, default `data`.** It
  selects the **write-target root**. Explicit value wins; the **producing mechanism sets
  the default** — a declared dataset → `data`; the `@cached`/produce-or-load decorator →
  `cache`. (Realizes the earlier "explicit wins, sensible guess otherwise.")
- **Read any, write by class** (chosen): reads probe roots in priority order
  `repo → data → cache`, first hit wins; writes go to the root named by `store`. The
  storage **key is already root-independent** (`build_dataset_key` → `host/path#version`),
  so `<root>/<key>` works uniformly — minimal surgery to `get_dataset_path`.
- **Coexists with `local_path`**, which is a *different* thing: `local_path` = "this
  exact file/dir, bypass the keyed scheme"; the `repo` root = "the project's keyed
  dataset folder."
- **Config lives in the manifest + env, no separate config file.** A new structural
  **`[_STORAGE]`** table holds *portable* policy (the `repo` subdir, relative — default
  `datasets`); **machine-specific `data`/`cache` locations** come from `platformdirs`
  defaults + env vars (`DATAMANIFEST_DATA_DIR` / `DATAMANIFEST_CACHE_DIR`, mirroring the
  existing `XDG_CACHE_HOME`/`DATAMANIFEST_TOML` precedent). `_STORAGE` *may* carry
  absolute overrides (with `~`/`$VAR` expansion) for solo projects, but committing
  absolute machine paths to a shared manifest is discouraged. `[_STORAGE]` round-trips
  losslessly via the existing `_*` passthrough (`db.extra`).
- **Deferred — project-scoped shared (#4, path-hash partition).** It does *not* serve the
  worktree-sharing case (different worktree paths → different buckets → duplication);
  that case is already covered by the **shared roots** (sharing) + **`repo` root**
  (isolation). Its real niche is global-namespace hygiene, addable later as *just another
  `[_STORAGE]` root* with zero core change. Skip now.

**Migration note:** the default write location moves from `~/.cache/Datasets` to
`user_data_dir/Datasets`. "Read any" still probes the `cache` root, so existing downloads
are still found; only new fetches land in `data`. Natural migration, no flag-day —
worth one line in release notes.

### Host/profile-specific roots (machine-aware storage)

Same manifest, different storage locations per machine (laptop ↔ cluster). A
location-resolution layer *below* `store=` — it changes *where* a named root lives, not
*which* root a dataset uses, and never touches the storage **key**, so the
`cached.toml`/GC identity model (below) is unaffected.

```toml
[_STORAGE]                          # portable defaults / fallback
data  = "~/data/Datasets"
cache = "~/.cache/Datasets"
repo  = "datasets"

[_STORAGE._HOST."login*.hpc.edu"]   # auto-matched by socket.gethostname()
data  = "/scratch/$USER/Datasets"
cache = "/dev/shm/$USER/cache"

[_STORAGE._PROFILE.cluster]         # explicit, selected by DATAMANIFEST_PROFILE
data  = "/work/proj/Datasets"
```

**Resolution precedence (per root):**
1. `DATAMANIFEST_DATA_DIR` / `_CACHE_DIR` env override — per-machine, not in VCS.
2. `_PROFILE.<name>` when `DATAMANIFEST_PROFILE` is set (explicit; robust to renamed
   hosts/VMs/containers).
3. `_HOST.<pattern>` first glob/regex match on the hostname (zero-config convenience;
   `login*` covers `login01..NN`).
4. Default `[_STORAGE]` scalars → else `platformdirs`.

Decision: **support both `_HOST` (auto) and `_PROFILE` (explicit), profile wins over
host.** `$USER`/`~`/`$VAR` expansion in values. This **refines the "no machine paths in
VCS" rule**: host/profile-keyed roots *are* good to commit for **shared infrastructure**
(a team's cluster — everyone benefits, and expansion keeps them per-user-portable);
**personal machines** lean on the env override instead (rung 1). `repo` is project-
relative and host-independent, so it rarely needs keying — mostly `data`/`cache`.

### Vocabulary (locked)

- Per-dataset field **`store`** (the verb: where to store *this* dataset).
- Values **`data` (default) | `cache` | `repo`**.
- Roots table **`[_STORAGE]`** (the noun: the storage places).

### D — produce-or-load (`@cached`) layer

- **In-core, thin layer** (chosen): the macro (Julia) / decorator (Python) ships inside
  `datamanifest` as a thin wrapper over the existing fetch/load + the `cache` root.
- **Unifying frame:** a "produced dataset" *is* a dataset whose fetcher is a project
  function, written to the `cache` root, keyed by a **parameter hash**. The decorator
  exposes the existing fetcher concept ergonomically; it defaults `store="cache"`.
- **Bookkeeping = a bidirectional link, which is a GC for the shared store** (prior art:
  Julia depot `Pkg.gc`, Nix GC roots, HF cache refs):
  - *Cache → project (provenance/audit):* per-artifact **`metadata.toml`** sidecar —
    origin repo path, git commit/branch/dirty, host, user, timestamp. Plus a
    **`config.toml`** sidecar = the re-hashable hash inputs (the params that produced it).
    Self-describing; lifted from LGMIO `@cached`.
  - *Project → cache (liveness + glance view):* a project-side **`cached.toml`**
    (`Manifest.toml` analogue) — the registry of **function-produced** datasets (the
    `@cached` concern), listing them by **portable key** (`cachetype/hash`), not absolute
    path. **It is not tied to the `cache` *store*** — `store="cache"` is a storage tier;
    `cached.toml` is about *how a dataset was produced* (a function), orthogonal to where
    it lives. It exists precisely because produced datasets are kept out of the
    hand-authored `datasets.toml`.
  - *Dual roots for GC:* **`datasets.toml`** roots *declared/fetched* datasets (including
    those in the `cache` store — they are re-fetchable, rooted by their manifest entry);
    **`cached.toml`** roots *function-produced* datasets (no other home). A depot-level
    **usage log** (known `cached.toml` paths + last-seen, cf. Julia's
    `manifest_usage.toml`) lets `datamanifest gc` find the produced-set roots. **Rule:**
    an artifact is collectable iff no still-existing root (either file) references its key
    (+ optional grace age). The artifact back-pointer is *audit only*, never the deletion
    authority (it goes stale / can't express multi-reference).
- **The hand-authored `datasets.toml` stays clean** — machine-generated produced entries
  never churn it (`datasets.toml` ≈ `Project.toml`, `cached.toml` ≈ `Manifest.toml`).
- **Robustness to lift from LGMIO** (defaults for any cache datamanifest owns): atomic
  `.tmp → rename` writes; pidfile locking with stale-PID refresh (HPC concurrency); the
  three-way hash-key split — *hash-affecting params* vs `_`-prefixed *runtime knobs* vs
  *audit-only extras*.
- **Phasing (confirmed):** *Phase 1* with the decorator — sidecars only
  (`config.toml` + `metadata.toml`), simple, self-describing. *Phase 2* when the shared
  cache accumulates cruft — `cached.toml` index + usage-log + `datamanifest gc`.
- **`cached.toml` commit policy (confirmed):** gitignored **per-machine state by
  default**; **opt-in commit** for projects wanting shared produced-cache reproducibility
  (the `Manifest.toml` convention — libraries ignore, apps commit).

### §2 — scope boundary (resolved)

- **It all stays in `datamanifest` core.** Storage policy and the produce-or-load layer
  are in-core (thin); no companion package.
- **The external-vs-produced distinction has collapsed** into one concept: *an addressable
  object = a fetch-or-produce **recipe** + a **key** + a **store** + a cache policy.*
  "External" = uri/shell/rsync recipe, source-identity key; "produced" = function recipe,
  param-hash key. Everything else (roots, `store=`, sidecars, GC, loaders) is
  recipe-agnostic. The only genuinely new axis the core must grow is **param-hash keying**.
- **Backends: built-in native fetchers stay the default**, deferred otherwise. HTTP/file
  use native modules (`httpx` / `Downloads.download`), git/rsync are the only subprocess
  fetchers (unavoidable). `fsspec`/cloud/CAS backends are **not** adopted as a core model
  (fsspec's mount/lazy paradigm ≠ datamanifest's materialize-to-path model); if added,
  they come as targeted, optional, per-language extras behind the recipe interface.
- **`fsspec`/mount re-homed as a future *store type*** (`store="mount"`, transient/virtual)
  rather than a fetch-model change — slots into the same `[_STORAGE]` resolver, deferred.

### Spec status

The storage model was **promoted into the normative spec** (`SCHEMA.md`) — schema stays
**1**, this is **spec-v1.1**: the `store` field, the `[_STORAGE]` table (with `_HOST` /
`_PROFILE`), the materialization×retention store semantics (incl. `mount`), and two new
capabilities **`storage`** and **`mount`**. Default root locations are normative and
language-independent (same path across tools); host/profile *precedence* stays
implementation-defined.

### Still open / next

- **Fixtures + CHANGELOG + spec tag** for spec-v1.1 (add a `storage`/`mount` fixture to
  `tests/fixtures/`, note the bump, cut `spec-v1.1`).
- **Implementation** (in `~/Projects/datamanifest` + `DataManifest.jl`), proposed order:
  ① the shared *safe-materialization* primitive (lock-on-`<root>/<key>` + atomic
  `.tmp→rename` + completion marker), used by fetch / extract / produce alike;
  ② the multi-root resolver + `store=` / `[_STORAGE]`; ③ the `@cached` decorator on top;
  ④ (later) `cached.toml` + GC; (later) `mount` store; (later) cloud backends.
