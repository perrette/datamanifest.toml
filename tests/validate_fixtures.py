#!/usr/bin/env python3
"""Validate conformance fixtures for internal consistency.

Checks:
- Every dataset in resolution/preserve_verbatim exists in the manifest.
- Every _LANG.<lang> namespace referenced in expectations is present in the manifest.
- Rung names and ref values conform to the expected-outcome schema.
- All capability tags are drawn from SCHEMA.md's Conformance-levels table.

Uses only Python stdlib: tomllib, json, pathlib.
"""

import hashlib
import json
import pathlib
import re
import sys
import tomllib

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# From SCHEMA.md §Conformance levels
KNOWN_CAPABILITIES = {
    "lang-read", "lang-write", "shell-fetch", "delegation",
    "storage", "byte-identity", "binding-args",
    "cache-produce", "inspect", "sync",
}

# Reserved keys under [_STORAGE] that are not folder-variable definitions.
# Reserved bare keys under [_STORAGE] (the two folder fields + the host sub-table); every
# other bare key is a user-defined symbol. Predefined $-symbols are not defined in [_STORAGE].
STORAGE_RESERVED = {"datasets_dir", "datacache_dir", "_HOST"}
PREDEFINED_SYMBOLS = {"user_data_dir", "user_cache_dir", "repo"}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(obj):
    """JCS-style canonical JSON: sorted keys, no insignificant whitespace,
    UTF-8 with minimal escaping. The normative hash input (SCHEMA.md spec-v2)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _param_hash(key_table):
    return hashlib.sha256(_canonical_json(key_table).encode("utf-8")).hexdigest()

FETCH_RUNGS = {"own-fetcher", "shell", "delegation", "uri", "error"}
LOAD_RUNGS = {"per-dataset", "manifest-format-default", "built-in", "error"}

# Rungs that have no callable ref (must be null)
NULL_REF_FETCH_RUNGS = {"uri", "error"}
NULL_REF_LOAD_RUNGS = {"built-in", "error"}


def _err(errors, msg):
    errors.append(msg)


def _ref_of(binding):
    """A binding is either a bare `module:function` string or a `{ ref, args }`
    table (parameterized binding). Return its `module:function` ref either way."""
    if isinstance(binding, dict):
        return binding.get("ref")
    return binding


def validate(toml_path, json_path):
    with open(toml_path, "rb") as f:
        manifest = tomllib.load(f)

    with open(json_path) as f:
        expected = json.load(f)

    errors = []

    # --- top-level structure ---
    for key in ("capabilities", "resolution", "preserve_verbatim"):
        if key not in expected:
            _err(errors, f"missing top-level key '{key}'")

    if errors:
        raise AssertionError("; ".join(errors))

    caps = expected["capabilities"]
    if not isinstance(caps, list):
        _err(errors, "'capabilities' must be a list")
    else:
        for cap in caps:
            if cap not in KNOWN_CAPABILITIES:
                _err(errors, f"unknown capability '{cap}' (known: {sorted(KNOWN_CAPABILITIES)})")

    # --- resolution ---
    resolution = expected.get("resolution", {})
    for lang, datasets in resolution.items():
        for ds_name, outcome in datasets.items():
            if ds_name not in manifest:
                _err(errors, f"resolution[{lang}][{ds_name}]: dataset not in manifest")
                continue

            ds = manifest[ds_name]

            for role, known_rungs, null_rungs in (
                ("fetcher", FETCH_RUNGS, NULL_REF_FETCH_RUNGS),
                ("loader", LOAD_RUNGS, NULL_REF_LOAD_RUNGS),
            ):
                if role not in outcome:
                    _err(errors, f"resolution[{lang}][{ds_name}]: missing '{role}'")
                    continue
                entry = outcome[role]
                if not isinstance(entry, dict) or "rung" not in entry or "ref" not in entry:
                    _err(errors, f"resolution[{lang}][{ds_name}].{role}: must have 'rung' and 'ref'")
                    continue
                rung = entry["rung"]
                ref = entry["ref"]

                if rung not in known_rungs:
                    _err(errors, f"resolution[{lang}][{ds_name}].{role}: unknown rung '{rung}'")
                    continue

                if rung in null_rungs and ref is not None:
                    _err(errors, f"resolution[{lang}][{ds_name}].{role}: rung '{rung}' requires ref=null")

                # Verify the manifest actually carries the binding the rung claims
                if rung == "own-fetcher":
                    lang_ds = ds.get("_LANG", {}).get(lang, {})
                    # explicit [_LANG.<lang>].fetcher wins; else the bare
                    # (language-implicit) ds.fetcher
                    binding = lang_ds.get("fetcher", ds.get("fetcher"))
                    if binding is None:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: rung 'own-fetcher' but manifest has no [_LANG.{lang}].fetcher nor a bare fetcher")
                    elif ref is not None and _ref_of(binding) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: ref mismatch (expected '{ref}', manifest has '{_ref_of(binding)}')")
                elif rung == "shell":
                    # canonical bare `shell` field; else legacy [_LANG.shell].fetcher
                    cmd = ds.get("shell", ds.get("_LANG", {}).get("shell", {}).get("fetcher"))
                    if cmd is None:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: rung 'shell' but manifest has no bare 'shell' nor [_LANG.shell].fetcher")
                    elif ref is not None and _ref_of(cmd) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: shell ref mismatch")
                elif rung == "per-dataset":
                    lang_ds = ds.get("_LANG", {}).get(lang, {})
                    # explicit [_LANG.<lang>].loader wins; else the bare
                    # (language-implicit) ds.loader
                    binding = lang_ds.get("loader", ds.get("loader"))
                    if binding is None:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'per-dataset' but manifest has no [_LANG.{lang}].loader nor a bare loader")
                    elif ref is not None and _ref_of(binding) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: ref mismatch (expected '{ref}', manifest has '{_ref_of(binding)}')")
                elif rung == "manifest-format-default":
                    # [_LANG.<lang>.loaders] overrides the bare [_LOADERS] map
                    effective = {
                        **manifest.get("_LOADERS", {}),
                        **manifest.get("_LANG", {}).get(lang, {}).get("loaders", {}),
                    }
                    fmt = ds.get("format")
                    if fmt is None:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'manifest-format-default' but dataset has no 'format'")
                    elif fmt not in effective:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'manifest-format-default' but neither [_LANG.{lang}.loaders] nor [_LOADERS] has '{fmt}'")
                    elif ref is not None and _ref_of(effective[fmt]) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: manifest-format-default ref mismatch (expected '{ref}', manifest has '{_ref_of(effective[fmt])}')")

    # --- preserve_verbatim ---
    pv = expected.get("preserve_verbatim", {})
    for key in ("unknown_structural", "lang_namespaces"):
        if key not in pv:
            _err(errors, f"preserve_verbatim: missing key '{key}'")

    if "unknown_structural" in pv:
        for key in pv["unknown_structural"]:
            if key not in manifest:
                _err(errors, f"preserve_verbatim.unknown_structural: '{key}' not in manifest")

    ln = pv.get("lang_namespaces", {})
    for key in ("top_level", "per_dataset"):
        if key not in ln:
            _err(errors, f"preserve_verbatim.lang_namespaces: missing key '{key}'")

    if "top_level" in ln:
        for entry in ln["top_level"]:
            if not entry.startswith("_LANG."):
                _err(errors, f"preserve_verbatim.lang_namespaces.top_level: '{entry}' must start with '_LANG.'")
                continue
            lang = entry[len("_LANG."):]
            if lang not in manifest.get("_LANG", {}):
                _err(errors, f"preserve_verbatim.lang_namespaces.top_level: '{entry}' not in manifest top-level _LANG")

    if "per_dataset" in ln:
        for ds_name, keys in ln["per_dataset"].items():
            if ds_name not in manifest:
                _err(errors, f"preserve_verbatim.lang_namespaces.per_dataset: dataset '{ds_name}' not in manifest")
                continue
            ds_lang = manifest[ds_name].get("_LANG", {})
            for entry in keys:
                if not entry.startswith("_LANG."):
                    _err(errors, f"preserve_verbatim.lang_namespaces.per_dataset.{ds_name}: '{entry}' must start with '_LANG.'")
                    continue
                lang = entry[len("_LANG."):]
                if lang not in ds_lang:
                    _err(errors, f"preserve_verbatim.lang_namespaces.per_dataset.{ds_name}: '{entry}' not in manifest")

    # --- storage (optional; present for `storage`-capability fixtures) ---
    # spec-v2 folder model: `store`/`default` are $-folder *selectors*; [_STORAGE]
    # is a namespace of folder variables (built-in data/cache/repo + user-defined)
    # plus the reserved `default` selector and _HOST/_PROFILE override sub-tables.
    storage = expected.get("storage")
    if storage is not None:
        st = manifest.get("_STORAGE", {})
        # the two folder fields
        for field in ("datasets_dir", "datacache_dir"):
            if field in storage and st.get(field) != storage[field]:
                _err(errors, f"storage.{field}: expected {storage[field]!r}, [_STORAGE] has {st.get(field)!r}")
        # user-defined symbols MUST be defined in [_STORAGE], and not reserved/predefined
        for name in storage.get("symbols", []):
            if name in STORAGE_RESERVED or name in PREDEFINED_SYMBOLS:
                _err(errors, f"storage.symbols: '{name}' is reserved/predefined, not a user symbol")
            elif name not in st:
                _err(errors, f"storage.symbols: '{name}' not defined in [_STORAGE]")
        # _HOST host-override patterns present
        host = st.get("_HOST", {})
        for pat in storage.get("host_patterns", []):
            if pat not in host:
                _err(errors, f"storage.host_patterns: '{pat}' not in [_STORAGE._HOST]")
        # per-dataset `local_path` overrides (default is $datasets_dir/$key; $key present =>
        # keyed/managed, exact path => user-managed). Compared exactly.
        for ds_name, lp in storage.get("local_paths", {}).items():
            if ds_name not in manifest:
                _err(errors, f"storage.local_paths: '{ds_name}' not in manifest")
                continue
            actual = manifest[ds_name].get("local_path")
            if actual != lp:
                _err(errors, f"storage.local_paths[{ds_name}]: expected {lp!r}, manifest has {actual!r}")

    # --- binding_args (optional; present for `binding-args`-capability fixtures) ---
    binding_args = expected.get("binding_args")
    if binding_args is not None:
        for lang, datasets in binding_args.items():
            for ds_name, roles in datasets.items():
                if ds_name not in manifest:
                    _err(errors, f"binding_args[{lang}]: '{ds_name}' not in manifest")
                    continue
                lang_ds = manifest[ds_name].get("_LANG", {}).get(lang, {})
                for role, exp in roles.items():
                    binding = lang_ds.get(role)
                    if not isinstance(binding, dict):
                        _err(errors, f"binding_args[{lang}][{ds_name}].{role}: manifest binding is not a `{{ ref, args, kwargs }}` table")
                        continue
                    if "args" in exp and binding.get("args", []) != exp["args"]:
                        _err(errors, f"binding_args[{lang}][{ds_name}].{role}: args mismatch (expected {exp['args']}, manifest has {binding.get('args')})")
                    if "kwargs" in exp and binding.get("kwargs", {}) != exp["kwargs"]:
                        _err(errors, f"binding_args[{lang}][{ds_name}].{role}: kwargs mismatch (expected {exp['kwargs']}, manifest has {binding.get('kwargs')})")

    # --- config_sidecar (optional; present for `cache-produce` fixtures) ---
    # The fixture .toml is itself a `config.toml` cache sidecar — NOT a datasets.toml.
    # Produced datasets are never declared in datasets.toml; this self-describing
    # sidecar is their on-disk record. `_META` carries `cachetype` + `hash`; every
    # other top-level key is part of the re-hashable key table. A `cache-produce` tool
    # recomputes the param hash from that key table and MUST find it equals `_META.hash`.
    config_sidecar = expected.get("config_sidecar")
    if config_sidecar is not None:
        meta = manifest.get("_META", {})
        # the key table is the sidecar minus its _META block
        manifest_kt = {k: v for k, v in manifest.items() if k != "_META"}
        exp_kt = config_sidecar.get("key_table", {})
        if manifest_kt != exp_kt:
            _err(errors, f"config_sidecar: key_table mismatch (expected {exp_kt}, sidecar has {manifest_kt})")
        if meta.get("cachetype", "") != config_sidecar.get("cachetype", ""):
            _err(errors, f"config_sidecar: cachetype mismatch (expected {config_sidecar.get('cachetype')!r}, _META has {meta.get('cachetype')!r})")
        # param hash = SHA-256 of canonical JSON of the key table (normative)
        computed = _param_hash(exp_kt)
        if config_sidecar.get("param_hash") != computed:
            _err(errors, f"config_sidecar: param_hash mismatch (expected {config_sidecar.get('param_hash')}, canonical-JSON SHA-256 is {computed})")
        # the sidecar's recorded hash MUST match the recomputed hash (re-hashable)
        if meta.get("hash") != computed:
            _err(errors, f"config_sidecar: _META.hash {meta.get('hash')!r} != recomputed {computed}")
        if not _HEX64.match(str(meta.get("hash", ""))):
            _err(errors, "config_sidecar: _META.hash is not 64 lowercase hex chars")
        ct = config_sidecar.get("cachetype")
        if "key" in config_sidecar and config_sidecar["key"] != f"{ct}/{computed}":
            _err(errors, f"config_sidecar: key mismatch (expected {config_sidecar['key']}, derived {ct}/{computed})")

    # --- cached_index (optional; present for `inspect` fixtures) ---
    # Schema 2 (nested): a top-level `produced` array of recipe tables keyed by
    # (scope, cachetype, version), each with `instances` recording a variation's
    # `hash` + `params`. The fixture is self-verifying — every instance hash MUST
    # equal the canonical-JSON param-hash of its `params`.
    cached_index = expected.get("cached_index")
    if cached_index is not None:
        cached_meta = manifest.get("_META", {})
        exp_schema = cached_index.get("schema", 2)
        if cached_meta.get("schema") != exp_schema:
            _err(errors, f"cached_index: _META.schema is {cached_meta.get('schema')!r}, expected {exp_schema!r}")

        # `forbidden_keys` is the canonical *writer* contract: a generated
        # cached.toml must NOT carry these legacy/renamed keys (e.g. `project`,
        # renamed to `scope`), in `_META` or any recipe. Deliberately distinct
        # from the lenient round-trip preservation of unknown keys (R3/R4):
        # preservation governs foreign input copied verbatim; this governs what a
        # tool *emits*. Without it, `additionalProperties: true` (and the bespoke
        # positive-only checks here) would silently accept a stray `project`.
        forbidden = cached_index.get("forbidden_keys", [])
        for bad in forbidden:
            if bad in cached_meta:
                _err(errors, f"cached_index[_META]: canonical output must not carry legacy key '{bad}'")

        produced = manifest.get("produced", [])
        if not isinstance(produced, list):
            _err(errors, "cached_index: top-level 'produced' must be an array of recipe tables")
            produced = []
        by_id = {
            (r.get("cachetype"), r.get("version", "")): r
            for r in produced if isinstance(r, dict)
        }
        for exp_r in cached_index.get("recipes", []):
            rid = (exp_r.get("cachetype"), exp_r.get("version", ""))
            r = by_id.get(rid)
            if r is None:
                _err(errors, f"cached_index: recipe {rid} not in manifest 'produced'")
                continue
            for field in ("cachetype", "version", "ref", "format"):
                if field in exp_r and r.get(field) != exp_r[field]:
                    _err(errors, f"cached_index{rid}: {field} mismatch (expected {exp_r[field]!r}, manifest has {r.get(field)!r})")
            for bad in forbidden:
                if bad in r:
                    _err(errors, f"cached_index{rid}: canonical output must not carry legacy key '{bad}' (renamed to 'scope')")
            inst_by_hash = {
                i.get("hash"): i for i in r.get("instances", []) if isinstance(i, dict)
            }
            for exp_i in exp_r.get("instances", []):
                h = exp_i.get("hash")
                inst = inst_by_hash.get(h)
                if inst is None:
                    _err(errors, f"cached_index{rid}: instance hash {h!r} not in manifest recipe")
                    continue
                if not _HEX64.match(str(h)):
                    _err(errors, f"cached_index{rid}: hash {h!r} is not 64 lowercase hex chars")
                params = inst.get("params", {})
                computed = _param_hash(params)
                if computed != h:
                    _err(errors, f"cached_index{rid}: hash {h} != recomputed param-hash {computed} of params {params!r}")
                if "params" in exp_i and params != exp_i["params"]:
                    _err(errors, f"cached_index{rid}: instance {h} params mismatch (expected {exp_i['params']!r}, manifest has {params!r})")

    if errors:
        raise AssertionError("\n  " + "\n  ".join(errors))

    return caps


def main():
    toml_files = sorted(FIXTURES.glob("*.toml"))
    if not toml_files:
        print("No fixtures found.", file=sys.stderr)
        return 1

    failed = 0
    for toml_path in toml_files:
        json_path = toml_path.with_suffix(".expected.json")
        name = toml_path.stem
        if not json_path.exists():
            print(f"MISSING  {name}: {json_path.name} not found")
            failed += 1
            continue
        try:
            caps = validate(toml_path, json_path)
            print(f"OK  {name}  [{', '.join(caps)}]")
        except AssertionError as exc:
            print(f"FAIL {name}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR {name}: {exc}")
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
