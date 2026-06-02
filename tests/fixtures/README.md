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
