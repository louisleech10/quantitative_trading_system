#!/usr/bin/env bash
# measure_ic_footprint.sh — GAP-3 UX Task 6.2：IC 分析之記憶體量測協定（**可重跑**）。
#
# 為何存在：Task 6.1 之特徵數上限**禁拍腦袋填**。上限必須由實跑量測導出，
#   且量測本身要可被別人重跑得到相近結果，否則那個數字沒有意義。
#
# 🔴 量測工具**固定**為 macOS `sample <pid>` 之 **Physical footprint**，**禁用 `ps rss`**：
#   macOS 的壓縮頁面會讓 RSS 嚴重失真——UAT 實測同一時刻 RSS 96–400MB 而 footprint 7.1GB。
#   receipt 內 `tool` 欄固定寫 `sample:Physical footprint`，Task 6.2 驗收④會斷言它不是 ps rss。
#
# 每個量測點記**六欄**（缺任一即 fail-closed，不產出半套 receipt）：
#   ① machine（機型＋RAM 總量）② pid（單一，不得混進程）③ baseline_footprint_bytes（發請求前）
#   ④ peak_footprint_bytes（採樣至任務結束或被 kill）⑤ sampling（間隔與總時長）⑥ feature_count
#
# 用法：
#   bash scripts/measure_ic_footprint.sh --config-hash <hash> --feature-count <n> \
#        --symbol <SYM> --timeframe <TF> --out handoffs/run_receipts/<name>.json \
#        [--interval-sec 2] [--max-sec 900] [--api http://127.0.0.1:8000]
#
# 🔴 **先決條件**：後端須已在跑（`source venv/bin/activate && python run_api.py`），
#   且**只有一個** `run_api.py` 進程——多個進程時本腳本 fail-closed 拒測（量到誰的都不算數）。
#
# 🔴 **這支腳本會把機器推到實體記憶體上限**：UAT 量到 218,369 特徵之 footprint 為 7.1GB。
#   在 RAM 較小的機器上跑大 run 會重度 swap 甚至失去回應。**請在你在場時跑。**
#
# receipt 為**累積**格式：同一個 --out 反覆呼叫會把新的量測點 append 進 `points`，
# 因為 Task 6.2 要求 ≥3 個量測點，而它們本來就該分次跑（每次一個 run）。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

TOOL_LITERAL="sample:Physical footprint"

config_hash=""; feature_count=""; symbol=""; timeframe=""; out=""
interval_sec="2"; max_sec="900"; api="http://127.0.0.1:8000"
# 🔴 安全閥：peak 超過「機器 RAM × 本比例」即**主動停掉分析**並記為超標點。
#    規格本就寫「採樣至任務結束**或被 kill**」——首版漏了 kill 那半，實測時
#    腳本停止採樣後任務仍在跑、footprint 一路爬到 5.7G/8G，是我手動殺掉的。
#    在 8GB 機器上預設 0.5（＝4GB）：再往上就進入 swap 風險區，量下去只是把機器推爆。
kill_ratio="0.5"

usage() {
  sed -n '2,32p' "$0" >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config-hash)   [ "$#" -ge 2 ] || usage; config_hash="$2"; shift 2 ;;
    --feature-count) [ "$#" -ge 2 ] || usage; feature_count="$2"; shift 2 ;;
    --symbol)        [ "$#" -ge 2 ] || usage; symbol="$2"; shift 2 ;;
    --timeframe)     [ "$#" -ge 2 ] || usage; timeframe="$2"; shift 2 ;;
    --out)           [ "$#" -ge 2 ] || usage; out="$2"; shift 2 ;;
    --interval-sec)  [ "$#" -ge 2 ] || usage; interval_sec="$2"; shift 2 ;;
    --max-sec)       [ "$#" -ge 2 ] || usage; max_sec="$2"; shift 2 ;;
    --api)           [ "$#" -ge 2 ] || usage; api="$2"; shift 2 ;;
    --kill-ratio)    [ "$#" -ge 2 ] || usage; kill_ratio="$2"; shift 2 ;;
    -h|--help)       usage ;;
    *) echo "ERROR: 未知參數 $1" >&2; usage ;;
  esac
done

for req in config_hash feature_count symbol timeframe out; do
  eval "val=\${$req}"
  [ -n "${val}" ] || { echo "ERROR: 缺必填參數 --$(echo "${req}" | tr '_' '-')" >&2; exit 2; }
done

# ---- ① machine ----
model="$(sysctl -n hw.model 2>/dev/null || echo unknown)"
mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
[ "${mem_bytes}" -gt 0 ] 2>/dev/null || { echo "ERROR: 取不到 hw.memsize（非 macOS？本協定綁 macOS sample）" >&2; exit 2; }

# ---- ② pid（單一，不得混進程）----
# 🔴 必須挑出真正的 **python** 進程：`pgrep -f 'run_api\.py'` 會連**包裝用的 shell**一起抓
#    （`/bin/zsh -c … venv/bin/python run_api.py` 的命令列同時含 python 與 run_api.py）
#    ⇒ 實測得到兩個 pid、本腳本誤判「多進程」而拒測；而量到 shell 的 footprint 毫無意義。
#    判準改為看**執行檔名**（`ps -o comm=`），不是看命令列字串。
pids=""
for _p in $(pgrep -f 'run_api\.py' 2>/dev/null || true); do
  case "$(ps -o comm= -p "${_p}" 2>/dev/null)" in
    *[Pp]ython*) pids="${pids}${_p}
" ;;
  esac
done
pids="$(printf '%s' "${pids}")"
n_pids="$(printf '%s\n' "${pids}" | grep -c '[0-9]' || true)"
if [ "${n_pids}" != "1" ]; then
  echo "ERROR: 期望**恰好一個** run_api.py 進程，實得 ${n_pids} 個：${pids}" >&2
  echo "       多進程時量到誰的都不算數（六欄之②要求單一 pid）。請先收斂到一個再測。" >&2
  exit 2
fi
pid="$(printf '%s\n' "${pids}" | grep -m1 '[0-9]')"

# `sample` 之 Physical footprint（bytes）。K/M/G 皆換算為 bytes。
footprint_bytes() {
  local target="$1" tmp line num unit
  tmp="$(mktemp -t icfootprint)"
  sample "${target}" 1 -f "${tmp}" >/dev/null 2>&1 || { rm -f "${tmp}"; echo ""; return; }
  line="$(grep -i 'Physical footprint (peak)' "${tmp}" | head -1)"
  [ -n "${line}" ] || line="$(grep -i 'Physical footprint' "${tmp}" | head -1)"
  rm -f "${tmp}"
  [ -n "${line}" ] || { echo ""; return; }
  num="$(printf '%s' "${line}" | sed -E 's/.*: *([0-9.]+)([KMG])B?.*/\1/')"
  unit="$(printf '%s' "${line}" | sed -E 's/.*: *([0-9.]+)([KMG])B?.*/\2/')"
  awk -v n="${num}" -v u="${unit}" 'BEGIN{
    m = (u=="K")?1024:((u=="M")?1048576:((u=="G")?1073741824:1));
    printf "%d\n", n*m }'
}

baseline="$(footprint_bytes "${pid}")"
[ -n "${baseline}" ] || { echo "ERROR: 取不到 baseline footprint（sample 失敗；pid=${pid}）" >&2; exit 2; }
echo "[measure] pid=${pid} baseline=${baseline} bytes（${model}，RAM ${mem_bytes} bytes）"

# ---- 發出 analyze 請求 ----
body="$(printf '{"symbol":"%s","timeframe":"%s","config_hash":"%s"}' "${symbol}" "${timeframe}" "${config_hash}")"
resp="$(curl -sS -X POST "${api}/api/v1/ic/analyze" -H 'Content-Type: application/json' -d "${body}" 2>&1 || true)"
echo "[measure] analyze 回應：${resp}"
task_id="$(printf '%s' "${resp}" | sed -E 's/.*"task_id" *: *"([^"]*)".*/\1/')"

# ---- ④ peak：採樣至任務結束或逾時 ----
started="$(date +%s)"
peak="${baseline}"
n_samples=0
exceeded="false"
kill_at="$(awk -v m="${mem_bytes}" -v r="${kill_ratio}" 'BEGIN{printf "%d", m*r}')"
echo "[measure] 安全閥：peak 超過 ${kill_at} bytes（RAM × ${kill_ratio}）即停止分析並記為超標點"
while : ; do
  now="$(date +%s)"
  elapsed=$(( now - started ))
  [ "${elapsed}" -lt "${max_sec}" ] || { echo "[measure] 逾時 ${max_sec}s，停止採樣"; break; }
  cur="$(footprint_bytes "${pid}")"
  if [ -n "${cur}" ]; then
    n_samples=$(( n_samples + 1 ))
    [ "${cur}" -gt "${peak}" ] 2>/dev/null && peak="${cur}"
    # 🔴 安全閥：超過門檻即**主動停掉分析**，不把機器推爆才記錄
    if [ "${peak}" -gt "${kill_at}" ] 2>/dev/null; then
      exceeded="true"
      echo "[measure] 🔴 peak=${peak} 超過 ${kill_at} ⇒ 記為**超標點**並停止該分析"
      [ -n "${task_id}" ] && curl -sS -m 5 -X DELETE "${api}/api/v1/ic/task/${task_id}" >/dev/null 2>&1
      kill -TERM "${pid}" 2>/dev/null
      break
    fi
  else
    echo "[measure] pid ${pid} 已消失（可能被 OOM kill）；停止採樣"
    break
  fi
  if [ -n "${task_id}" ] && [ "${task_id}" != "${resp}" ]; then
    st="$(curl -sS "${api}/api/v1/ic/task/${task_id}" 2>/dev/null || true)"
    case "${st}" in
      *'"status":"completed"'*|*'"status": "completed"'*|*'"status":"failed"'*|*'"status": "failed"'*)
        echo "[measure] 任務已結束"; break ;;
    esac
  fi
  sleep "${interval_sec}"
done
total_sec=$(( $(date +%s) - started ))

# ---- 寫 receipt（累積 points）----
mkdir -p "$(dirname "${out}")"
[ -f "${out}" ] || printf '{"epic":"gap3ux-b9","task":"6.2","tool":"%s","points":[]}\n' "${TOOL_LITERAL}" > "${out}"

point="$(printf '{"machine":{"model":"%s","ram_bytes":%s},"pid":%s,"baseline_footprint_bytes":%s,"peak_footprint_bytes":%s,"sampling":{"interval_sec":%s,"total_sec":%s,"n_samples":%s},"feature_count":%s,"tool":"%s","task_id":"%s","exceeded":%s,"kill_threshold_bytes":%s}' \
  "${model}" "${mem_bytes}" "${pid}" "${baseline}" "${peak}" "${interval_sec}" "${total_sec}" "${n_samples}" "${feature_count}" "${TOOL_LITERAL}" "${task_id}" "${exceeded}" "${kill_at}")"

tmp_out="$(mktemp -t icfpreceipt)"
jq --argjson p "${point}" '.points += [$p]' "${out}" > "${tmp_out}" && mv "${tmp_out}" "${out}"

echo "[measure] ✓ 量測點已寫入 ${out}"
echo "[measure]   feature_count=${feature_count} baseline=${baseline} peak=${peak} samples=${n_samples} total=${total_sec}s"
echo "[measure] 🔴 Task 6.2 要求 ≥3 個量測點、且同一 run 重跑 2 次之 peak 差 < 20%；請分次跑齊再算上限。"
echo "[measure] 🔴 上限 ＝ **最小超標點之 feature_count × 0.5**；在 receipt 齊備前**不得**把數字寫進設定。"
