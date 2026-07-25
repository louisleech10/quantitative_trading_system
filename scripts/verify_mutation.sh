#!/usr/bin/env bash
# verify_mutation.sh — 一鍵驗證「守衛測試是真 oracle」:改壞→須轉紅→**保證還原**→須轉綠。
#
# 為何存在(2026-07-25):我這 session 手做了 5+ 次「python 改檔 → pytest → git checkout 還原」,
#   步驟散、且**還原漏做就髒工作區**(Grok 同輪就踩過 git checkout 意外)。
#   本腳本用 trap 保證無論中途成功/失敗/被中斷都還原。
#
# 用法:
#   bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>
# 例:
#   bash scripts/verify_mutation.sh scripts/verify_task_provenance.py \
#     'return (' 'return (0,) if False else (' tests/governance/test_stamp_no_task_rejected.py
#
# 通過條件(兩者都要,缺一即 rc≠0):①變異後測試**轉紅** ②還原後測試**轉綠**
#   ——只紅不綠=測試本身壞;只綠不紅=測試假綠(抓不到該抓的)。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

file="${1:-}"; old="${2:-}"; new="${3:-}"; target="${4:-}"
[ -n "${file}" ] && [ -n "${old}" ] && [ -n "${new}" ] && [ -n "${target}" ] || {
  echo "用法: bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>" >&2; exit 2; }
[ -f "${file}" ] || { echo "ERROR: 檔不存在: ${file}" >&2; exit 2; }

py="venv/bin/python"; [ -x "${py}" ] || py="$(command -v python3 || command -v python)"
[ -n "${py}" ] || { echo "ERROR: 找不到 python" >&2; exit 2; }

bak="$(mktemp -t vmut)" || exit 2
cp "${file}" "${bak}"
# 保證還原(成功/失敗/中斷皆然)
trap 'cp "${bak}" "${file}"; rm -f "${bak}"; echo "[verify_mutation] 已還原 ${file}"' EXIT INT TERM

# --- 套用變異(字面替換一次;找不到即 fail,不靜默略過) ---
"${py}" - "${file}" "${old}" "${new}" <<'PY' || exit 2
import sys
from pathlib import Path
p, old, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
s = p.read_text(encoding="utf-8")
if old not in s:
    sys.stderr.write("ERROR: 檔內找不到要變異的字串(結構已改?):\n  %r\n" % old); sys.exit(2)
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("[verify_mutation] 已套用變異(替換 1 處)")
PY

echo "[verify_mutation] === 變異後跑 ${target}(期望:轉紅) ==="
if "${py}" -m pytest "${target}" -q --tb=line >/dev/null 2>&1; then
  echo "[verify_mutation] ❌ 變異後測試仍**綠** → 這測試抓不到該抓的(假綠/弱 oracle)" >&2
  exit 1
fi
echo "[verify_mutation] ✓ 變異後轉紅(正確)"

# 還原(trap 也會做;這裡先做以便跑第二次)
cp "${bak}" "${file}"
echo "[verify_mutation] === 還原後跑 ${target}(期望:轉綠) ==="
if ! "${py}" -m pytest "${target}" -q --tb=line >/dev/null 2>&1; then
  echo "[verify_mutation] ❌ 還原後仍紅 → 測試本身有問題(或還原不完整)" >&2
  exit 1
fi
echo "[verify_mutation] ✅ 通過:變異→紅、還原→綠(此守衛是真 oracle)"
exit 0
