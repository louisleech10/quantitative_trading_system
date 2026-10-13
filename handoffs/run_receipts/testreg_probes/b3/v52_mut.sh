#!/bin/bash
# v52 驗收之 mutation：每個 mutant 拿掉／放寬試作一個分支 ⇒ 對應之 v52 新案須轉紅（列出該 mutant 下失敗之 v52 案）。
W=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/wt_v50
B=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/testreg_v52_backup.py
cd "$W" || exit 2
f=scripts/testreg.py
cp "$f" "$B"
run() {
  echo "== $1 =="
  venv/bin/python -m pytest -p no:cacheprovider -q tests/registry/test_testreg_repair_additive.py \
    -k "test_z or test_aa or test_ab or test_y" 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/^FAILED tests\/registry\/test_testreg_repair_additive.py::/FAILED /; s/ - .*//' | tail -12
  cp "$B" "$f"
}
mut() { # $1 標籤 $2 舊片段 $3 新片段
  OLD="$2" NEW="$3" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$f"
  if cmp -s "$f" "$B"; then echo "== $1 == anchor missing"; return; fi
  run "$1"
}
mut "M15 不讀模組 pytestmark 之參數化層（codex r50 P1-01）" '    for marks, scope_body, before in layers:' '    for marks, scope_body, before in layers[:-1]:'
mut "M16 pytest.param 元素視為不可列舉" '    return len(node.elts) if isinstance(node, (ast.List, ast.Tuple)) else None' '    return len(node.elts) if isinstance(node, (ast.List, ast.Tuple)) and not any(isinstance(e, ast.Call) for e in node.elts) else None'
mut "M17 基底解析不到改為略過（grok r50 P1-01）" '            if base is None:
                return None' '            if base is None:
                continue'
mut "M18 不掃類別本體 fixture（grok r50 P1-02）" '    if cchain:' '    if False:'
mut "M19 R 不遍歷 fixture（K4-1）" '    for f, node in _applied_fixtures(eng.tree, path, qual):' '    for f, node in []:'
mut "M20 目錄層 autouse 納入 R" '                    if au and f == path:' '                    if au:'
mut "M21 可見即套用" '        _usefixtures_in(marks) + sorted(auto)' '        _usefixtures_in(marks) + sorted(auto) + sorted(visible)'
mut "M22 情境綁定只看所改之檔" '            if not any(msyms & rt for _m, msyms, _s in killers):' '            if not any({f_ for f_, _n in msyms} & {f_ for f_, _n in rt} for _m, msyms, _s in killers):'
mut "M23 不比對 assert 條件" 'ast.dump(nx[1].test) != want' 'False'
mut "M24 assert 不必緊接" '                nx = seq[j + 1] if j + 1 < len(seq) else None' '                nx = next(((i_, x_) for i_, x_ in seq[j + 1:] if isinstance(x_, ast.Assert) and i_ == seq[j][0]), None)'
mut "M25 不檢條件之無副作用" '    if not all(isinstance(n, _SAFE_COND_NODES) for n in ast.walk(st.test)):' '    if False:'
mut "M26 不檢直接子敘述" '        if not leaf(x) and any(_is_exit_stmt(y) for y in ast.walk(x) if isinstance(y, ast.stmt)):' '        if False:'
mut "M27 不檢只在一側" '    if bool(in_body) == bool(in_else):' '    if not in_body and not in_else:'
mut "M28 不要求 assert 綁定" '            if want is not None:' '            if False:'
cmp -s "$f" "$B" && echo "restored to trial"
