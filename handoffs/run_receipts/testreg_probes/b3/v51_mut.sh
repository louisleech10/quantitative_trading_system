#!/bin/bash
# v51 驗收 (u)(v)(w)(x) 之 mutation：每個單行 mutant 拿掉 resolver 一個分支 ⇒ 對應驗收須轉紅（(s)(t) 對照）。
W=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/wt_v50
B=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/testreg_v51_backup.py
cd "$W" || exit 2
f=scripts/testreg.py
cp "$f" "$B"
run() {
  echo "== $1 =="
  venv/bin/python -m pytest -p no:cacheprovider -q tests/registry/test_testreg_repair_additive.py \
    -k "test_s_ or test_t_ or test_u_ or test_v_ or test_w_ or test_x_" 2>&1 | grep -E "^(PASSED|FAILED)|::test_[stuvwx]_.*(PASSED|FAILED)|passed|failed" | sed 's/^tests\/registry\/test_testreg_repair_additive.py:://' | tail -8
  cp "$B" "$f"
}
mut() { # $1 標籤 $2 舊片段 $3 新片段
  OLD="$2" NEW="$3" perl -0pi -e 's/\Q$ENV{OLD}\E/$ENV{NEW}/' "$f"
  if cmp -s "$f" "$B"; then echo "== $1 == anchor missing"; return; fi
  run "$1"
}
mut "M10 不展開 autouse 遞移依賴" 'todo += deps.get(name, [])' 'todo += []'
mut "M11 不讀類別裝飾器層" 'layers += [(c.decorator_list, mod.body, c.lineno), (_pytestmark_values(c.body), mod.body, c.lineno)]' 'layers += [(_pytestmark_values(c.body), mod.body, c.lineno)]'
mut "M12 不讀類別 pytestmark 層" 'layers += [(c.decorator_list, mod.body, c.lineno), (_pytestmark_values(c.body), mod.body, c.lineno)]' 'layers += [(c.decorator_list, mod.body, c.lineno)]'
mut "M13 不讀模組 pytestmark 層" 'layers.append((_pytestmark_values(mod.body), mod.body, fn.lineno))' 'pass'
mut "M14 usefixtures 只取函式裝飾器層" 'used = _usefixtures_in([m for marks, _b, _l in layers for m in marks])' 'used = _usefixtures_in(list(layers[0][0]))'
cmp -s "$f" "$B" && echo "restored to trial"
