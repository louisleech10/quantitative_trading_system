#!/usr/bin/env bash
# v49 外掛 fixture 掃描之 mutation 自證（拿掉外掛模組掃描 ⇒ test_s 轉紅）
set -u
W="$1"; F="$W/scripts/testreg.py"; cp "$F" "$F.orig"
OLD='            ordered += [pp for pp in _plugin_paths(tree, f) if pp not in ordered]'
NEW='            pass'
grep -qF -- "$OLD" "$F" || { echo "needle missing"; exit 1; }
OLD="$OLD" NEW="$NEW" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$F"
(cd "$W" && venv/bin/python -m pytest -q -p no:cacheprovider -k "test_s_" tests/registry/test_testreg_repair_additive.py > "$W/../mut49.log" 2>&1)
echo "M8_plugin_scan_off rc=$? $(grep -E '[0-9]+ (passed|failed)' "$W/../mut49.log" | tail -1)"
cp "$F.orig" "$F"; rm -f "$F.orig"
