# Conformance and versioning

Two version axes (see [SCHEMA.md §Versioning](../schema.md#versioning)):

- **`_META.schema`** — the data-model version (always **1** today). A reader rejects a
  schema it doesn't understand.
- **Spec tag** (`spec-v4`, …) — the document/behavior revision. Carried by git tags and by
  the JSON Schema filenames in [`schemas/`](../schemas.md); older versions stay alongside.

A tool advertises **capabilities** and runs only the shared conformance fixtures whose
capability set it supports:

| Capability | What it adds |
|---|---|
| `lang-read` / `lang-write` | Read/regenerate own `_LANG` bindings, preserve foreign ones verbatim |
| `shell-fetch` | Execute the `shell` command template |
| `delegation` | Cross-language fetch (rung 3) |
| `storage` | `datasets_dir`/`datacache_dir` + `$`-symbols + `[_STORAGE]` host-aware resolution |
| `byte-identity` | Canonical key ordering across tools |
| `binding-args` | The `{ ref, args, kwargs }` table binding form |
| `cache-produce` | Produced datasets + `config.toml`/`metadata.toml` sidecars |
| `inspect` | Store enumeration, filter, delete/move |
| `sync` | Cross-machine `push`/`pull` |

The machine-checkable fixtures live in [`tests/fixtures/`](../fixtures.md); both
implementations pin and run them.

*Normative: [SCHEMA.md §Conformance levels](../schema.md#conformance-levels).*
