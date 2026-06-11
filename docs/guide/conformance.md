# Conformance and versioning

Two version axes (see [SCHEMA.md §Versioning](../schema.md#versioning)):

- **`_META.schema`** — the data-model version (currently **1**). A reader rejects a
  schema it doesn't understand.
- **Spec tag** (a git tag such as `spec-v5.5`) — the document/behavior revision. Carried by
  git tags and by the JSON Schema filenames in [`schemas/`](../schemas.md); older versions
  stay alongside.

A **capability** is a named feature an implementation may support independently of the
others. A tool advertises its capability set and runs only the shared conformance fixtures
tagged for those capabilities:

| Capability | What it adds |
|---|---|
| `lang-read` / `lang-write` | Read/regenerate own `_LANG` bindings, preserve foreign ones verbatim |
| `shell-fetch` | Execute the `shell` command template |
| `delegation` | Cross-language fetch (rung 3) |
| `storage` | `datasets_dir`/`datacache_dir` + `$`-symbols (incl. `$project`) + the config-file ladder + host-aware resolution |
| `byte-identity` | Canonical key ordering across tools (see below) |
| `binding-args` | The `{ ref, args, kwargs }` table binding form |
| `cache-produce` | Produced datasets + `config.toml`/`metadata.toml` sidecars |
| `inspect` | Store enumeration, filter, delete/move |
| `sync` | Cross-machine `push`/`pull` |

**Canonical ordering and the canonical form.** A writer sorts keys at every level: at the
top level the structural `_*` tables (`_META`, `_LANG`, `_LOADERS`, `_STORAGE`) come first,
then the dataset tables, each group in code-point order. This guarantees **semantic
identity** — the same logical manifest round-trips to the same keys, values, and order
through any tool. Literal byte-for-byte identity is not assured by default (serializers
differ in cosmetic formatting); the Python tool's output is the normative reference — the
**canonical form** — and a tool can opt into it (e.g. `datamanifest format`, or the
`canonical` configuration field, which routes manifest writes through the reference
serializer).

The machine-checkable fixtures live in [`tests/fixtures/`](../fixtures.md); both
implementations pin and run them.

*Normative: [SCHEMA.md §Conformance levels](../schema.md#conformance-levels).*
