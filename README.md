# datamanifest.toml

A small, normative specification for the **`datamanifest.toml`** manifest format — a
TOML file that declares the data dependencies of a scientific project (each dataset's
source URI, checksum, version, format, and how to fetch and load it).

The spec is at **schema v1** (`_META.schema = 1`). The key change from v0 is the
**`_LANG` namespace**: language-specific bindings (`fetcher`/`loader` as
`module:function` references) live under `[<dataset>._LANG.<lang>]` and
`[_LANG.<lang>.loaders]`, keeping the language-agnostic contract fields separate.
Each implementation reads its own `_LANG` entries and preserves the rest verbatim,
enabling lossless round-trips in multi-language projects.

➡️ **[Read the schema: `SCHEMA.md`](SCHEMA.md)**  
➡️ **[Conformance fixtures: `tests/fixtures/`](tests/fixtures/README.md)**  
➡️ **[Changelog: `CHANGELOG.md`](CHANGELOG.md)**

## Implementations

| Language | Repository | Description |
|---|---|---|
| Julia | [awi-esc/DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) | The reference implementation: download, verify, extract, and load datasets declared in a manifest. |
| Python | [perrette/datamanifest](https://github.com/perrette/datamanifest) | A faithful Python port mirroring the Julia API, using entry-point loader references instead of inline code execution. |

## License

MIT — see [LICENSE](LICENSE).
