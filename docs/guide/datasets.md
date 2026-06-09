# Declaring datasets

A dataset table holds language-agnostic **contract fields**. All are optional; the common
ones:

| Field | Meaning |
|---|---|
| `uri` | Source to download (`https`, `git`/GitHub, `ssh`, an object store `s3://`/`gs://`/`az://`/…, …). `uris` for mirrors. |
| `sha256` | Expected digest; auto-filled on first download, verified at fetch. |
| `format` | Format hint (`csv`, `nc`, `parquet`, `zip`, …) that picks a default loader; inferred from the URI when absent. |
| `extract` | After download, unpack the archive and use the extracted directory as the path. |
| `doi` | DOI of the dataset (also a lookup key). |
| `aliases` | Alternative names to look the dataset up by. |
| `version` | Dataset version; part of the storage key, so versions coexist on disk. |
| `requires` | Names of datasets to fetch first (a dependency graph, resolved in order). |
| `description` | Human-readable note (replaces TOML comments). |
| `storage_path` | Where the dataset lives on disk (overrides the default `$datasets_dir/$key`) — see [Storage](storage.md). |
| `skip_checksum` | Disable checksum verification. |
| `skip_download` | *Management* mode: a passive dependency you maintain yourself — not downloaded, not verified, never touched by maintenance (e.g. a large shared archive). |
| `lazy_access` | *Access* mode: open the `uri` in place via a loader (e.g. a remote object store) — no local copy, no checksum, no record; a loader is required. Mechanism (stream/mount) is implementation-defined. |
| `fetcher` / `loader` / `shell` | How to obtain/load it — see [Language bindings](bindings.md). |

```toml
# A DOI archive: downloaded, checksum-verified, then unpacked.
[herzschuh2023]
uri         = "https://doi.pangaea.de/10.1594/PANGAEA.930512?format=zip"
sha256      = "4e40e43ac0f1ddea125cb5314eee46e332aacbcb18aff7efbf59f1d8b1d84a13"
doi         = "10.1594/PANGAEA.930512"
format      = "zip"
extract     = true
description = "Pollen-based climate reconstructions (Herzschuh et al., 2023)"
```

A dataset key may contain a slash if quoted: `["jesstierney/lgmDA"]`.

*Normative: [SCHEMA.md §Language-agnostic contract](../schema.md#language-agnostic-contract-common-fields).*
