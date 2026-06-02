# Conformance fixture suite

This directory contains the shared conformance fixtures for the `datamanifest.toml`
schema. Each fixture is a pair:

- `<name>.toml` — a manifest TOML file
- `<name>.expected.json` — machine-readable expected outcomes

Both the Python and Julia implementations reference this directory via a pinned git
submodule and run a conformance runner against it as their test suite.

## Fixture index

| File | Languages | Capabilities exercised |
|------|-----------|----------------------|
| `single_python` | python | `lang-read`, `lang-write` |
| `single_julia` | julia | `lang-read`, `lang-write` |
| `multilang` | python, julia, shell | `lang-read`, `lang-write`, `shell-fetch` |
| `unknown_structural` | python, r | `lang-read`, `lang-write` |
| `parameterized` | python, julia | `lang-read`, `lang-write`, `binding-args` |
| `storage` | (none) | `storage` |
| `config_sidecar` | (none) | `cache-produce` |
| `cached_index` | (none) | `cache-gc` |

## Expected-outcome JSON schema

```json
{
  "capabilities": ["<cap>", ...],
  "resolution": {
    "<lang>": {
      "<dataset>": {
        "fetcher": {"rung": "<rung-name>", "ref": "<ref>" | null},
        "loader":  {"rung": "<rung-name>", "ref": "<ref>" | null}
      }
    }
  },
  "preserve_verbatim": {
    "unknown_structural": ["<top-level-key>", ...],
    "lang_namespaces": {
      "top_level": ["_LANG.<lang>", ...],
      "per_dataset": {
        "<dataset>": ["_LANG.<lang>", ...]
      }
    }
  }
}
```

### `capabilities`

An array of capability tags from SCHEMA.md's Conformance-levels table:

| Tag | Meaning |
|-----|---------|
| `lang-read` | Parse `_LANG.<lang>` tables and apply the load ladder |
| `lang-write` | Regenerate own `_LANG.<self>` and preserve foreign `_LANG.*` verbatim on write |
| `shell-fetch` | Execute `_LANG.shell.fetcher` command templates in the fetch ladder |
| `delegation` | Opt-in peer-CLI delegation (fetch-ladder rung 3) |
| `storage` | Honor the `store` field and `[_STORAGE]` root resolution |
| `mount` | Support the `mount` store (mechanics unspecified in v1.1) |
| `byte-identity` | Emit canonical lexicographic key ordering (cross-tool byte-identical output) |
| `binding-args` | Execute the `{ ref, args }` table form of a binding |
| `cache-produce` | Produced (function-backed) datasets keyed by parameter hash + `config.toml`/`metadata.toml` sidecars |
| `cache-gc` | The `cached.toml` produced-dataset index, usage log, and root-reachability `gc` |

A runner filters fixtures to those whose `capabilities` array is a subset of the
implementation's declared capability set. Fixtures with unsupported capabilities are
skipped with a reason logged.

### `resolution`

Per language, per dataset: the effective fetcher and loader that a conforming
implementation MUST resolve for that dataset. Each is expressed as `{"rung": <name>,
"ref": <value>}`.

**Fetch rung names** (corresponding to SCHEMA.md §Fetch-ladder):

| Rung | Meaning |
|------|---------|
| `"own-fetcher"` | `[<ds>._LANG.<self>].fetcher` (own language, rung 1) |
| `"shell"` | `[<ds>._LANG.shell].fetcher` command template (rung 2) |
| `"delegation"` | Peer-CLI delegation, opt-in (rung 3) |
| `"uri"` | Plain `uri` download (rung 4) |
| `"error"` | No rung applies — implementation MUST error |

**Load rung names** (corresponding to SCHEMA.md §Load-ladder):

| Rung | Meaning |
|------|---------|
| `"per-dataset"` | `[<ds>._LANG.<self>].loader` (rung 1) |
| `"manifest-format-default"` | `[_LANG.<self>.loaders][<ds>.format]` (rung 2) |
| `"built-in"` | Tool's built-in default for `<ds>.format` (rung 3) |
| `"error"` | No rung applies — implementation MUST error |

`"ref"` is the resolved callable string (`module:function` or shell template). It is
`null` when no callable is involved: `"uri"`, `"built-in"`, and `"error"` rungs have
no normative callable string.

### `preserve_verbatim`

Lists every manifest key that a conforming writer MUST copy back byte-for-byte on a
read-then-write round-trip.

- **`unknown_structural`** — top-level `_*` keys that are neither `_META`, `_LANG`, nor
  `_LOADERS`. ALL writers, regardless of language, must preserve these.
- **`lang_namespaces.top_level`** — all `_LANG.<lang>` entries present at the top level.
  A writer of language `L` preserves every entry where `<lang> ≠ L`.
- **`lang_namespaces.per_dataset`** — per-dataset `_LANG.<lang>` sub-tables present in
  the manifest. A writer of language `L` preserves every entry where `<lang> ≠ L`.

`_LANG.shell` is never "owned" by any writer language, so it always appears in the
foreign set and must always be preserved verbatim.

### Parameterized bindings and `resolution`

A per-dataset `fetcher`/`loader` may be a bare `module:function` string **or** a
`{ ref, args, kwargs }` table (a parameterized binding). In `resolution`, `"ref"` is the
`module:function` string in either case (the table's `ref`). The arguments are asserted
separately, under `binding_args`.

### `binding_args` (optional)

Present for `binding-args`-capability fixtures. For each `<lang>` → `<dataset>` →
`<role>` (`fetcher`|`loader`) whose binding uses the table form, gives the exact `args`
(positional, ordered array) and/or `kwargs` (keyword table) the resolved function MUST
receive (before any `$var` substitution). Either may be omitted; bindings using the
bare-string form have no entry here.

### `storage` (optional)

Present for `storage`-capability fixtures. Asserts store selection and `[_STORAGE]`
structure (but not absolute on-disk paths, which are machine-dependent — `platformdirs` /
env / host):

- `default_store` — the `store` assumed when a dataset omits the field (`data`).
- `datasets.<ds>` — the store each dataset resolves to (its `store` field, or the default).
- `roots.base` — store-root keys that MUST be present in `[_STORAGE]`.
- `roots.host_patterns` / `roots.profiles` — `_HOST` / `_PROFILE` override keys present.

### `config_sidecar` (optional)

Present for `cache-produce`-capability fixtures. Here the fixture `.toml` is itself a
**`config.toml` cache sidecar** — the self-describing, re-hashable record written next
to a produced artifact (SCHEMA.md §Produced datasets and caching) — **not** a
`datasets.toml`. Produced (function-backed) datasets are never declared in
`datasets.toml`; they originate from a `@cached`-decorated function and their only TOML
footprint is this sidecar plus the `cached.toml` index. The sidecar's `[_META]` block
carries `cachetype` + `hash`; every other top-level key is part of the key table.

`config_sidecar` asserts:

- `cachetype` — the artifact namespace (matches the sidecar's `_META.cachetype`).
- `key_table` — the hash-affecting parameters: every non-`_META` key of the sidecar
  (runtime knobs, the `_`-prefixed keys, are excluded *before* the sidecar is written,
  so a valid `config.toml` never contains them).
- `param_hash` — the lowercase-hex **SHA-256 of the canonical JSON** of `key_table`
  (JCS: sorted keys, `separators=(",", ":")`, UTF-8, no floats/nulls). A runner MUST
  recompute and match this — it is the cross-tool reference vector.
- `key` — the storage key `"<cachetype>/<param_hash>"`.

The validator recomputes `param_hash` from `key_table`, checks it equals the sidecar's
recorded `_META.hash` (the re-hashability contract), and checks `key_table` equals the
sidecar minus `_META`, so the sidecar and the expectation cannot drift.

### `cached_index` (optional)

Present for `cache-gc`-capability fixtures. Here the fixture `.toml` is itself a
**`cached.toml`** index (not a `datasets.toml`). `cached_index.entries.<name>` asserts,
per produced-dataset entry: `cachetype`, `hash` (64 lowercase hex), `ref` (the producing
`module:function`), and `store`. Resolution / preservation blocks are empty for this
fixture.

### Byte-identity (cross-tool)

The `byte-identity` capability asserts that a logical manifest serializes to
byte-identical output across tools (canonical lexicographic key ordering at every level,
including keys inside inline `{ }` tables). This check is run by the implementation
runners — each serializes the same fixture and the outputs are diffed byte-for-byte —
rather than by an in-repo expected-bytes file, which would couple to one writer's exact
formatting.

## How a runner implements conformance tests

```
for each <name>.expected.json in this directory:
  1. Parse capabilities.
  2. If capabilities ⊄ implementation.declared_capabilities:
       SKIP <name> — log which capabilities are missing.
       continue.
  3. Load <name>.toml.
  4. (Resolution tests) For each (lang, dataset) in resolution where lang == self_lang:
       Resolve fetcher: walk the fetch ladder and verify rung and ref match.
       Resolve loader:  walk the load ladder and verify rung and ref match.
  5. (Preservation tests) Serialize the manifest back to TOML (write round-trip).
       For each key in preserve_verbatim.unknown_structural:
         Assert the serialized output contains that top-level table verbatim.
       For each key in preserve_verbatim.lang_namespaces.top_level where lang ≠ self_lang:
         Assert the serialized output contains that top-level _LANG.<lang> table verbatim.
       For each dataset in preserve_verbatim.lang_namespaces.per_dataset:
         For each key where lang ≠ self_lang:
           Assert the serialized output contains that per-dataset _LANG.<lang> verbatim.
  6. Print: PASS <name> [<caps>]
     on any assertion failure: FAIL <name> [<caps>]: <reason>

Exit non-zero if any fixture FAILED; zero if all passed or skipped.
```

"Verbatim" means the key and all its sub-keys appear with the same values in the
output. Whitespace and key ordering within a table may differ, but no key-value pair
may be dropped or altered.
