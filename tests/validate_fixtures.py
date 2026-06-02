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
    "cache-produce", "cache-gc",
}

# Reserved keys under [_STORAGE] that are not folder-variable definitions.
STORAGE_RESERVED = {"default", "_HOST", "_PROFILE"}
BUILTIN_FOLDERS = {"data", "cache", "repo"}

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
                    if "fetcher" not in lang_ds:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: rung 'own-fetcher' but manifest has no [_LANG.{lang}].fetcher")
                    elif ref is not None and _ref_of(lang_ds["fetcher"]) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: ref mismatch (expected '{ref}', manifest has '{_ref_of(lang_ds['fetcher'])}')")
                elif rung == "shell":
                    shell_ds = ds.get("_LANG", {}).get("shell", {})
                    if "fetcher" not in shell_ds:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: rung 'shell' but manifest has no [_LANG.shell].fetcher")
                    elif ref is not None and _ref_of(shell_ds["fetcher"]) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: shell ref mismatch")
                elif rung == "per-dataset":
                    lang_ds = ds.get("_LANG", {}).get(lang, {})
                    if "loader" not in lang_ds:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'per-dataset' but manifest has no [_LANG.{lang}].loader")
                    elif ref is not None and _ref_of(lang_ds["loader"]) != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: ref mismatch (expected '{ref}', manifest has '{_ref_of(lang_ds['loader'])}')")
                elif rung == "manifest-format-default":
                    top_loaders = manifest.get("_LANG", {}).get(lang, {}).get("loaders", {})
                    fmt = ds.get("format")
                    if fmt is None:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'manifest-format-default' but dataset has no 'format'")
                    elif fmt not in top_loaders:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'manifest-format-default' but [_LANG.{lang}.loaders] has no '{fmt}' entry")
                    elif ref is not None and top_loaders[fmt] != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: manifest-format-default ref mismatch (expected '{ref}', manifest has '{top_loaders[fmt]}')")

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
        # `default` selector ($-form), itself defaulting to "$data"
        default_sel = storage.get("default", "$data")
        manifest_default = st.get("default", "$data")
        if manifest_default != default_sel:
            _err(errors, f"storage.default: expected '{default_sel}', [_STORAGE] has '{manifest_default}'")
        # selectors MUST be $-references (hard migration — no bare legacy names)
        for ds_name, sel in storage.get("datasets", {}).items():
            if ds_name not in manifest:
                _err(errors, f"storage.datasets: '{ds_name}' not in manifest")
                continue
            if not sel.startswith("$"):
                _err(errors, f"storage.datasets[{ds_name}]: selector '{sel}' must be a $-reference")
            actual = manifest[ds_name].get("store", default_sel)
            if isinstance(actual, str) and actual and not actual.startswith("$"):
                _err(errors, f"storage.datasets[{ds_name}]: manifest store '{actual}' is a bare name (spec-v1.1 form); must be $-form")
            if actual != sel:
                _err(errors, f"storage.datasets[{ds_name}]: expected selector '{sel}', manifest has '{actual}'")
        # local_path datasets (bypass the keyed layout)
        for ds_name, lp in storage.get("local_paths", {}).items():
            if ds_name not in manifest:
                _err(errors, f"storage.local_paths: '{ds_name}' not in manifest")
                continue
            actual = manifest[ds_name].get("local_path")
            if actual != lp:
                _err(errors, f"storage.local_paths[{ds_name}]: expected '{lp}', manifest has '{actual!r}'")
        # folder-variable namespace
        folders = storage.get("folders", {})
        for name in folders.get("builtin", []):
            if name not in BUILTIN_FOLDERS:
                _err(errors, f"storage.folders.builtin: '{name}' is not a built-in folder {sorted(BUILTIN_FOLDERS)}")
        for name in folders.get("user", []):
            if name in STORAGE_RESERVED or name in BUILTIN_FOLDERS:
                _err(errors, f"storage.folders.user: '{name}' is reserved or built-in, not a user folder")
            elif name not in st:
                _err(errors, f"storage.folders.user: '{name}' not defined in [_STORAGE]")
        host = st.get("_HOST", {})
        for pat in folders.get("host_patterns", []):
            if pat not in host:
                _err(errors, f"storage.folders.host_patterns: '{pat}' not in [_STORAGE._HOST]")
        prof = st.get("_PROFILE", {})
        for name in folders.get("profiles", []):
            if name not in prof:
                _err(errors, f"storage.folders.profiles: '{name}' not in [_STORAGE._PROFILE]")

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

    # --- cached_index (optional; present for `cache-gc` fixtures) ---
    cached_index = expected.get("cached_index")
    if cached_index is not None:
        for name, exp in cached_index.get("entries", {}).items():
            if name not in manifest:
                _err(errors, f"cached_index: entry '{name}' not in manifest")
                continue
            entry = manifest[name]
            for field in ("cachetype", "hash", "ref"):
                if field in exp and entry.get(field) != exp[field]:
                    _err(errors, f"cached_index[{name}]: {field} mismatch (expected {exp[field]!r}, manifest has {entry.get(field)!r})")
            if "store" in exp and entry.get("store", "$cache") != exp["store"]:
                _err(errors, f"cached_index[{name}]: store mismatch (expected {exp['store']!r}, manifest has {entry.get('store')!r})")
            if not _HEX64.match(str(entry.get("hash", ""))):
                _err(errors, f"cached_index[{name}]: hash is not 64 lowercase hex chars")

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
