# Examples

Reference, human-facing examples of the formats defined by `SCHEMA.md`. Unlike
`tests/fixtures/` (the per-capability conformance suite, with machine-checked expected
outcomes), these are complete, readable, copy-and-adapt starting points.

| File | What it shows |
|---|---|
| `datasets.toml` | A full manifest: plain/DOI/GitHub downloads with checksums and extraction, project-wide format-default loaders, per-dataset loader/fetcher bindings in both the **string** and `{ ref, args, kwargs }` **table** forms, a `shell` fetcher, and a per-dataset `storage_path` location override. |

The datasets above the first divider in `datasets.toml` are real and public and fetch
out of the box; the ones below are illustrative and reference example `module:function`
names you would replace with your own.

Both implementations can load this file directly as a demo / smoke test.
