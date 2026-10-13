#!/usr/bin/env bash
# raises 端到端案之 mutation 自證：逐一改壞 testreg.py 判定、只跑 raises 三案、還原
set -u
W="$1"; F="$W/scripts/testreg.py"; cp "$F" "$F.orig"
run() {
  local name="$1" old="$2" new="$3"
  cp "$F.orig" "$F"
  grep -qF -- "$old" "$F" || { echo "$name: needle missing"; return; }
  OLD="$old" NEW="$new" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$F"
  (cd "$W" && venv/bin/python -m pytest -p no:cacheprovider -q -k "test_raises_" tests/registry/test_testreg_defective_rewrite.py > "$W/../mut_$name.log" 2>&1)
  echo "$name rc=$? $(grep -E '[0-9]+ (passed|failed)' "$W/../mut_$name.log" | tail -1)"
  grep -E '^FAILED' "$W/../mut_$name.log" | sed 's/ - .*//'
}
run M1_raises_branch_off 'if kw.arg == "match" and _pure_literal(kw.value):' 'if False:'
run M2_allowed_ignored 'return id(a) in allowed, 1' 'return True, 1'
run M3_nonconst_diff_ignored '            elif x != y:
                return False, 0' '            elif False:
                return False, 0'
cp "$F.orig" "$F"; rm -f "$F.orig"
