# Language bindings

By default a dataset is fetched by downloading its `uri` and loaded by its `format`'s
built-in loader. To customize either, attach **bindings**: a **fetcher** is the function
that obtains the dataset's bytes, a **loader** the function that opens them into memory,
and a binding names which function to call (plus, optionally, its arguments). All
executable references are `module:function` references — **never inline code**, in any
language.

## Binding forms: string or table

Every binding takes one of two interchangeable forms:

```toml
loader = "mypkg.loaders:load_sst"                       # string
loader = { ref = "mypkg.loaders:load_sst",             # table (parameterized)
           args = ["$path"], kwargs = { decode = false } }
```

The string is an **alias** for the ref-only table (`"M:f"` ≡ `{ ref = "M:f" }`). Call
semantics follow the *arguments*, not the syntax: with no `args`/`kwargs` the tool makes its
**conventional call** (a loader receives the dataset path; a fetcher the standard fetch
context); with `args`/`kwargs` the call is **explicit** — `ref(*args; kwargs...)`, nothing
auto-injected, runtime values passed via `$var` substitution (`$path`, `$download_path`, …).
A writer emits the **string** whenever there are no arguments.

*Normative: [SCHEMA.md §Binding forms](../schema.md#binding-forms-string-or-table).*

## Where bindings live

```toml
# Per-dataset, language-explicit:
[ocean_temp._LANG.python]
loader = "mypkg.loaders:load_argo"
[ocean_temp._LANG.julia]
loader = "MyPkg:load_argo"

# Project-wide format defaults, per language (format -> binding):
[_LANG.python.loaders]
csv = "pandas.io.parsers:read_csv"
nc  = "xarray:open_dataset"
```

`shell` is the **language-agnostic** fetcher — a command template (the *same* command for
every tool), so it sits directly on the dataset:

```toml
[model_output]
format = "nc"
shell  = "make model_output OUTPUT=$download_path"
```

## Language-implicit (bare) bindings

A single-language project can skip the `_LANG.<lang>` wrapper entirely. A **bare**
`fetcher`/`loader` on the dataset, and a top-level `[_LOADERS]` format map, are read as
bindings in the **running tool's own language**:

```toml
[ocean_temp]
uri    = "https://example.com/argo.nc"
format = "nc"
loader = "mypkg.loaders:load_argo"     # bare = own language; no [._LANG.python]
```

Precedence: an explicit `[<ds>._LANG.<self>]` binding overrides the bare one, and
`[_LANG.<self>.loaders]` overrides `[_LOADERS]`. Bare bindings are the single-language
form; **multi-language manifests use explicit `[<ds>._LANG.<lang>]`** (which other languages
correctly skip).

*Normative: [SCHEMA.md §Language-implicit bindings](../schema.md#language-implicit-bindings-bare-fetcher-loader).*
