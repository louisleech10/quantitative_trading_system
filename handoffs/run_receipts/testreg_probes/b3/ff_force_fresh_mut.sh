#!/usr/bin/env bash
# CODEX-R7-P1-01 查證：拿掉 `and not force_fresh` 後 test_cgsa_force_fresh_skips_existing_manifest 是否轉紅（暫存樹內、跑完還原）
set -u
W="$1"; OUT="$2"
F="$W/momentum/FeatureEngineering/feature_factory.py"
cp "$F" "$F.orig"
OLD='resume_allowed = manifest_path.exists() and not force_fresh'
NEW='resume_allowed = manifest_path.exists()'
grep -cF "$OLD" "$F"
OLD="$OLD" NEW="$NEW" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$F"
grep -cF "$OLD" "$F"
NID='tests/test_cgsa_resume.py::test_cgsa_force_fresh_skips_existing_manifest'
(cd "$W" && NUMBA_CACHE_DIR="$(mktemp -d)" venv/bin/python -m pytest -q -p no:testreg_recorder -p no:cacheprovider "$NID" > "$OUT" 2>&1)
echo "mutant_rc=$?"
tail -2 "$OUT"
cp "$F.orig" "$F"; rm -f "$F.orig"
(cd "$W" && NUMBA_CACHE_DIR="$(mktemp -d)" venv/bin/python -m pytest -q -p no:testreg_recorder -p no:cacheprovider "$NID" > "$OUT.base" 2>&1)
echo "baseline_rc=$?"
git -C "$W" diff --stat -- momentum
