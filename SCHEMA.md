# `datamanifest.toml` — manifest schema specification

This document is the normative description of the TOML manifest format shared by the
[DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) (Julia) and
[datamanifest](https://github.com/perrette/datamanifest) (Python) tools. A manifest
declares the data dependencies of a project: each dataset's source URI, checksum,
version, format, and how to fetch and load it. Either implementation can read and write a
conforming file; each reads the language-agnostic contract fields plus its own
`_LANG`-namespaced bindings, and preserves the rest verbatim.

## Versioning

Two independent version axes govern this format:

- **`_META.schema`** (integer, stored inside the file) is the **data-model compatibility
  version**. It increments only on a breaking structural change. A file without `[_META]`
  is treated as schema v0 (legacy flat) and read leniently. Current value: **1**.
- **Spec-document version** (a git tag such as `spec-v1.0`) versions the prose,
  examples, and fixture suite. An implementation conforming to "schema 1, spec ≥ v1.0"
  pins to a spec tag; the spec may advance without retroactively breaking a pinned
  implementation. The spec is never forked per language package: one normative document,
  one fixture suite, multiple implementations at varying capability levels.

## Structural keys

Keys beginning with `_` are **structural** — they are not dataset tables. At the top
level, the defined structural tables are `_META`, `_LANG`, `_STORAGE`, and `_LOADERS`.
Within a dataset table, the only defined structural sub-table is `_LANG`. Readers MUST
preserve unknown `_*` keys verbatim and MUST NOT treat them as datasets or drop them on
write.

## Top-level layout

A v1 manifest is a TOML document with:

- **`[_META]`** — schema metadata (`schema = 1`).
- **`[_LANG.<lang>]`** — project-wide execution-context configuration for language
  `<lang>`. The sub-key `loaders` is a `format → ref` map of default loaders for that
  language.
- **One table per dataset**, keyed by the dataset name. Dataset tables hold the
  language-agnostic contract fields, an optional `_LANG` sub-table for per-dataset
  bindings, and optional **bare (language-implicit) `fetcher`/`loader` bindings** (see
  *Language-implicit bindings*).
- **`[_STORAGE]`** — optional storage configuration: a host-aware namespace of **folder
  variables** (built-in `data`, `cache`, `repo` plus user-defined keys), the project-wide
  `default` selector, the `_HOST` override sub-table, and the `_PREFIX` / `_SCOPE` content
  sub-tables. See Storage.
- **`[_LOADERS]`** — a language-implicit `format → binding` loaders map (tolerated; the
  bare counterpart of `[_LANG.<self>.loaders]`). See *Language-implicit bindings*.

Example:

```toml
[_META]
schema = 1

[_LANG.python.loaders]
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"

[_LANG.julia.loaders]
csv = "CSV:read"
nc  = "NCDatasets:Dataset"

[foo]
uri    = "https://example.com/foo.csv"
sha256 = "abc123"
format = "csv"

[bar]
sha256 = "def456"
format = "nc"
shell  = "make-bar -o $download_path"   # language-agnostic shell fetcher

[bar._LANG.julia]
fetcher = "MyPkg:build_bar"
loader  = "MyPkg:load_bar"

[bar._LANG.python]
fetcher = "mypkg.build:bar"
loader  = "mypkg.load:bar"
```

## Language-agnostic contract (common fields)

Every field is optional and defaults to the empty string / empty list / `false` shown.
Types are TOML types (`string`, `array of string`, `bool`).

| Field | Type | Default | Semantics |
|---|---|---|---|
| `uri` | string | `""` | Single source URI. HTTP(S), `git`/`ssh+git`/`*.git`, `ssh`/`sshfs`/`rsync`, or `file://`. Mutually exclusive with `uris`. |
| `uris` | array of string | `[]` | Batch of source URIs written into a single dataset folder under disambiguated relative paths. Mutually exclusive with `uri`. |
| `host` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `path` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `scheme` | string | `""` | Parsed from the URI (derived; tools omit it on write). |
| `version` | string | `""` | Dataset version; participates in the storage key so multiple versions coexist on disk. |
| `branch` | string | `""` | For git sources: branch/tag to clone (`--branch`). |
| `doi` | string | `""` | DOI of the dataset; also usable as a search key. |
| `aliases` | array of string | `[]` | Alternative names this dataset can be looked up by. |
| `description` | string | `""` | Human-readable description (replaces TOML comments). |
| `key` | string | `""` | Storage key (relative path under the datasets folder). Derived from host + path + version when absent. |
| `local_path` | string | `""` | **Path expression** for a user-managed exact location; may interpolate `$`-folder variables, `$USER`/env, and `~`. After interpolation: absolute → used verbatim; relative → resolved against the project root. Bypasses the keyed `<root>/<key>` layout and download. See Storage. |
| `store` | string | `default` | **Selector** choosing the folder the dataset is materialized into: a `$`-folder reference, optionally with a sub-path (`$data`, `$scratch`, `$cache/sub`). The dataset is keyed under it as `<resolved-folder>/<key>`. Omitted ⇒ the project-wide `[_STORAGE].default` selector (itself `$data`). See Storage. Honored under the `storage` capability; other tools preserve it verbatim. |
| `sha256` | string | `""` | Expected SHA-256 of the downloaded file/folder. Auto-filled on first successful download and verified at fetch time; **not** re-verified on every load (re-verification is opt-in). |
| `skip_checksum` | bool | `false` | Disable checksum verification for this dataset. |
| `skip_download` | bool | `false` | Treat the dataset as externally provided; the documented `uri` is returned as the path and no download is attempted. |
| `delegate` | bool | *(run default)* | Force the cross-language fetch rung (rung 3) on (`true`) or off (`false`) for this dataset. When omitted, the tool's run-level default applies (`--delegate` / configuration). Honored under the `delegation` capability; other tools preserve it verbatim. See Cross-language fetch. |
| `extract` | bool | `false` | After download, extract the archive (`zip` / `tar` / `tar.gz`) and use the extracted directory as the dataset path. |
| `format` | string | `""` | Data format hint used to pick a default loader (`csv`, `parquet`, `nc`, `json`, `yaml`, `toml`, `md`, `txt`, `zip`, `tar`, `tar.gz`, …). Inferred from the URI when absent. |
| `requires` | array of string | `[]` | Names of datasets that must be downloaded before this one; defines a dependency graph resolved in topological order. |
| `fetcher` | string \| table | `""` | **Language-implicit** fetcher binding — read as the running tool's own language (see *Language-implicit bindings*). Equivalent to `[<dataset>._LANG.<self>].fetcher`. |
| `loader` | string \| table | `""` | **Language-implicit** loader binding — read as the running tool's own language. Equivalent to `[<dataset>._LANG.<self>].loader`. |
| `shell` | string | `""` | **Language-agnostic** shell fetcher — a command template run as a subprocess (the same command for every tool). Fetcher only; see *`shell` fetcher*. |

## Language bindings (`_LANG`)

Executable bindings live under a structural `_LANG` namespace, keyed by language tag
(`python`, `julia`, `r`, …). The dataset table itself stays fully agnostic. (The
language-agnostic shell fetcher is a bare `shell` field, not a `_LANG` tag — see
*`shell` fetcher*.)

All executable references are **`module:function` references** — never inline code, in
any language. A local module is importable because the manifest's directory (the project
root) is on the language tool's import path by convention. There are no `includes` or
`modules` fields in v1. A binding may additionally carry **arguments as data**
(`args` / `kwargs`); these are passed to the referenced function and are never
interpreted as code (see *Binding forms*).

### Binding forms (string or table)

A **binding** is the single, unified concept used at **every** executable site — a
per-dataset `fetcher` or `loader` (`[<dataset>._LANG.<lang>]`) **and** every entry in a
project-wide `[_LANG.<lang>.loaders]` format map. It takes one of two interchangeable
forms:

1. **string** — a bare `module:function` reference; or
2. **table** — `{ ref = "module:function", args = [...], kwargs = {...} }`, with
   `args`/`kwargs` optional (see *Parameterized bindings*).

The string is an **alias** for the ref-only table — `"M:f"` ≡ `{ ref = "M:f" }` — so a
reader MUST accept either form anywhere a binding is allowed. **Call semantics follow the
arguments, not the syntax:** with no `args`/`kwargs` the tool makes its **conventional
call** (a loader receives the dataset path; a fetcher the standard fetch context); with
`args`/`kwargs` the call is **explicit** — `ref(*args; kwargs...)`, nothing auto-injected
— and runtime values are passed via `$var` substitution (`$path`, …).

**Canonical writing.** A binding with no `args` and no `kwargs` MUST be written as the
**string**; the bare `{ ref = … }` table is accepted on read but normalized to the string
on write. A binding that carries `args`/`kwargs` is written as a table.

The `shell` fetcher is **not** a `module:function` binding — it is a language-agnostic
command-template string (see *`shell` fetcher*) — so it is always a string, never a table.

### Per-dataset bindings

`[<dataset>._LANG.<lang>]` holds singular bindings for a specific dataset in language
`<lang>`. Both keys are optional, and each is a **binding** in either form (see *Binding
forms*).

| Key | Type | Semantics |
|---|---|---|
| `fetcher` | string \| table | `module:function` ref (or `{ ref, args }` table) called to produce the dataset bytes, instead of (or in addition to) downloading the `uri`. |
| `loader` | string \| table | `module:function` ref (or `{ ref, args }` table) called to load the dataset into memory, overriding the format default. |

#### Parameterized bindings (`ref` + `args` / `kwargs`)

A binding may be written as a table so one function is reused across datasets that differ
only in arguments — the same loader called with `grid = "5x5"` for one dataset and
`grid = "10x10"` for another:

```toml
[esm_5x5._LANG.julia.loader]
ref    = "MyPkg:load_esm"
args   = ["$path"]                                     # positional, in order
kwargs = { grid = "5x5", skip_models = ["CESM.*"] }    # keyword

[esm_10x10._LANG.julia.loader]
ref    = "MyPkg:load_esm"
args   = ["$path"]
kwargs = { grid = "10x10" }
```

| Key | Type | Semantics |
|---|---|---|
| `ref` | string | The `module:function` reference (required). |
| `args` | array | Positional arguments, in order (optional). |
| `kwargs` | table | Keyword arguments (optional). |

- `args` and `kwargs` are **plain data** (string, number, bool, array, table) — never
  code. `args` is an ordered list of positional values; `kwargs` keys become keyword
  parameters. Values map to each language's native types.
- A binding carrying `args`/`kwargs` is called **explicitly**: the tool calls
  `ref(*args; kwargs...)` and does **not** auto-inject any standard value. Runtime values
  are referenced by **`$var` substitution** in string values — the same variables the
  `shell` fetcher exposes (`$key`, `$version`, `$doi`, `$format`, `$branch`, `$uri`,
  `$project_root`; `$download_path` for fetchers, `$path` — the resolved dataset path —
  for loaders). The ref-only form (the bare string, equivalently `{ ref = … }`) instead
  makes the tool's conventional call and is written as the string (see *Binding forms*).
- **Type mapping is language-neutral.** A value with no TOML type — e.g. a Julia `Symbol`
  — is written as its plain string form (`weighting_method = "model"` for `:model`); the
  target function accepts the string (or coerces it at its boundary). A binding's
  arguments MUST be representable as TOML data.
- A tool that executes `<lang>` bindings but does not implement the `binding-args`
  capability MUST **error** when it encounters `args`/`kwargs`, rather than silently
  calling the function without them (which would change results). The bare-string form
  requires no such capability.
- For canonical serialization, `kwargs` keys are emitted in lexicographic order like all
  other keys (including inside an inline `{ }` table); `args` is an **ordered array**, so
  its element order is preserved as data (arrays are never reordered). Both therefore carry
  the same key order and element order across tools — **semantically identical** (and
  byte-identical via the canonical reference form; see the `byte-identity` capability).

### `shell` fetcher

`shell` is a **bare, language-agnostic** dataset field: a command template run as a
subprocess to fetch the dataset. Unlike a bare `fetcher`/`loader` (language-*implicit* —
the running tool's own language), `shell` is the **same command for every tool**, so it
belongs on the dataset table, not under the language namespace. It is a fetcher only — a
subprocess cannot return a live in-memory object, so there is no shell `loader`. The value
is a command template supporting variable substitutions: `$download_path`, `$project_root`,
`$uri`, `$key`, `$version`, `$doi`, `$format`, `$branch`, `$path_<ref>`, `$path_<i>`,
`$requires_paths`.

The legacy `[<dataset>._LANG.shell].fetcher` form is still read and preserved verbatim;
the bare `shell` field is the canonical form.

### Project-wide loaders

`[_LANG.<lang>.loaders]` is a `format → binding` map of project-wide default loaders for
language `<lang>`: each value is a **binding** in either form (a bare `module:function`
string, or a `{ ref, args, kwargs }` table — see *Binding forms*), so a format default may
be parameterized exactly like a per-dataset loader. It applies when a dataset has no
per-dataset `loader` for that language. Note the singular `loader` key per dataset vs. the
plural `loaders` format map at the top level.

### Language-implicit bindings (bare `fetcher` / `loader`)

For a single-language project the `[<dataset>._LANG.<lang>]` wrapper is needless ceremony.
A dataset table MAY therefore carry a **bare** `fetcher` and/or `loader` directly (a
binding in either form), and a top-level **`[_LOADERS]`** table MAY carry a bare
`format → binding` map. "Bare" means **language-implicit**: a reading tool interprets these
as bindings in **its own language**, exactly as if they appeared under
`[<dataset>._LANG.<self>]` / `[_LANG.<self>.loaders]`.

- **Precedence — explicit wins.** An explicit own-language binding overrides the bare one:
  `[<dataset>._LANG.<self>].loader` > bare `loader`, and `[_LANG.<self>.loaders][fmt]` >
  `[_LOADERS][fmt]` (likewise for `fetcher`).
- **Strict — fail loud.** A bare binding is **present** for the running language (bare =
  the running language), so it is treated exactly like an explicit `[<dataset>._LANG.<self>]`
  binding: if it fails to **resolve** it is an **error**, and if it resolves and then
  **raises** at run time the error **propagates** — never a silent fall-through to a
  different loader/fetcher (which could hand a program wrong-shaped data behind only a
  warning). The ladder falls through only for bindings that are **absent** for the running
  language. A manifest meant to be read by more than one language uses explicit
  `[<dataset>._LANG.<lang>]` bindings (absent — and so correctly skipped — in the other
  languages); sharing a *bare* binding across languages and expecting the others to ignore
  it is unsupported. (A tool-wide best-effort mode — e.g. "fetch everything that succeeds,
  skip the rest" — is a separate concern, out of scope for this rule and not introduced
  here.)
- **Preserve verbatim (round-trip).** A writer MUST keep a bare binding **bare** — it MUST
  NOT promote `loader = …` into `[<dataset>._LANG.<self>].loader`. A tool writes under
  `_LANG.<self>` only for bindings it generates itself, so hand-authored bare bindings
  survive a read-write round-trip unchanged and one tool never rewrites another language's
  view.

`[_LOADERS]` was previously a deprecated back-compat table; it is now **tolerated** as the
language-implicit counterpart of `[_LANG.<self>.loaders]` — read as the running tool's
format-default loaders and preserved verbatim on write. The `shell` fetcher is the
language-**agnostic** sibling of these language-implicit bindings: a bare dataset field
carrying the same command for every tool (see *`shell` fetcher*).

## Resolution semantics

At runtime, each language tool collapses the `_LANG` tree to a single effective
**fetcher** and **loader** for each dataset. The full `_LANG` tree is retained
internally for lossless round-trip.

### Fetch ladder

The tool tries each rung in order, using the first that applies:

1. `[<dataset>._LANG.<self>].fetcher`, else the bare `[<dataset>].fetcher` — in-process
   call (own language, fastest);
2. the dataset's `shell` command (else legacy `[<dataset>._LANG.shell].fetcher`) — run the
   command template (cheap subprocess);
3. **cross-language fetch** — the rare case: run a fetcher defined in another language
   (mechanism implementation-defined; the Python CLI can serve as a fallback), controlled
   by `delegate` / `--delegate`; see Cross-language fetch below;
4. plain `uri` download (if `uri` is set);
5. else error.

### Load ladder

The tool tries each rung in order:

1. `[<dataset>._LANG.<self>].loader`, else the bare `[<dataset>].loader`;
2. `[_LANG.<self>.loaders][<dataset>.format]`, else `[_LOADERS][<dataset>.format]` —
   manifest-configured format default;
3. the tool's built-in default loader for `<dataset>.format`;
4. else error.

At each own-language rung the explicit `_LANG.<self>` binding takes precedence over the
bare one. A binding that is **present** for the running language (bare, or explicit
`_LANG.<self>`) but fails to resolve is an **error**; one that resolves and then raises
**propagates**. The ladder falls through only to skip rungs that are **absent** (another
language's `_LANG.<other>` fetcher, or no own loader), never to paper over a broken present
binding (see *Language-implicit bindings*).

**Load never delegates.** A loader returns a live in-memory native object, which cannot
cross a process boundary. Cross-language data preparation is modeled as one language's
*fetcher* writing a normalized artifact (Arrow/parquet/netcdf) that another language
then loads with its own format default.

### Cross-language fetch (rung 3)

Reached **only** in the rare case that a dataset has no fetcher in the running tool's own
language, no `shell` command, and no `uri` — its bytes can be produced only by a fetcher
defined in another language (`[<ds>._LANG.<other>].fetcher`). Native / `shell` / plain
`uri` cases never reach here, so each implementation is self-sufficient for nearly all
datasets.

**How a tool runs a foreign fetcher is implementation-defined.** It MAY invoke that
language's runtime directly (e.g. `julia --project=<env> -e '…'`, writing to
`$download_path` and materializing the result itself), MAY delegate to a peer-language
`datamanifest` CLI (see Peer-CLI contract), or MAY skip the rung. The **Python
implementation is the reference** and aims to cover every language, so a tool with no
native way to run a foreign fetcher can simply **call the Python CLI as a fallback**.

Either way it moves bytes on disk only (load never crosses languages); a tool MUST fall
through to `uri` when the needed toolchain is absent; and it applies to fetched datasets
only — produced (`@cached`) datasets are not cross-language. Gated by the `delegation`
capability; the `delegate` field / `--delegate` toggles it.

## Storage

A dataset's bytes are materialized under a **store folder** at a path the consuming layer
composes: a fetched dataset lands at `<folder>/<datasets-prefix>/[<datasets-scope>/]<key>`,
a produced one at `<folder>/<cached-prefix>/[<cached-scope>/]<cachetype>/…` (see *Produced
datasets and caching*). Three independent pieces compose that path:

- **store folder** — a `$`-variable naming a top-level root (a *place* / partition): `$data`,
  `$cache`, `$repo`, or a user-defined one. A dataset's `store` **selector** picks it.
- **content prefix** — the subfolder the layer writes under: `datasets/` (fetch) or
  `cached/` (produce). A convention applied by the *layer*, never baked into the folder
  variable; configurable (see below).
- **scope** — an optional partition segment controlling *sharing*: empty ⇒ shared across
  projects, a project id ⇒ project-isolated, a group name ⇒ shared within that group.

Storage is a portable *location* layer: a selector carries the same meaning in every
implementation, and the built-in folders resolve to language-independent defaults so peer
tools share the same on-disk location without configuration. The core knows **locations
only — no lifetime policy**; disposability and GC of *produced* datasets are the cache
layer's concern (see *Produced datasets and caching*), not the core fetch engine's.

### Folder variables (store folders)

A **folder** is a named top-level location, referenced as a `$`-variable. One namespace,
three built-in members plus any number of user-defined ones:

| Folder | Default root | Nature |
|---|---|---|
| `$data` | `$DATAMANIFEST_DIR` if set, else `platformdirs.user_data_dir("datamanifest")` | persistent, protected |
| `$cache` | `$DATAMANIFEST_DIR` if set, else `platformdirs.user_cache_dir("datamanifest")` | OS-reclaimable *location* — no core lifetime policy |
| `$repo` | `<project_root>` | project-relative; travels with the repo |

A folder resolves to a **bare top-level root** — the `datasets/` / `cached/` prefix and any
scope are added *on top* by the consuming layer, so the same folder holds both fetched
datasets (`<root>/datasets/…`) and produced artifacts (`<root>/cached/…`) as siblings. A user
therefore defines a path **once** (`$scratch = "/scratch/$USER"`) and reuses it for both
layers without repeating it.

- **`DATAMANIFEST_DIR` — the application base.** A single knob for "put everything here":
  when set it is the default root of `$data` and `$cache`, so fetched data lands under
  `$DATAMANIFEST_DIR/datasets/…`, produced under `$DATAMANIFEST_DIR/cached/…`, and the tool's
  own app-state files alongside. `$repo` is unaffected (always project-relative). When unset,
  `$data` and `$cache` fall back to the OS split below.
- **Built-in defaults are language-independent.** **Python's `platformdirs` is the normative
  reference:** `user_data_dir("datamanifest")` (`$XDG_DATA_HOME/datamanifest`, default
  `~/.local/share/datamanifest`, on Linux; `~/Library/Application Support/datamanifest` on
  macOS; `%LOCALAPPDATA%\datamanifest` on Windows) and the parallel `user_cache_dir`
  (`~/.cache/datamanifest` on Linux). Every implementation MUST resolve to the identical path
  and MUST NOT substitute a language-native location (e.g. a package depot), so Python and
  Julia agree. The roots are the **bare app dirs** — the `datasets/` / `cached/` subfolders
  leave the rest of the dir free for a tool's own app-internal files (e.g. HTTP metadata).
- **User-defined folders** are any other bare key under `[_STORAGE]` (`scratch = "…"` →
  `$scratch`). The reserved keys `default`, `_HOST`, `_PREFIX`, `_SCOPE` (and the shelved
  `_PROFILE`) are not folder variables.
- **Definition vs reference.** A folder is *defined* with a **bare** key in `[_STORAGE]`
  (`scratch = "/scratch/$USER"`); it is *referenced* with **`$`** (`store = "$scratch"`).
  References always use `$` — no bare folder names anywhere (selectors included), removing any
  ambiguity between a folder alias and a literal string.

### Two field kinds

Every storage *value* is one of two kinds:

- **Selectors** — `[_STORAGE].default` (project-wide) and a dataset's `store`. A selector is
  a `$`-folder reference, optionally with a literal sub-path: `default = "$data"`,
  `store = "$scratch"`, `store = "$cache/sub"`. It resolves to `<root>[/<subpath>]`; the
  consuming layer then appends its prefix, scope, and key — a fetched dataset lands at
  `<root>[/<subpath>]/<datasets-prefix>/[<datasets-scope>/]<key>`. A dataset's `store`
  defaults to `[_STORAGE].default`, which defaults to `$data`. The storage **key** (see
  `key`) is independent of the selector, so the same dataset resolves under whichever folder
  is chosen.
- **Path expressions** — `[_STORAGE]` folder values and `local_path`. A full path that may
  interpolate `$`-folder variables, `$USER`/env vars, and `~`. `local_path` is an **exact
  location**: it bypasses the keyed layout *and* the prefix/scope composition entirely.

In a path expression `$NAME` / `${NAME}` expands to the folder variable `NAME` if defined,
otherwise the environment variable `NAME`; `~` expands to home. A folder variable MUST NOT
reference itself.

### Content prefixes and scopes

The prefix and scope compose the path *above* the key, and both default so a casual user
never sets them:

- **Prefix** — the per-layer subfolder. Resolves `DATAMANIFEST_PREFIX_<KIND>` →
  `[_STORAGE._PREFIX].<kind>` → built-in default (`datasets` for fetch, `cached` for
  produce). An empty prefix puts content directly under the folder root; the defaults are
  non-empty precisely to keep *fetched / produced / app-state* in separate subtrees (and to
  let produced-cache maintenance never reach the fetched tree), so emptying them is allowed but forfeits
  that separation.
- **Scope** — the optional partition id controlling *sharing*. Resolves
  `DATAMANIFEST_SCOPE_<KIND>` → `[_STORAGE._SCOPE].<kind>` → built-in default: **empty for
  `datasets`** (shared across all projects — the dedup default for external data) and **the
  project id for `cached`** (project-isolated). Set it to a project id for full isolation, or
  to a group name to share within a set of projects (e.g. a lab sharing one download pool).
  Because fetched datasets are never garbage-collected, the datasets scope is a pure
  locality/dedup choice with **no GC consequence**; only the cached scope affects GC (its
  project-id default preserves the no-cross-project-deletion guarantee — widening it to a
  group trades isolation for sharing within that group).

The **project id** used as the default `cached` scope resolves, first non-empty wins:
declared `[_META].project` → the **package identity** at the project root (Python
`[project].name` in `pyproject.toml`; Julia `uuid` else `name` in `Project.toml`) → a hash of
the project root's absolute path (machine-local; does not coincide across clones, so clones
do not share). Rungs 1–2 are stable across clones and branches, which is what lets those
clones share. A tool SHOULD render the chosen value to a single path-safe segment.

### Host-aware resolution (`[_STORAGE]`)

`[_STORAGE]` defines folder variables, the `default` selector, the optional `_PREFIX` /
`_SCOPE` sub-tables, and per-host overrides:

```toml
[_STORAGE]
default = "$data"                  # project-wide default selector ($-form)
scratch = "$TMPDIR"                # user-defined folder variable (a bare top-level root)

[_STORAGE._HOST."login*.hpc.edu"]  # matched against the hostname (glob/regex)
scratch = "/scratch/$USER"         # same variable, host-specific resolution
data    = "/work/$USER"            # override a built-in root, host-specific

[_STORAGE._PREFIX]                 # optional: rename the per-layer subfolders
datasets = "datasets"
cached   = "cached"

[_STORAGE._SCOPE]                  # optional: control sharing (empty = shared)
# datasets = "climate-lab"         # share downloads within a group of projects
# cached   = "myproj"              # (defaults to the project id)
```

Normative rules:

- `[_STORAGE]` and its `_HOST` / `_PREFIX` / `_SCOPE` sub-tables are **defined structural
  keys**: every conforming tool MUST parse them identically and preserve them verbatim on
  write (a tool without the `storage` capability treats the whole table as a preserved
  unknown).
- **Selectors MUST be `$`-references.** A bare folder name (the spec-v1.1 form,
  `store = "data"`) is **not** a valid selector; a `storage` tool MUST reject it. Bare keys
  appear only as folder *definitions* in `[_STORAGE]`.
- **Host-specificity is always a property of a folder variable's resolution**, never a
  per-dataset host map. A machine-specific exact path is a `local_path` interpolating a
  host-resolved variable (`local_path = "$scratch/exact/file.nc"`); there is **no**
  per-dataset `_HOST` table.
- **Folder resolution ladder (normative).** Every folder variable — built-in and
  user-defined alike — resolves through the same ladder; the first rung that applies wins:
  1. the `DATAMANIFEST_<NAME>_DIR` environment variable (`<NAME>` upper-cased:
     `DATAMANIFEST_DATA_DIR`, `DATAMANIFEST_CACHE_DIR`, `DATAMANIFEST_SCRATCH_DIR`, …);
  2. the first matching `[_STORAGE._HOST.<pattern>].<name>` entry (hostname glob/regex);
  3. the base `[_STORAGE].<name>` definition;
  4. the built-in default — `$data` / `$cache` → `$DATAMANIFEST_DIR` if set, else the
     `platformdirs` path; `$repo` → `<project_root>`. A user-defined name with no definition
     on any rung is an error.

  **Prefixes and scopes** resolve through their own short ladders
  (`DATAMANIFEST_PREFIX_<KIND>` / `DATAMANIFEST_SCOPE_<KIND>` →
  `[_STORAGE._PREFIX | _SCOPE].<kind>` → built-in default; see *Content prefixes and
  scopes*). Every tool MUST honor these names and precedences, so a single environment moves
  all tools to the same path.
- **Read resolution.** A dataset is materialized at, and read from, its composed path under
  the resolved `store` selector. If absent there, a tool SHOULD additionally probe the
  built-in folders in the fixed order `repo`, `data`, `cache` (each under its `datasets`
  prefix) and use the first where the entry exists, so a dataset materialized under a
  different folder (or by a peer tool) still resolves. Explicit paths replace the
  corresponding default and MUST be honored identically by every tool.
- **Legacy read-only location (non-normative, transitional).** Implementations whose
  pre-spec-v1.1 default datasets folder was the un-namespaced `$XDG_CACHE_HOME/Datasets`
  SHOULD probe it **last** and **read-only**, so old downloads still resolve; new writes
  never land there, and the probe is skipped when `DATAMANIFEST_DATA_DIR` (or
  `DATAMANIFEST_DIR`) is set. A back-compat aid, not part of the normative contract.
- **`_PROFILE` is reserved (shelved).** Earlier drafts defined `[_STORAGE._PROFILE.<name>]`
  overrides activated by `DATAMANIFEST_PROFILE` — a manual-label twin of `_HOST`. It is
  **not part of this spec**: host-specificity is covered by the auto-matched `_HOST`. The key
  stays **reserved** (preserved verbatim) for a possible future revision.

> **Note — the `$cache` *folder* is not the `@cached` *mechanism*.** `store = "$cache"`
> selects a *location* (the OS-reclaimable cache dir) and is independent of *how* a dataset
> is produced. Under the `$cache` folder, fetched datasets live at `<cache>/datasets/<key>`
> and produced artifacts at `<cache>/cached/<scope>/…` — **sibling subtrees**: the `datasets`
> prefix holds fetched data (source-keyed), the `cached` prefix holds function results
> (recipe-keyed, project-scoped). Any folder may hold either.

### Concurrent access and completeness

A folder may be shared between tools and between concurrent processes (e.g. HPC jobs), so
materialization MUST be safe under concurrency, and peer tools sharing a folder MUST agree
on these conventions:

- **Atomic publish.** Materialize into a temporary path within the folder and atomically
  rename it into place (`<key>.tmp` → `<key>`), so a killed process never leaves a partial
  entry that looks complete.
- **Completion marker.** An entry is *complete* iff its marker exists —
  `<key>/.complete` for a directory, `<key>.complete` for a file. Readers MUST treat an
  entry without its marker as absent (re-fetch); a writer MUST create the marker only
  after a successful, verified materialization.
- **Lock.** A writer SHOULD hold an exclusive lock `<key>.lock` (a pidfile; a lock whose
  PID is dead and older than a grace period MAY be reclaimed) while materializing, so
  concurrent workers neither recompute nor clobber the same entry.

## Produced datasets and caching (companion layer)

> **Spec-v2.1 — a companion *layer*, not a core capability.** The produce-or-load
> (`@cached`) layer sits **outside the core fetch engine** as a distinct capability layer
> built on the shared substrate it reuses (safe-materialization, folder resolution,
> loaders). This section is the cross-tool **format** spec for that layer — it stays in
> this document so both languages agree on the on-disk shape.
>
> **Packaging is not constrained by this spec.** Whether an implementation ships the layer
> as a **separate package** that depends on the core, or as an **optional module of the
> same package**, is the implementation's choice (spec-v2 over-specified this as a separate
> package; spec-v2.1 relaxes it). What the spec fixes is the **boundary**: the
> `cache-produce` / `inspect` capabilities are **never declared by the core fetch
> capability**, and **the core fetch engine keeps no garbage collection and no disposability
> policy**.
>
> The format is **additive over a `datasets.toml`**: it adds **no field to the
> hand-authored `datasets.toml`** and does not change its `_META.schema` (still **1**). A
> produced dataset reuses the existing **engine** — the storage model, the
> safe-materialization primitive, and the load ladder — but is **not declared in
> `datasets.toml`**; its only on-disk record is the machine-generated `config.toml` /
> `metadata.toml` sidecars and the `cached.toml` index, each carrying its own
> `_META.schema = 1`. The format is gated by two independent capabilities, `cache-produce`
> and `inspect`, so a companion may ship neither, one, or both.

A **produced dataset** is one whose bytes come from running a project function rather
than downloading a `uri`. It is the same "recipe + key + store + policy" object as a
fetched dataset; the distinction is purely two slots:

- the **recipe** — a `uri`/`shell`/`git` recipe with a source-identity key, versus a
  *function* recipe with a *parameter-hash* key;
- the **authorship** — a fetched dataset is **hand-authored** in `datasets.toml`; a
  produced dataset is **machine-generated**.

Everything else — stores, `store=`, the safe-materialization primitive, loaders, the
preservation contract — is recipe-agnostic and applies unchanged. The only new
normative axis is **parameter-hash keying** and its on-disk bookkeeping.

**A produced dataset has no entry in `datasets.toml`.** It originates from a function
that a tool exposes through its produce-or-load surface (the `@cached` decorator /
macro — per-language and non-normative; see below), and is recorded only after it
runs. `cachetype` is therefore **not** a `datasets.toml` field; it is a namespace that
appears solely in the machine-generated records — the `cached.toml` index entry, the
`config.toml` `[_META]` block, and the on-disk path. A conforming fetch path
(`download_dataset` and the fetch ladder) **never encounters a produced dataset**: the
two concerns share the *engine*, not the *manifest*. This keeps `datasets.toml` clean
(the `Project.toml` analogue) and confines produced, parameter-hash-keyed churn to
`cached.toml` (the `Manifest.toml` analogue).

A produced dataset is identified **by its keyword parameters**, not by content: its
storage **key** is `<cachetype>/<param-hash>`, its parameters *are* the hash inputs,
and the `config.toml` sidecar is the re-checkable record of those inputs (it is not
content-pinned by a manifest `sha256`). It defaults to **`store = "$cache"`** (the
producing mechanism sets the default; an explicit override still wins), because a
produced artifact is the textbook reconstructible cache.

> **Keyword-only.** Because the parameters double as identity, the producing function
> is **keyword-only** for hashing: an ordered positional argument list has no stable
> name→value identity to hash, so a `cache-produce` tool MUST derive the key table from
> keyword parameters only. This is a property of the produce-or-load *surface*, not a
> `datasets.toml` rule — fetched datasets keep their positional `args` per spec-v1.1.

### Parameter-hash keying

A produced dataset's identity is `(cachetype, hash-of-its-parameters)`. The
**hash inputs** are the producing function's hash-affecting keyword parameters as a
**key table**: a mapping parameter name → value. Parameters split three ways
(normative — the split, not the exact source mapping):

| Class | In the hash? | Stored where | Example |
|---|---|---|---|
| **hash-affecting params** | yes | `config.toml` sidecar | `grid = "5x5"` |
| **runtime knobs** (`_`-prefixed keys) | no | nowhere (transient) | `_parallel = true` |
| **audit-only extras** | no | `metadata.toml` sidecar | producing git commit |

How a tool derives the key table from a function's declared keyword parameters
(signature introspection, an explicit key selector like LGMIO's `key=(args -> (;…))`,
etc.) is **implementation-defined**; the **serialization and hash are normative** so
the same parameters yield the same key everywhere:

1. Build the key table from the hash-affecting keyword parameters, **excluding every
   key whose name begins with `_`** (those are runtime knobs).
2. Serialize it to **canonical JSON** (JCS, [RFC 8785]): object members sorted by
   Unicode code point at every nesting level, no insignificant whitespace
   (member separator `,`, name separator `:`), UTF-8 output with minimal JSON
   string escaping. To keep canonicalization unambiguous, **hash-input values are
   restricted to strings, integers, finite floats, booleans, and arrays/objects
   composed of those**. A finite float serializes through this same canonical-JSON
   projection — the Python reference `json.dumps` float form is normative (`1.0` →
   `1.0`, `0.1` → `0.1`) and a non-Python tool MUST reproduce it byte-for-byte.
   **`NaN` and `±Inf` are disallowed** (no JSON representation), as are **nulls**
   (an absent parameter is omitted, not encoded as null). A float-valued knob MAY
   still be passed as a string when maximal cross-tool hash stability matters,
   since float formatting is the most implementation-sensitive case. Array element
   order is significant (arrays are data); object key order is not (sorted).
3. The parameter hash is the lowercase hex **SHA-256** of those canonical UTF-8
   bytes.
4. The storage **key** is `"<cachetype>/<hash>"` — or `"<cachetype>/<version>/<hash>"`
   when an optional recipe version is set (see *Produced-artifact location*). (Tools MAY
   *display* a short hash prefix, but the on-disk directory and all references use the full
   64-hex digest.)

Canonical JSON (rather than TOML) is the hash input precisely because it has a
fully-pinned byte form that Python (`json.dumps(obj, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)`) and Julia produce **identically
today** for strings, integers, booleans, and their arrays/objects, independent of
the cross-tool TOML `byte-identity` work (for finite floats the Python form is the
normative reference a non-Python tool reproduces). So a produced
dataset resolves to the same `<cache_root>/<cachetype>/<hash>` path under either
tool (even though the artifact *bytes* a given tool writes there may be
language-specific; cross-tool *loading* of a produced artifact is not implied,
only cross-tool *addressing* and *maintenance*). The `config.toml` sidecar
stores the same key table in human-readable TOML; the hash is over its canonical
**JSON** projection, not over the TOML bytes.

[RFC 8785]: https://www.rfc-editor.org/rfc/rfc8785

### Produced-artifact location

A produced artifact composes its path exactly like any stored dataset (see Storage), using
the **`cached`** content prefix and the **cached scope**:

```
<folder>/<cached-prefix>/[<cached-scope>/]<cachetype>/[<version>/]<hash>/
```

- **folder** — defaults to `$cache`; a producing call MAY select another (e.g. `$scratch`
  for a huge artifact).
- **cached scope** — defaults to the **project id**, so artifacts are project-isolated and
  maintenance stays easy to scope (Storage §Content prefixes and scopes defines the
  project-id ladder and the shared / group / isolated declensions). Because the default
  scope is the project id, two clones of one project share, while distinct projects do not.
- **version** — optional recipe/code version (below).
- An **explicit location** — given per `@cached` call (`cache_dir = …`) or via project cache
  configuration — is used **verbatim** (`<explicit>/<cachetype>/[<version>/]<hash>`),
  bypassing folder / prefix / scope; the user owns that directory's isolation (the
  *experiment-folder* workflow). The per-call value wins over project config.

The composition affects *location only* — never hit validity, which is the key
(`cachetype` + hash) alone.

**Recipe version (optional).** A producing call MAY carry a short **`version`** string
(e.g. `"v3"`, a date). When set it becomes a path segment between `cachetype` and `hash`
(`<cachetype>/<version>/<hash>`) and is recorded in the `config.toml` sidecar and the
`cached.toml` entry. `version` does **not** enter the parameter hash; it is an explicit,
human-set **recipe/code** version, orthogonal to the parameter key and distinct from
`_META.schema` (the on-disk *format* version). Its purpose is correctness under sharing: a
change to a function's *logic* that leaves its *parameters* unchanged would otherwise read a
stale hit from another branch or clone — bumping `version` forces a miss. When unset, the key
stays `<cachetype>/<hash>`.

### Cache layout and sidecars

A produced artifact is materialized at the composed path above —
`<folder>/<cached-prefix>/[<cached-scope>/]<cachetype>/[<version>/]<hash>/` (see
*Produced-artifact location*) — via the same safe-materialization primitive (atomic publish,
`.complete` marker, `.lock` pidfile) as any other store write. The directory is
**self-describing** through two sidecars written next to the artifact:

```
…/<cachetype>/[<version>/]<hash>/
├── <basename>.<ext>      # the produced artifact (format-determined)
├── config.toml           # the re-hashable hash inputs (the key table)
├── metadata.toml         # provenance / audit (never hashed)
└── .complete             # completion marker (file form: <hash>.complete alongside)
```

**`config.toml`** (`cache-produce`) — the key table verbatim plus a `[_META]`
block, so any tool can recompute the hash and confirm the directory's identity. The
key table is written at the **root** and **first** (TOML requires root-table keys to
precede any table header), so `[_META]` comes last; reading back, the key table is
every root key except the `[_META]` block:

```toml
# --- hash-affecting parameters (the key table) ---
grid        = "5x5"
skip_models = ["CESM.*", "FGOALS.*"]

[_META]
schema    = 1
cachetype = "esm_20c_anomaly"
# version = "v3"   # optional recipe/code version (becomes a path segment when set)
# hash = SHA-256( {"grid":"5x5","skip_models":["CESM.*","FGOALS.*"]} ), canonical JSON:
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
```

(`83425a3…` is a verifiable reference vector: it is the SHA-256 of the canonical
JSON `{"grid":"5x5","skip_models":["CESM.*","FGOALS.*"]}`. Every conforming
`cache-produce` implementation MUST reproduce it.)

A tool with `cache-produce` MUST be able to recompute the hash from `config.toml`'s
key table and MUST treat a directory whose recomputed hash ≠ `_META.hash` as
**not** a valid cache hit (re-produce).

**`metadata.toml`** (`cache-produce`) — provenance only, never an input to the
hash and never an authority for cache validity:

```toml
[_META]
schema = 1

created = "2026-06-02T15:04:05Z"        # RFC 3339 UTC
tool    = "datamanifestpy 0.17.0"        # producing tool + version
host    = "login3.hpc.edu"
user    = "mahe"

[git]
commit = "1f8839c…"
branch = "main"
dirty  = false

[origin]
cached_toml = "/home/mahe/proj/cached.toml"   # the index that roots this artifact
```

### The `cached.toml` index

Produced datasets are **not** written into the hand-authored `datasets.toml`
(which stays clean — the `Project.toml` analogue). They are registered in a
sibling **`cached.toml`** (the `Manifest.toml` analogue), by default alongside
the manifest. `cached.toml` is the *liveness* root for produced artifacts: it
lists them by **portable key** (`cachetype` + `hash`), never by absolute path.

```toml
[_META]
schema  = 1
# project = "lgmpre"   # optional declared project id (else derived: package name / Julia uuid, else path hash)

[load_20c_esm_anomaly]
cachetype = "esm_20c_anomaly"
# version = "v3"      # optional recipe version (path segment when set)
hash      = "83425a30d111562d46c1fce9de7618ea7f1f54e1be72e086cba0ac63c6f2ce9b"
ref       = "lgmpre.data:load_20c_esm_anomaly"   # the producing function
format    = "nc"
```

- `cached.toml` is a **defined structural sibling format**, with its own
  `_META.schema = 1`. A tool that does not implement `inspect` need not read it.
- **Commit policy:** `cached.toml` is **gitignored per-machine state by default**
  (it indexes machine-local produced artifacts); a project that wants
  reproducible shared produced-caches MAY opt in to committing it (the
  `Manifest.toml` convention — libraries ignore, applications commit).
- A produced dataset is registered in exactly one `cached.toml`; the
  `metadata.toml` `[origin].cached_toml` back-pointer names it (audit only).

### Maintenance (inspect, filter, delete)

Both fetched datasets and produced artifacts accumulate, so a tool MAY offer **maintenance**
(the `inspect` capability): enumerate the physical store, filter it, and delete an explicit
selection. Maintenance is **user-driven, never automatic**: it surfaces what is stored and
deletes only what the user explicitly selects. There is **no automatic garbage collector** —
see *Why not automatic reachability* below.

> **Reference CLI (non-normative).** A tool exposes this however fits — like the `@cached`
> surface, the command shape is per-tool, not part of the spec. The reference design folds
> it into the existing **`datamanifest list`**: a default summary view with `--field` to pick
> columns; filter flags over the object fields (`--kind`, `--scope`, `--orphan`,
> `--older-than`, `--format`, size); and action flags on the selected set — **`--delete`**
> and optionally **`--move`** (dry-run/confirm by default). There is no separate `gc`
> command.

- **Object fields.** Each stored object — a fetched dataset or a produced artifact — exposes
  a common set of inspectable fields:
  - `kind` — `data` (fetched) or `cached` (produced);
  - `key` — `<key>` (fetched) or `<cachetype>[/<version>]/<hash>` (produced); `hash` for
    produced;
  - `location` — the resolved absolute path on disk;
  - `referenced` — whether a still-present local `.toml` roots it (its key is listed in a
    `datasets.toml` / `cached.toml`) or it is an **orphan**;
  - `scope`, `format`, `size`, `created`, and a best-effort, filesystem-derived
    **last-access** time (read from `stat`, never written on read; MAY be unknown).

  These fields are the cross-tool inspectable surface; a tool with the `inspect` capability
  MUST be able to report them.
- **View.** A tool presents a **default summary** (the most useful columns) and SHOULD let
  the user choose which fields to show.
- **Filter.** Any field is a filter predicate — `kind = cached`, `scope = <project>`,
  `referenced = false` (orphans), `last-access older than 90d`, `format`, `size` — so the
  user can target, e.g., "orphaned produced artifacts in this scope not accessed in 90 days."
- **Act on the selection.** Actions operate on **exactly** the filtered set: **`delete`**
  (remove the objects) and optionally **`move`** (relocate to another folder/scope; the
  manifest/index still resolves them by key). A tool **MUST NOT** delete everything by
  default and **MUST NOT** delete as a side effect of any other command; it SHOULD default
  to a **dry run** and require explicit confirmation. Deletion is always of a user-chosen
  set, never an automatic sweep.

**Both kinds are reclaimable, with different regeneration costs.** Deleting a fetched
dataset under `datasets/` just means it re-downloads on next use; deleting a produced
artifact under `cached/` means it recomputes. Neither destroys irreplaceable state — the
manifest and the producing function are the sources of truth — which is exactly why a
curated delete is safe and an automatic collector is unnecessary. `local_path` data and
anything outside the tool-managed `datasets/` / `cached/` trees are never touched by
maintenance.

**Why not automatic reachability.** An earlier draft computed liveness as "no manifest
references this key." That model has a hole: the record documents an artifact's *producer*,
but a **read-only consumer** — another project, or a fresh clone, reading a shared- or
group-scoped artifact it did not produce and does not list — never registers as a referrer,
so an automatic collector would reap an artifact still in active use. Rather than patch this
with ever-more-complete bookkeeping, maintenance keeps a human in the loop; liveness signals
are **advisory inputs to a filter**, not a deletion authority:

- **Last-access is filesystem-derived and best-effort — never written on read.** A tool
  reads it at inspect time from the artifact's filesystem metadata (the `stat` access time,
  falling back to the modification time or `created` when atime is unusable); it **MUST NOT**
  rewrite any sidecar, index, or `.toml` on read to record access. (Touching a file on the
  lock-free read path would contend with the produce `.lock`, serialize concurrent readers,
  and put I/O on the hot path — all for a value that is purely advisory.) Because the OS
  maintains it, a read-only consumer's use is still reflected wherever the filesystem records
  it, but the signal is coarse and may be **absent**: `relatime` advances atime at most once
  a day, and `noatime`, network, and read-only filesystems record nothing — so a tool MAY
  report `last-access` as **unknown**. It is **advisory only**, never the sole basis for
  deletion; `created` (stamped once at produce time in `metadata.toml`) is the
  always-available age signal.
- **The `referenced` field is advisory too.** "Is this orphaned?" (no still-present local
  `.toml` lists its key) is one more column to show and filter on — input to the user's
  choice, not an automatic trigger. An orphan is a strong *delete candidate*, never an
  automatic deletion.
- The per-artifact `metadata.toml` back-pointer remains **audit only** — never a deletion
  authority (it goes stale and cannot express multiple references).

The **scope** partition still helps here: it organizes the layout so "show/delete only my
project's scope" is a trivial filter, and inspecting across scopes never risks an accidental
cross-project wipe because deletion is always an explicit selection.

### What this spec does not specify

- **The `@cached` macro / decorator API** (Julia macro, Python decorator) is the
  *ergonomic surface* over this model and is **per-language, not normative** — a
  tool exposes it however fits the language. Only the on-disk formats (key hash,
  `config.toml`, `metadata.toml`, `cached.toml`), the path composition (folder / prefix /
  scope), and the maintenance rules (user-driven; no automatic deletion) are normative.
- **The artifact serialization format** (`jls`/`jld2`/`pickle`/…) is a per-tool,
  per-`format` choice (the existing `format` + loader concern); produced
  artifacts are not assumed cross-language-loadable.
- **In-place / mounted access** (the former `mount` store) is out of scope: folders are
  *locations only*, with no materialization axis. It is deferred to a future revision —
  see `ROADMAP.md` — not part of this spec; no `mount` capability is defined.
- **Cloud / `fsspec` / CAS backends** are not a core model; if a tool adds them,
  they are optional per-language extras behind the recipe interface, not a spec
  contract.

## Cross-machine sync

A stored object — a fetched dataset or an expensive produced artifact — can be **transferred
between machines** instead of re-downloaded or recomputed, because every object has a
**machine-independent address** (a fetched dataset's source key; a produced artifact's
`cachetype[/version]/hash`): the same object has the same logical address everywhere, only
the physical root differs. Sync is a transfer between two stores, gated by the optional
**`sync`** capability.

- **Target = an SSH address** (`user@host`): SSH is both the transport (rsync over ssh) and
  the host identity; no separate remote registry is required.
- **Each end resolves its own store** from its own environment (`DATAMANIFEST_*`) plus the
  manifest's `[_STORAGE._HOST]` rules — *not* from any knowledge of the remote's project
  folder. This works because syncable objects live in **machine-global** folders
  (`$data` / `$cache` / user-defined); **`$repo` (project-relative) is out of scope** for
  sync, which is exactly why the remote project location never has to be known.
- **Symmetric.** `push` and `pull` differ only in transfer direction; each side resolves its
  own store identically, so there is no asymmetry between them.
- **Writes no manifest.** Sync moves bytes only; it never edits `datasets.toml` or
  `cached.toml` on either end. A transferred object lands in the global store as an
  **orphan** (present, unreferenced) — immediately usable via read-resolution, and registered
  by the receiver's normal flow if and when its own project uses it.
- **Integrity is the transport's** (rsync verifies every file as it copies); the spec adds no
  separate artifact-level digest. **Idempotent**: a no-op when the target already holds the
  object complete (its `.complete` marker is present).
- **Scope routes it**: transferring into the same project-id scope lands in the receiver's
  matching partition; a group scope is how a team shares one expensive artifact. The recipe
  `version` keeps produced-sync safe — logic that changed bumps `version`, so a divergent
  artifact never overwrites at the same address.

**Addressing for sync.** An object is named by its identifier: a fetched dataset by `name` /
`alias` / `doi`; a produced artifact by `cachetype[/version]/hash` (full, or an unambiguous
hash prefix). Resolution to **exactly one** object is the contract; a bare `cachetype` (or
any token matching several) is ambiguous.

> **Reference CLI (non-normative).** First-order `datamanifest push <id> <ssh-host>` /
> `pull <id> <ssh-host>` transfer a **single** object; an ambiguous `<id>` errors unless
> `--batch` is given, and `--dry-run` reports the selection and total size first. Filtered
> bulk transfer reuses the selection model — `datamanifest list <filters> --push/--pull
> <host>` — rather than duplicating filters onto `push`/`pull`.

## Preservation contract

A conforming writer of language `L` MUST:

- Regenerate its own `[<dataset>._LANG.L]` from its internal state;
- Copy every other `[<dataset>._LANG.X]` (X ≠ L) **verbatim**, without parsing or
  reordering;
- Regenerate its own top-level `[_LANG.L]` (config and `loaders` map);
- Copy every other top-level `[_LANG.X]` (X ≠ L) verbatim;
- Preserve any `_`-prefixed structural table that it does not own (`_META`, unknown
  future `_*`) verbatim;
- Preserve legacy `[_LOADERS]` verbatim if present and not explicitly migrated.
- Preserve `[_STORAGE]` verbatim unless it implements the `storage` capability, in which
  case it MAY regenerate its own `_STORAGE` entries (a shared, non-language-namespaced
  table).

Implementation pattern: a `DatasetEntry` keeps foreign `_LANG.X` subtrees and unknown
scalar keys in its `extra`; the `Database` keeps foreign top-level `[_LANG.X]` and
unknown `_*` tables in a database-level `extra`. Both splice back on write.

## Conformance levels

A *capability* is a named feature that an implementation may support independently of
others. An implementation declares the capability set it supports and runs only the
fixture-suite tests tagged for those capabilities.

| Capability | Description |
|---|---|
| `lang-read` | Parse `[<ds>._LANG.<lang>]` and `[_LANG.<lang>.loaders]`; apply the load ladder. |
| `lang-write` | Regenerate own `_LANG.<self>` and preserve foreign `_LANG.*` verbatim on write (full lossless round-trip). |
| `shell-fetch` | Execute the dataset's `shell` command template (or legacy `[<ds>._LANG.shell].fetcher`) in the fetch ladder. |
| `delegation` | Cross-language fetch (rung 3, the rare case): run a fetcher defined in another language — mechanism implementation-defined (call the language's runtime, or a peer `datamanifest` CLI), with fall-through to `uri` — controlled by `delegate` / `--delegate` (see Cross-language fetch, Peer-CLI contract). |
| `storage` | Honor the `store` / `default` `$`-folder selectors and `[_STORAGE]` folder-variable resolution; materialize datasets into the selected folder at its canonical or configured root (see Storage). |
| `byte-identity` | Emit the canonical lexicographic key ordering so the same logical manifest is **semantically identical** across tools — same keys, same values, same order at every level (verified by the cross-tool fixture). This is the *guaranteed* constraint. Literal **byte-for-byte** identity is **not** assured by default: current TOML writers differ in cosmetic formatting (indentation, blank lines, inline-vs-multiline arrays), so a one-to-one byte match is not always achievable. The **Python tool is the normative reference** for the canonical byte form; tools MAY offer an opt-in path to it (e.g. `datamanifest format`, or Julia `write(...; canonical=true)`). |
| `binding-args` | Execute the table form of a binding (`{ ref, args, kwargs }`): call `ref(*args; kwargs...)` with `$var` substitution in string values. |
| `cache-produce` | **Cache-layer** produce-or-load: function-backed (produced) datasets with parameter-hash keying, optional recipe `version`, the `config.toml` / `metadata.toml` sidecars, and the `cached/` prefix + cached scope under the default `$cache` folder (§Produced datasets). Declared by the cache layer, never by the core fetch capability (packaging — separate package or submodule — is unconstrained). |
| `inspect` | The **user-driven** store-inspection toolkit (§Maintenance): enumerate stored objects (datasets + cached) with their fields (`kind`, `key`/`hash`, `location`, `referenced`/orphan, `scope`, `format`, `size`, `created`, `last-access`), filter them, and act on a selection (`delete`, optional `move`). There is **no automatic collector**: deletion is always an explicit user selection; `referenced`/`last-access` are advisory. The reference CLI exposes it as `datamanifest list … --delete`. |
| `sync` | Cross-machine transfer (`push` / `pull`) of a stored object between two stores over SSH/rsync, addressed by its machine-independent identifier (`name`/`alias`/`doi`, or `cachetype[/version]/hash`); each end resolves its own store from env + `_HOST` (`$repo` excluded); writes no manifest; integrity via rsync; idempotent (§Cross-machine sync). |

Capabilities are independent — a partial implementation may ship `lang-read` and
`lang-write` without `shell-fetch` or `delegation`. The spec and its fixture suite are
never forked per language package; divergent per-language pace is expressed by each
implementation declaring its supported capability set and pinning to a spec tag.

`_META.schema` (the integer stored in the file) is the data-model compatibility version
and is bumped only on breaking structural changes. The spec-document version (git tag,
e.g. `spec-v1.0`) tracks prose and fixture evolution independently. An implementation
conforms to "schema N, spec ≥ vX" — these two axes are independent.

## Peer-CLI contract

One way to do cross-language fetch (rung 3) is to call a peer-language `datamanifest` CLI.
This section is the normative invocation interface for any tool that does so. (A tool that
instead runs the foreign language's runtime directly does not use this contract.)

### Invocation

```
datamanifest fetch <name> --datasets-toml <path> [--datasets-folder <dir>]
```

- `<name>` — the dataset key as it appears in the manifest.
- `--datasets-toml <path>` — absolute or project-relative path to the manifest file.
- `--datasets-folder <dir>` — (optional) directory that holds the shared download
  cache. If omitted, the tool's default cache location applies.

The peer tool resolves its own `[<dataset>._LANG.<lang>].fetcher` (using its own
fetch ladder), writes the result into the shared cache, verifies `sha256` if
present, and **exits non-zero on any failure**. It produces **no dataset bytes on
stdout** — the artifact lands in the cache on disk and the calling tool reads it
from there.

### Discovery and availability

Each language's CLI is discoverable on `PATH` under a language-specific name, e.g.
`datamanifest` (Python), `DataManifest` or `datamanifest-julia` (Julia). The Python
`datamanifest` CLI is the **reference peer** (the fallback target for cross-language fetch).
Before
delegating, a tool MUST probe that the peer CLI (and its runtime) is installed and
usable; if the probe fails, the delegation rung is silently skipped and the ladder
advances to rung 4 (`uri` download). Probe commands and PATH names are left to each
implementation to document.

## Deprecations

The following v0 forms are still read for backward compatibility but SHOULD NOT be
written by conforming v1 tools:

- **Per-dataset language-named flat fields `julia=` / `python=` / `callable=`** (and any
  other `<lang>=`) — historically held **inline code**, which v1 forbids. Replaced by a
  `module:function` binding under `[<dataset>._LANG.<lang>].fetcher` (or the bare,
  language-implicit `fetcher`). Kept verbatim in the dataset's `extra` on read (no
  auto-rewrite, to avoid touching another language's data); `migrate` rewrites the
  ref-shaped ones. A tool MAY emit a one-time deprecation notice.
- **`julia_modules` / `python_includes`** — retired; the manifest's directory is on the
  tool's import path by convention. Legacy `*_includes` values are still read as extra
  import-path entries for back-compat.

Note: bare `fetcher` / `loader` (language-implicit), bare `shell` (language-agnostic), and
top-level `[_LOADERS]` are **not** deprecated — they are supported forms (see
*Language-implicit bindings* and *`shell` fetcher*). Only the inline-code language-named
fields above are legacy.

An opt-in `datamanifest migrate` command (not normative in this spec) may rewrite a v0
flat file to v1 `_LANG` form for the tool's own language.

## Conformance notes

- Readers MUST ignore unknown top-level tables and unknown fields rather than erroring,
  so that new datasets, new `_LANG` entries, and other tools' extension keys do not break
  an older reader.
- Readers MUST preserve unknown `_*` structural keys verbatim — not treat them as
  datasets, not drop them on write.
- Writers SHOULD omit derived fields (`host`, `path`, `scheme`) and any field left at
  its default value.
- Writers MUST emit all keys, at every nesting level — top-level tables (structural `_*`
  and datasets alike) and the fields within each table, including keys nested in inline
  `{ }` tables — sorted by **Unicode code-point lexicographic order** (the shared default of Python `sorted()` and Julia
  `TOML.print(sorted=true)`). No table is special-cased (no `_LOADERS`/`_META`-first). This
  guarantees **semantic identity** across tools — the same logical manifest round-trips to
  the same keys, values, and ordering through either tool (the weaker constraint that is
  always met). It does **not**, by itself, guarantee **byte-for-byte** identity: the Python
  (`tomli_w`) and Julia (`TOML.print`) serializers differ in cosmetic formatting
  (indentation, blank lines, inline-vs-multiline arrays), and current tooling does not
  always permit a one-to-one byte match. For literal byte-identity the **Python tool is the
  normative reference** for the canonical form, and a tool MAY route its output through it
  opt-in (`datamanifest format`, or Julia `write(...; canonical=true)`). Note:
  because `_` (U+005F) sorts after uppercase but before lowercase ASCII letters, an
  uppercase dataset name sorts *before* the `_*` structural tables and a lowercase one
  *after* — intended; the canonical *ordering* is the requirement, not structural-table
  placement.
- `uri` and `uris` are mutually exclusive on a single dataset.
- A file with no `[_META]` section is read as schema v0 (legacy flat), leniently.
