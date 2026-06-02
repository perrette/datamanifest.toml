# Design & schema: language namespaces in `datamanifest.toml`

**Status:** design agreed in discussion; not yet implemented past Phase 0.
**Scope:** the canonical `datamanifest.toml` spec (shared with DataManifest.jl)
and the Python implementation.

## 1. Problem

A dataset table mixes two concerns in one flat namespace:

- **the contract** — what the data *is* and how to fetch/verify it (`uri`,
  `sha256`, `format`, …): language-agnostic, the unit of reproducibility;
- **bindings** — *executable code* for a given language: how to **fetch**
  (produce the bytes) and how to **load** (read them into memory).

Because they shared one namespace, a tool that met another language's binding key
either errored (the original `julia` crash) or, once tolerant, clobbered it on
write. Root cause: no boundary between the portable contract and the
language-specific bindings.

## 2. Requirements

- **R1 — machine portability (primary).** One self-contained file lets any
  machine reproduce the project's data. The file stays whole.
- **R2 — real multi-language projects.** One repo may run *both* the Julia and
  Python tools against the *same* manifest; both must work and neither may damage
  the other's bindings.
- **R3 — forward/backward compatibility.** Readers ignore and **preserve**
  fields/tables they don't understand; never error.
- **R4 — lossless round-trip.** Read → write drops nothing, including foreign
  bindings and unknown structural tables.

## 3. What is language-specific?

Almost nothing. Sorting by R1:

| Agnostic (the contract) | Language-specific (executable bindings) |
|---|---|
| `uri`/`uris`, `sha256`, `format`, `version`, `doi`, `extract`, `skip_*`, `local_path`, `key`, `aliases`, `description`, `requires` | **fetcher** — produce the bytes (vs. the default: download `uri`) |
| | **loader** — bytes → in-memory native object (vs. the default: by `format`) |

`fetch` and `load` are the only two language-specific runtime actions, and they
get parallel treatment. All executable code is a **`module:function` reference**
— never inline code, in any language. (This unifies Julia and Python, makes code
version-controlled and testable, and removes arbitrary-code-from-manifest
entirely, which also de-fangs delegation in §6.)

## 4. File layout

Executable bindings live under a structural **`_LANG`** namespace keyed by
language tag; the dataset table itself stays fully agnostic.

```toml
[_META]
schema = 1                               # absent ⇒ v0 (legacy flat), read leniently

# ---- project-wide format-default loaders (per language) ----
[_LANG.python.loaders]                   # default loader per format, for Python
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"

[_LANG.julia.loaders]                    # foreign to the Python tool → copied verbatim
csv = "CSV:read"
nc  = "NCDatasets:Dataset"

# ---- datasets: agnostic contract at the top of each table ----
[foo]                                    # plain download; loaded by the `format` default
uri    = "https://example.com/foo.csv"
sha256 = "abc123"
format = "csv"

[bar]                                    # produced by code; custom loader
sha256 = "def456"
format = "nc"
[bar._LANG.julia]                        # in-process Julia bindings, bound to bar
fetcher = "MyPkg:build_bar"
loader  = "MyPkg:load_bar"
[bar._LANG.python]                       # in-process Python bindings, bound to bar
fetcher = "mypkg.build:bar"
loader  = "mypkg.load:bar"
[bar._LANG.shell]                        # neutral fetcher (command template); no loader
fetcher = "make-bar -o $download_path"
```

Conventions:

- **The first key under `_LANG` is always a language tag** (`python`, `julia`,
  `r`, `shell`, …), at both levels. So "keys of `_LANG` = execution contexts" —
  the property that powers delegation discovery (§6) and clean enumeration.
- **Per-dataset** `[<ds>._LANG.<lang>]` holds singular `fetcher` / `loader`
  refs bound to that dataset (either optional).
- **Top-level** `[_LANG.<lang>.loaders]` is a `format → ref` map of default
  loaders for that language. (Note the singular `loader` per dataset vs. the
  plural `loaders` format map.)
- **`shell`** is just another execution context: a `fetcher` command template
  (supports `$download_path`, `$uri`, …) and no loader (you can't load into
  memory from a shell).
- **No inline code, and no `modules`/`includes` fields.** A `module:function`
  ref *is* its module context, so importing it is idempotent (an already-loaded
  heavy module costs nothing — the point of in-process binding); that retires
  `modules`. The ref names *what* to import; *where* to find a local module is
  handled by convention — the tool puts the manifest's directory (the project
  root) on the import path automatically — which retires `includes`. (Installed
  packages import normally; only modules in non-root directories would ever need
  more, and `includes` can return as an opt-in if that case arises.)

## 5. Why `_LANG` (rather than flat `[bar.julia]`)

Flat is fully capable; name-collision is *not* the reason (language tags can be
reserved forever). Two real reasons:

1. **It reserves the dataset's *table* namespace for the contract to grow.**
   Today agnostic fields are scalars/arrays, so "any sub-table is a language"
   would work. But the contract may later want nested structure (multiple
   checksums, mirror lists, per-file metadata for `uris`, provenance). The first
   agnostic *table* would be indistinguishable from a language table without a
   hardcoded language list. `_LANG` draws the line once: under `_LANG` =
   execution context; everything else = contract. Two namespaces, owned by
   different parties (shared spec vs. each tool), evolving independently.
2. **Delegation discovery with zero prior knowledge (§6).** A tool answers
   "which contexts can handle this dataset?" by listing `bar._LANG` keys — and
   discovers contexts *it has never heard of*. A 2024 Python build meets
   `bar._LANG.rust`, doesn't know rust, but knows it's a context it doesn't own
   ⇒ a delegation candidate. Flat-layout, `rust` is indistinguishable from a
   stray agnostic field unless the tool ships a current language registry, so a
   context added after the tool was built is invisible as a delegation target.

## 6. Resolution semantics

`_LANG` is a *file-format* concern. On load, each entry collapses to a single
effective **`fetcher`** and **`loader`** for the running tool; the full `_LANG`
tree is retained (in `extra`) only for lossless round-trip. Which binding is
selected is decided at load time; the function import / subprocess is deferred to
the actual fetch/load call.

**Fetch** (output is bytes on disk — language-agnostic, so anyone may produce
them):

1. own language `[<ds>._LANG.L].fetcher` — in-process (fastest; reuses loaded
   modules);
2. `[<ds>._LANG.shell].fetcher` — run the command template (cheap subprocess);
3. **(opt-in)** another language — **delegate to that language's `datamanifest`
   peer tool** (`"peer, fetch <ds>"`), which resolves its own
   `[<ds>._LANG.<lang>].fetcher` in the right env and populates the shared cache;
   ranked by local availability + startup cost;
4. else the plain `uri` download (if any);
5. else error.

Delegation is to the **peer tool**, never a hand-rolled `julia -e …`; and it is
off by default (`--delegate` / `delegate = true`), so reproducibility stays
predictable. Multiple languages' fetchers for one dataset MUST be equivalent —
the shared `sha256` enforces it.

**Load** (output is a *live native object* — cannot cross a process boundary):

1. own language `[<ds>._LANG.L].loader`;
2. manifest format default `[_LANG.L.loaders][<ds>.format]`;
3. the tool's built-in default loader for `<ds>.format`;
4. else error.

**Loaders never delegate** — no shell, no subprocess. A subprocess could only
return *serialized* data, and the moment you serialize to a file you've written a
*fetcher* (produce a normalized artifact) + a format-default load. Hence:

> **Delegation is a fetch-phase concept only.** Cross-language data prep is
> modeled as one language's `fetcher` writing a normalized artifact
> (Arrow/parquet/netcdf) that another loads with its own format default.

Corollary: fetching / `datamanifest path` is always achievable cross-language
(peer tool or shell); `load`-into-memory is own-language-only.

## 7. Preservation contract

**One rule: own `_LANG.<self>` wherever it appears; copy every `_LANG.<other>`
verbatim.** On write, a tool of language `L` emits:

- agnostic dataset tables (sorted), each carrying its scalar contract fields, any
  unknown scalar keys (per-dataset `extra`, already shipped), its own
  `[<ds>._LANG.L]` regenerated, and **every other `[<ds>._LANG.X]` copied
  verbatim**;
- top-level `[_LANG.L]` (config + `loaders`) regenerated; **every other
  `[_LANG.X]` copied verbatim**;
- any other `_`-prefixed structural table (`_META`, future `_*`) preserved
  verbatim;
- legacy flat `[_LOADERS]` preserved if present and not migrated.

Implementation mirror: a `DatasetEntry` keeps its foreign `_LANG.X` subtrees (and
unknown scalar keys) in `extra`; the `Database` keeps foreign top-level
`[_LANG.X]` / unknown `_*` tables in a database-level `extra`. Both splice back on
write — the same passthrough pattern at two levels.

## 8. Structural vs dataset tables

> **Keys beginning with `_` are reserved/structural** — both top-level tables and
> sub-tables within a dataset. Top-level: `_META`, `_LANG`, legacy `_LOADERS`.
> Within a dataset: `_LANG`. Known ones are interpreted; unknown `_*` keys are
> preserved verbatim and otherwise ignored.

This fixes the latent bug where every top-level table is treated as a dataset,
and satisfies R3 at both levels.

## 9. Back-compat & migration

- **Read** legacy flat `[_LOADERS]` as own-language/neutral loaders; honour
  legacy `python_includes`/`julia_includes` as extra import-path entries for
  back-compat (the v1 schema has no `includes` field — the project root is on the
  path by convention).
- **Read** legacy per-dataset `julia=` / `python=` / `shell=` / `callable=` /
  `loader=` keys and keep them verbatim in the dataset `extra` (no auto-rewrite —
  that would touch another language's data). Optional one-time deprecation note.
- **Migration is opt-in**: a `datamanifest migrate` command rewrites a v0 flat
  file into v1 `_LANG` form for the tool's own language only.
- A file with no `[_META]` is read as **v0** (legacy flat), leniently.

## 10. Proposed SCHEMA.md v2 (text for the spec repo)

> **Structural keys.** Keys beginning with `_` are structural, not datasets/data
> — at the top level (`_META`, `_LANG`) and within a dataset (`_LANG`). Readers
> MUST preserve unknown `_*` keys verbatim.
>
> **Bindings.** At runtime a dataset has two language-specific actions, **fetch**
> (produce the bytes; default = download `uri`) and **load** (bytes → in-memory
> object; default = by `format`). Both are overridden under `_LANG`, keyed by
> language tag, with values that are `module:function` references (no inline
> code):
> - per dataset: `[<ds>._LANG.<lang>].fetcher` / `.loader`;
> - project-wide: `[_LANG.<lang>.loaders]` (`format → ref` defaults). Local
>   modules resolve because the manifest's directory is on the import path by
>   convention; there are no `includes`/`modules` fields.
> - `shell` is an execution context with a `fetcher` command template and no
>   loader.
>
> A conforming tool of language `L`: resolves fetch as own → shell → (opt-in)
> delegated peer → `uri` → error; resolves load as own → manifest format default
> → built-in format default → error (**load never delegates**); **owns
> `_LANG.L`** on write and **preserves every other `_LANG.*` verbatim**; never
> errors on unknown fields/datasets/structural tables.
>
> Python executes `module:function` refs via `importlib` (no `exec`/`eval`).
> Flat `[_LOADERS]` and per-dataset `julia=`/`python=`/`shell=`/`callable=`/
> `loader=` are deprecated but still read.

## 11. Cross-repo roadmap

Three repositories move together:

- **`datamanifest.toml`** — the normative spec (this repo; both tools target it);
- **`datamanifest`** — the Python implementation;
- **`DataManifest.jl`** — the Julia implementation.

> **For the future agent who executes this:** the `DataManifest.jl` notes below
> are **unverified — that repo was not scanned when this was written.** Treat
> them as expected shape only; scan the actual source and adjust before acting.

### Coordination & ordering

1. Land the **spec** v2 (Track A) plus a shared conformance fixture suite.
2. Python (Track B) and Julia (Track C) adopt in parallel against those fixtures.
3. **Delegation** (cross-language fetch) ships last — it needs *both* tools
   conformant and an agreed peer-CLI contract.

### Shared conformance suite (lives in the spec repo)

Example manifests (single- and multi-language) plus expected outcomes, run as
tests by *both* implementations — this is what actually guards R2/R3/R4 across
tools:

- round-trip **byte-stability** of a foreign-owned `_LANG.*` subtree;
- **resolution** results (which fetcher/loader each language selects, incl. the
  format-default fallbacks);
- **structural-key** preservation (`_META`, unknown `_*`).

### Peer-CLI contract (define in the spec; prerequisite for delegation)

- **Invocation:** how tool A asks tool B to fetch a dataset, e.g.
  `datamanifest fetch <name> --datasets-toml <path> [--datasets-folder <dir>]`,
  which populates the shared cache and exits non-zero on failure. No dataset
  bytes on stdout — the artifact lands in the cache and is verified via `sha256`.
- **Discovery & availability:** the PATH name of each language's CLI and how a
  tool probes that a peer (and its runtime) is installed before delegating.

### Track A — `datamanifest.toml` (spec, do first)

- Rewrite SCHEMA.md to v2 (text in §10): structural `_` keys; `_LANG` layout;
  `fetcher`/`loader` refs; resolution ladders incl. **load-never-delegates**;
  the preservation rule; deprecations; the peer-CLI contract; `schema` versioning
  (absent ⇒ v0).
- Add the conformance fixtures and a short v0→v1 changelog.

### Track B — `datamanifest` (Python)

- **Phase 0 — shipped (uncommitted).** No-write-on-read; per-dataset `extra`
  passthrough; project-root discovery; PyPI keywords.
- **Phase 1.** Treat `_`-prefixed keys as structural (top-level + in-dataset);
  preserve unknown `_*` via a database-level `extra`. Fixes the
  unknown-top-level-table bug.
- **Phase 2 (read).** Parse `[<ds>._LANG.<lang>]` (fetcher/loader) and top-level
  `[_LANG.<lang>.loaders]`; auto-add the project root to `sys.path`. Collapse to
  the effective fetcher/loader for Python via the §6 ladders (load: own →
  manifest format default → built-in default). Keep reading legacy forms.
- **Phase 3 (write).** Regenerate own `_LANG.python`; copy foreign `_LANG.*`
  verbatim. Full lossless round-trip, incl. multi-language files. Run the shared
  conformance suite.
- **Phase 4 (fetch ladder + delegation).** Own → shell → opt-in peer delegation
  → `uri`. Implement the peer-CLI consumer side.
- **Phase 5.** Deprecation handling + opt-in `datamanifest migrate`.

### Track C — `DataManifest.jl` (Julia) — UNVERIFIED, scan first

Mirror Track B against the same fixtures. Expected work:

- Treat `_`-keys as structural; parse `_LANG.julia` (own) and **preserve foreign
  `_LANG.*` verbatim**.
- Resolution ladders: fetch own → shell → delegate → `uri`; load own → format
  default (own-language only).
- **Refs-only:** replace inline `include_string` execution of `julia=` with
  `Module:function` resolution; retire `julia_modules` (idempotent `using`) and
  `julia_includes` (project-env / LOAD_PATH convention). This is the biggest
  semantic change on the Julia side and the most likely back-compat concern —
  confirm with the maintainer.
- Implement the peer-CLI (producer side) so the Python tool can delegate Julia
  fetchers, and the consumer side so Julia can delegate Python/shell.
- Run the shared conformance suite.

## 12. Decisions log

1. Namespace root **`_LANG`** ✓ (reasons in §5; not collision-avoidance).
2. Two parallel actions **`fetcher`** / **`loader`**; second `_LANG` level earns
   its keep by carrying both ✓.
3. **`module:function` refs only** — no inline code, including Julia's;
   eliminates `modules` ✓.
4. **`shell` is a `_LANG` execution context** (fetcher only) ✓.
5. **In-memory collapse** to one effective fetcher/loader per dataset; full
   `_LANG` retained for round-trip ✓.
6. **Delegation is fetch-only**; loaders are own-language/in-process ✓.
7. **`[_LANG.<lang>.loaders]`** format-default map included now; arbitrary
   *named* loader registry deferred until needed ✓.
8. Migration **opt-in**; absent `_META` ⇒ v0 ✓.
9. **Drop `modules` and `includes`** from v1: `modules` is subsumed by the
   `module:function` ref (idempotent import); `includes` is replaced by the
   convention that the tool puts the manifest's directory on the import path
   (legacy `*_includes` still read for back-compat) ✓.

### Still open
- Final fetcher-vs-`producer` wording (currently **`fetcher`**; revisit only if
  the "build/compute" connotation matters).
- Cross-language fetch **priority policy** per tool (availability + startup
  cost) — exact ordering TBD at implementation.
