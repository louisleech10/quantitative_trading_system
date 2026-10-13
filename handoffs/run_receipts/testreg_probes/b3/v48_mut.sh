#!/usr/bin/env bash
# v48 新判定之 mutation 自證：逐一改壞 scripts/testreg.py、只跑 v48 新增案、還原
set -u
W="$1"; F="$W/scripts/testreg.py"; cp "$F" "$F.orig"
run() {
  local name="$1" old="$2" new="$3"
  cp "$F.orig" "$F"
  grep -qF -- "$old" "$F" || { echo "$name: needle missing"; return; }
  OLD="$old" NEW="$new" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$F"
  (cd "$W" && venv/bin/python -m pytest -q -p no:cacheprovider -k "test_o_ or test_p_whitelist or test_q_ or test_r_" \
     tests/registry/test_testreg_repair_additive.py > "$W/../mut48_$name.log" 2>&1)
  echo "$name rc=$? $(grep -E '[0-9]+ (passed|failed)' "$W/../mut48_$name.log" | tail -1)"
  grep -E '^FAILED' "$W/../mut48_$name.log" | sed 's/ - .*//; s#tests/registry/test_testreg_repair_additive.py::##'
}
run M1_detection_off 'if not any(blind(sm_) for _m, _f, sm_ in killers):' 'if False:'
run M2_star_off 'elif x.id not in mi.defs:  # v48' 'elif False:  # v48'
run M3_clash_off '                if clash:' '                if False:'
run M4_decorator_off 'all(isinstance(d, ast.Call) and _last_name(d.func) == "parametrize" for d in n.decorator_list)' 'True'
run M5_usefixtures_off 'info["auto"] + used, set()' 'info["auto"], set()'
run M6_base_unresolved '            if base is None:
                return None
            chain_.append(base)' '            return None'
run M7_keepdup_off ' or \
            opt.get("keepduplicates"):' ':'
cp "$F.orig" "$F"; rm -f "$F.orig"
