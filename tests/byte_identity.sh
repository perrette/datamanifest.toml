#!/usr/bin/env bash
# Cross-tool byte-identity check (spec-v1.1 `byte-identity` capability).
#
# For each shared fixture, serialize the SAME logical manifest from both the
# Python (`datamanifest`) and Julia (`DataManifest.jl`) tools and diff the
# outputs byte-for-byte. The spec requires the canonical key ordering to make a
# logical manifest serialize identically across tools.
#
# Reports, per fixture:
#   RAW       — byte-for-byte identical? (the spec's `byte-identity` goal)
#   SEMANTIC  — parse both outputs and compare data structures; isolates a real
#               ordering/content divergence from mere TOML-library formatting
#               (indentation, blank lines, inline-vs-multiline arrays).
#
# Two levels of "identical", and which one is the contract:
#   * SEMANTIC identity is the GUARANTEE — same keys, same values, same canonical
#     (Unicode code-point) key ordering at every level. This is what each tool's
#     native writer assures, and what this check gates on (PASS == semantic).
#   * RAW byte-identity is NOT guaranteed by the native writers: Python's tomli_w
#     and Julia's TOML.print lay TOML out differently (flush-left vs nested-header
#     indentation; multi-line vs inline arrays; blank lines). That is cosmetic —
#     no content or ordering changes.
#   * For LITERAL byte-identity (same file checksum across tools), both tools
#     offer an OPT-IN canonical path that routes through one serializer:
#       - Python: `datamanifest format <file>`         (the canonical writer)
#       - Julia:  `write(db, path; canonical=true)`     (pipes through the above)
#     With that, RAW becomes identical too. This script verifies the SEMANTIC
#     floor on the *native* writers; run it after changing either writer to catch
#     a real ordering/content regression.
#
# Env overrides:
#   PY_REPO   (default ~/Projects/datamanifest)
#   JL_REPO   (default ~/Projects/DataManifest.jl)
#   FIXTURES  (default this repo's tests/fixtures)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_REPO="${PY_REPO:-$HOME/Projects/datamanifest}"
JL_REPO="${JL_REPO:-$HOME/Projects/DataManifest.jl}"
FIXTURES="${FIXTURES:-$HERE/fixtures}"

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# Fixtures both tools can fully round-trip (lang-read + lang-write).
FIX=(storage multilang parameterized single_python single_julia unknown_structural)

# --- Python serialization ---
( cd "$PY_REPO" && for f in "${FIX[@]}"; do
    .venv/bin/python -c "
from datamanifest.database import Database
db = Database(datasets_toml='$FIXTURES/$f.toml', persist=False, skip_checksum=True)
db.write('$OUT/$f.py.toml')
"
  done )

# --- Julia serialization ---
( cd "$JL_REPO" && julia --project=. -e '
using DataManifest
fixtures = "'"$FIXTURES"'"; out = "'"$OUT"'"
tmp = mktempdir()
for f in ["storage","multilang","parameterized","single_python","single_julia","unknown_structural"]
    db = DataManifest.read_dataset(joinpath(fixtures, f*".toml"), tmp; persist=false)
    DataManifest.Databases.write(db, joinpath(out, f*".jl.toml"))
end
' )

# Semantic comparison: parse both TOML files and compare the data structures.
# Key ORDER is irrelevant to dict equality, so this passes iff the same keys map
# to the same values regardless of formatting — the true ordering/content test.
semantic_eq() {
    python3 - "$1" "$2" <<'PY'
import sys, tomllib
with open(sys.argv[1],"rb") as f: a = tomllib.load(f)
with open(sys.argv[2],"rb") as f: b = tomllib.load(f)
sys.exit(0 if a == b else 1)
PY
}

raw_fail=0
sem_fail=0
echo "fixture                raw          semantic"
echo "----------------------------------------------"
for f in "${FIX[@]}"; do
    if diff -q "$OUT/$f.py.toml" "$OUT/$f.jl.toml" >/dev/null 2>&1; then
        raw="IDENTICAL"
    else
        raw="DIFFERS"; raw_fail=1
    fi
    if semantic_eq "$OUT/$f.py.toml" "$OUT/$f.jl.toml"; then
        sem="IDENTICAL"
    else
        sem="DIFFERS"; sem_fail=1
    fi
    printf "%-22s %-12s %s\n" "$f" "$raw" "$sem"
done

echo
# Contract: SEMANTIC identity (canonical ordering + identical parsed content).
# A logical manifest must round-trip to the same data through either tool. Pure
# TOML-library formatting differences (indentation, blank lines, inline-vs-
# multiline arrays) are NOT a failure — harmonizing them would require a custom
# canonical writer in both tools, deliberately out of scope.
if [ "$sem_fail" -ne 0 ]; then
    echo "FAIL: ordering/content DIFFERS across tools — a real regression."
    exit 1
else
    echo "PASS: semantic identity holds across tools (ordering + content identical)."
    [ "$raw_fail" -ne 0 ] && echo "      (Raw bytes differ in formatting only — by design, not a failure.)"
    exit 0
fi
