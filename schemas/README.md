# Machine-readable schemas

Declarative [JSON Schema](https://json-schema.org/) (draft 2020-12) for the TOML
documents defined by `SCHEMA.md`, so external tools can validate them mechanically. These
complement the prose spec and the conformance fixtures (`../tests/`) — they do not replace
them: the prose remains normative, and several rules (resolution ladders, hash
reproduction, round-trip preservation) are behavioural and cannot be expressed in JSON
Schema.

## TOML, validated as JSON

JSON Schema validates a JSON value. TOML maps cleanly onto the JSON data model, so the
workflow is: **parse the TOML to JSON, then validate the result** against the relevant
schema. Most validators do this for you, e.g.:

```sh
# check-jsonschema (pip install check-jsonschema) — reads TOML directly
check-jsonschema --schemafile schemas/manifest.v2.1.json datasets.toml

# or parse then validate with any JSON-Schema tool
python -c 'import tomllib,json,sys; json.dump(tomllib.load(open(sys.argv[1],"rb")),sys.stdout)' datasets.toml \
  | ajv validate -s schemas/manifest.v2.1.json -d /dev/stdin
```

## Files

| File | Validates | Capability |
|---|---|---|
| `manifest.v3.json` | the hand-authored manifest (`datasets.toml`) | core |
| `cached.v3.json` | the produced-dataset index (`cached.toml`) | `inspect` |
| `config-sidecar.v3.json` | a produced artifact's `config.toml` (re-hashable key table) | `cache-produce` |
| `metadata-sidecar.v3.json` | a produced artifact's `metadata.toml` (provenance) | `cache-produce` |

The `*.v2.1.json` files are kept alongside for tools pinned to the earlier spec. **spec-v3**
changes storage (top-level folder roots; `[_STORAGE._PREFIX]` / `[_STORAGE._SCOPE]`;
`_PROFILE` reserved) and adds the produced `version` / `scope` fields; `manifest.v3.json`
allows the new `_STORAGE` sub-tables, and `config` v3 types the new fields. `cached.v3.json`
validates the **nested schema-2** `cached.toml` (`_META.schema = 2`: an array of `produced`
recipes keyed by `(scope, cachetype, version)`, each with per-variation `instances`); the
flat schema-1 form is still read by tools but always rewritten as schema 2.

## Versioning

Two version axes govern the format (see `SCHEMA.md` §Versioning), and they map onto these
files as follows:

- **Filename carries the spec-document tag** (`*.v2.1.json`). The JSON Schema encodes
  prose-level structural rules — e.g. that a `store` selector must be a `$`-reference,
  which is a spec-v2 rule, not a `_META.schema` change. So the right axis to version a
  schema file by is the spec tag, and **older versions stay alongside** new ones
  (a tool pinned to an earlier spec keeps using its file). spec-v2.1 is structurally
  identical to spec-v2 (the v2.1 change was prose only); these files apply to both.
- **`_META.schema` is asserted inside each schema** as `const: 1` (the data-model
  version). A file carrying a different `_META.schema` will (correctly) fail to validate
  against a v2.x schema.

When a future spec tag changes structure, add new files (`*.v4.json`) next to these rather
than editing them in place. Earlier-version files (`*.v1.1.json`) may be backfilled.

## Strictness notes

- **Underscore-prefixed keys are preserved, not rejected.** The spec requires readers to
  preserve unknown `_*` structural keys verbatim, so the schemas allow unknown `_`-prefixed
  keys (at the top level and inside a dataset table).
- **Unknown plain dataset fields are rejected.** Within a dataset table, a non-`_` key that
  is not a known contract field is flagged — it is almost always a typo (`shar256`). This is
  safe precisely because the file is version-pinned.
- **Behavioural rules are out of scope.** Checksum verification, the fetch/load ladders,
  hash reproduction from `config.toml`, and lossless round-trip are verified by the prose
  spec and the fixture suite, not here.
