#!/usr/bin/env python3
"""Validate conformance fixtures for internal consistency.

Checks:
- Every dataset in resolution/preserve_verbatim exists in the manifest.
- Every _LANG.<lang> namespace referenced in expectations is present in the manifest.
- Rung names and ref values conform to the expected-outcome schema.
- All capability tags are drawn from SCHEMA.md's Conformance-levels table.

Uses only Python stdlib: tomllib, json, pathlib.
"""

import json
import pathlib
import sys
import tomllib

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# From SCHEMA.md §Conformance levels
KNOWN_CAPABILITIES = {"lang-read", "lang-write", "shell-fetch", "delegation"}

FETCH_RUNGS = {"own-fetcher", "shell", "delegation", "uri", "error"}
LOAD_RUNGS = {"per-dataset", "manifest-format-default", "built-in", "error"}

# Rungs that have no callable ref (must be null)
NULL_REF_FETCH_RUNGS = {"uri", "error"}
NULL_REF_LOAD_RUNGS = {"built-in", "error"}


def _err(errors, msg):
    errors.append(msg)


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
                    elif ref is not None and lang_ds["fetcher"] != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: ref mismatch (expected '{ref}', manifest has '{lang_ds['fetcher']}')")
                elif rung == "shell":
                    shell_ds = ds.get("_LANG", {}).get("shell", {})
                    if "fetcher" not in shell_ds:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: rung 'shell' but manifest has no [_LANG.shell].fetcher")
                    elif ref is not None and shell_ds["fetcher"] != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].fetcher: shell ref mismatch")
                elif rung == "per-dataset":
                    lang_ds = ds.get("_LANG", {}).get(lang, {})
                    if "loader" not in lang_ds:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: rung 'per-dataset' but manifest has no [_LANG.{lang}].loader")
                    elif ref is not None and lang_ds["loader"] != ref:
                        _err(errors, f"resolution[{lang}][{ds_name}].loader: ref mismatch (expected '{ref}', manifest has '{lang_ds['loader']}')")
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
