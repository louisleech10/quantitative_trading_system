#!/usr/bin/env bash
# 清掉 `data_cache/features/registry.json` 裡**檔案已不存在**的 run 條目。
#
# 為什麼需要（2026-08-29 實測）：19 筆裡有 **7 筆**指向不存在的檔——
#   ① 兩筆指向已刪除的 pytest 暫存目錄（`/private/var/.../pytest-of-louis/pytest-NNNN/…`）
#      ——`pytest tests/api` **會改寫本檔**（交接已登記之坑），測試用的臨時 run 就這樣留了下來；
#   ② 五筆之 `hdf5_relative_path` 為**空字串**，且慣例目錄 `features/<sym>/<tf>/<hash>/` 也不存在。
# 後果：使用者在 IC 分析頁的 run 選單看得到它們、選下去必失敗，而那不是產品缺陷。
#
# 🔴 **判準是「兩種定位方式都找不到」**，不是「路徑欄看起來怪」：
#    ①`hdf5_relative_path` 指到的東西存在，或 ②慣例目錄
#    `data_cache/features/<symbol>/<timeframe>/<config_hash>/` 存在
#    —— **任一成立即保留**。單看其中一個會誤刪（實測 `abc9b9fe` 兩者皆有）。
#
# 🔴 **本腳本只改 registry，絕不刪任何 `data_cache/` 底下的實際資料**。
#    找不到檔的條目才是刪除對象，而那些條目**本來就沒有對應的檔**。
#
# 用法：
#   bash scripts/prune_dead_feature_runs.sh --dry-run   # 只列出會刪什麼
#   bash scripts/prune_dead_feature_runs.sh             # 實際刪（自動備份）
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "PRUNE: 不在 git repo"; exit 2; }
cd "$ROOT" || exit 2

REG="data_cache/features/registry.json"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

[ -f "$REG" ] || { echo "PRUNE: ${REG} 不存在，無事可做"; exit 0; }
command -v jq >/dev/null 2>&1 || { echo "PRUNE: 需要 jq"; exit 2; }

before="$(jq 'length' "$REG")"
dead=""
alive_idx=""
i=0
while IFS=$'\t' read -r fc sym tf ch p; do
  conv="data_cache/features/${sym}/${tf}/${ch}"
  ok=0
  { [ -n "$p" ] && [ "$p" != "null" ] && [ -e "$p" ]; } && ok=1
  [ -d "$conv" ] && ok=1
  if [ "$ok" = "1" ]; then
    alive_idx="${alive_idx}${i} "
  else
    dead="${dead}  ${fc} ${sym} ${tf} ${ch}
"
  fi
  i=$((i + 1))
done < <(jq -r '.[] | [.feature_count, .symbol, .timeframe, .config_hash, (.hdf5_relative_path|tostring)] | @tsv' "$REG")

n_dead=$(printf '%s' "$dead" | grep -c . || true)
if [ "${n_dead}" = "0" ]; then
  echo "PRUNE ✅ ${REG} 之 ${before} 筆全部有檔，無須清理"
  exit 0
fi

echo "PRUNE: ${before} 筆中有 ${n_dead} 筆兩種定位方式都找不到檔："
printf '%s' "$dead"

if [ "$DRY" = "1" ]; then
  echo "PRUNE [dry-run] 未改動任何檔"
  exit 0
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
cp "$REG" "${REG}.bak-${stamp}" || { echo "PRUNE ❌ 備份失敗，中止"; exit 2; }

# 保留 alive 的索引；`jq` 之 `IN` 對 bash 3.2 友善的作法＝把索引串成陣列字面
idx_json="[$(printf '%s' "$alive_idx" | tr ' ' ',' | sed 's/,$//')]"
tmp="${REG}.tmp.$$"
jq --argjson keep "$idx_json" '[ to_entries[] | select(.key as $k | $keep | index($k)) | .value ]' \
  "$REG" > "$tmp" || { echo "PRUNE ❌ jq 失敗，registry 未改動"; rm -f "$tmp"; exit 2; }

after="$(jq 'length' "$tmp")"
expected=$((before - n_dead))
if [ "$after" != "$expected" ]; then
  echo "PRUNE ❌ 筆數不符（期望 ${expected}、實得 ${after}）—— registry 未改動"
  rm -f "$tmp"
  exit 2
fi

mv "$tmp" "$REG"
echo "PRUNE ✅ ${before} → ${after} 筆（清掉 ${n_dead} 筆死條目）；備份 ${REG}.bak-${stamp}"
exit 0
