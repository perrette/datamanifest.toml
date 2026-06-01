# datamanifest.toml

A small, normative specification for the **`datamanifest.toml`** manifest format — a
TOML file that declares the data dependencies of a scientific project (each dataset's
source URI, checksum, version, format, and how to load it).

The spec exists so that independent implementations can interoperate on a single
manifest. It is intentionally implementation-agnostic: the common fields are identical
across tools, and each implementation reads its own language-specific extension keys
while ignoring the others.

➡️ **[Read the schema: `SCHEMA.md`](SCHEMA.md)**

## Implementations

| Language | Repository | Description |
|---|---|---|
| Julia | [awi-esc/DataManifest.jl](https://github.com/awi-esc/DataManifest.jl) | The reference implementation: download, verify, extract, and load datasets declared in a manifest. |
| Python | [perrette/datamanifest](https://github.com/perrette/datamanifest) | A faithful Python port mirroring the Julia API, using entry-point loader references instead of inline code execution. |

## License

MIT — see [LICENSE](LICENSE).
