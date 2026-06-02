#!/usr/bin/env bash
# template_check.sh — 機器驗證 SPEC/TODO 是否含 canonical 範本的必填錨點。
# 這是把「有沒有照範本」從『Claude 聲稱』變成『機器可驗』的關鍵；由 gate.sh 在派工/freeze 前呼叫。
#
# 用法：bash scripts/template_check.sh spec|todo <file>
# 退出：0=合規；1=缺錨點(列出缺什麼)/檔不存在/用法錯。
#
# 誠實邊界：只驗「結構錨點存在」，不驗每段內容充實（那是 adversarial review 的事）。
# 但「結構在」是必要條件——擋掉我那種扁平 checklist / 漏 §G 的文件。

set -u
kind="${1:-}"; file="${2:-}"
[ -n "${kind}" ] && [ -n "${file}" ] || { echo "用法: template_check.sh spec|todo <file>"; exit 1; }
[ -f "${file}" ] || { echo "ERROR: 檔不存在: ${file}"; exit 1; }

missing=""
need() { grep -qF "$1" "${file}" || missing="${missing}  · 缺錨點: $1  （$2）\n"; }
# 「A 或 B 擇一」：A 在就過；否則要求 B 出現（如 §G 缺則 §N 必須提到 §G）
need_or() { grep -qF "$1" "${file}" || grep -qF "$2" "${file}" || missing="${missing}  · 缺: $1（或於 $2 標 N/A）  （$3）\n"; }

case "${kind}" in
  spec)
    need "## §RISK" "風險分級"
    need "## §A"    "假設與待使用者確認"
    need "## §C"    "約束"
    need "## §P"    "Phase 與依賴"
    need "## §V"    "驗證策略與邊界"
    need "## §R"    "回退"
    need "## §N"    "N/A 登記"
    # §G Golden：有 §G 標題就過；否則 §N 區必須有一行同時含 §G 與 N/A
    if ! grep -qF "## §G" "${file}" && ! grep -qE "§G.*N/A|N/A.*§G" "${file}"; then
      missing="${missing}  · 缺: ## §G（高風險必填；不適用則於 §N 寫一行『§G：N/A — 理由』）\n"
    fi
    # §A facts-resolved（C3 反制）：§A 區必須「已確認」或明確宣告「待確認：無」，
    # 不准留著未解的待確認項就過機檢 → 擋「沒問到答案就在錯前提上寫 SPEC」。
    sec_a="$(awk '/^## §A/{f=1; print; next} f&&/^## /{f=0} f{print}' "${file}")"
    if [ -n "${sec_a}" ]; then
      if ! printf '%s' "${sec_a}" | grep -q "已確認" \
         && ! printf '%s' "${sec_a}" | grep -qE "待[^：:]*確認[：:][[:space:]]*無|無[^。]*待[^：:]*確認|無待確認"; then
        missing="${missing}  · §A 未解事實：§A 須含『已確認…（使用者回覆+日期）』或明確『待確認：無』。C3 反制：缺只有使用者知道的事實時，不准在錯前提上把 SPEC 寫完就過機檢。\n"
      fi
    fi
    ;;
  todo)
    need "## §0" "全域規則與約束"
    need "## §B" "批次執行策略"
    need "### Task" "至少一個 Task 區塊"
    # per-Task 三必填欄（presence；逐 Task 完整性交 adversarial review）
    need "驗證" "每 Task 可證偽驗證欄"
    need "邊界" "每 Task 邊界(≥2)欄"
    need "不可做" "每 Task 不可做欄"
    ;;
  *) echo "ERROR: kind 必須是 spec|todo"; exit 1 ;;
esac

# ---- 反空殼掃描（grep 錨點驗不到「標題在但內容空」；這層抓使用者遇過的「只寫表頭/驗證字樣、內容空」）----
# 誠實邊界：機械只抓「明顯空殼」（空表/樣板殘留/驗證無可證偽 token/§段無內容）。
# 「貌似合理但邏輯空」的精緻空殼靠 adversarial（不同模型）+ 執行閘兜底，非本層能保證。
hollow=""

# 1) 樣板殘留：複製範本未填（{{}} / 整行 TODO|TBD|xxx|待填|填此 / 整行 ...）
if grep -qE '\{\{|^[[:space:]]*(TODO|TBD|xxx|XXX|待填|填此)[[:space:]]*$|^[[:space:]]*\.\.\.[[:space:]]*$' "${file}"; then
  hollow="${hollow}  · 樣板殘留未填實（{{}} / 整行 TODO·TBD·xxx·待填·填此 / 整行 ...）\n"
fi

# 2) 空表：markdown 分隔列（|---|---|）後面沒有資料列 = 只有表頭
if awk '
    sep && $0 !~ /^[[:space:]]*\|/ { found=1 }
    { sep = ($0 ~ /^[[:space:]]*\|[-:| ]+\|[-:| ]*$/) }
    END { exit(found?0:1) }' "${file}"; then
  hollow="${hollow}  · 空表：有表頭+分隔列但無資料列（你遇過的『只寫表頭』）\n"
fi

# 3) 驗證欄不可證偽：bullet 行含「驗證」卻無任何可證偽 token
if awk '
    /^[[:space:]]*[-*].*驗證/ {
      if ($0 !~ /[0-9]|pytest|assert|==|<=|>=|!=|atol|rtol|sha256|grep|exit|\.py|\.json|\.h5|\.csv|\.parquet|npm|jest|vitest|expect|toHaveBeen|\.ts|\.tsx/) { found=1 }
    }
    END { exit(found?0:1) }' "${file}"; then
  hollow="${hollow}  · 驗證欄不可證偽：『驗證』bullet 缺具體 token（數字/pytest/==/atol/.py/sha256…），疑似『確認正確』式空話\n"
fi

# 註：非表格的「空段」未做機械檢查（易誤擋 inline 內容/子段）→ 交 coverage_check（缺項）+ adversarial（不同模型讀實際內容）。

if [ -n "${missing}" ] || [ -n "${hollow}" ]; then
  echo "TEMPLATE FAIL (${kind}): ${file}"
  [ -n "${missing}" ] && { echo "【缺必填錨點】"; printf "%b" "${missing}"; }
  [ -n "${hollow}" ]  && { echo "【空殼/敷衍偵測】"; printf "%b" "${hollow}"; }
  echo "  → 依 templates/$( [ "${kind}" = spec ] && echo SPEC_TEMPLATE.md || echo TODO_GENERATION_PROMPT.md ) 補齊結構與內容。"
  exit 1
fi
echo "TEMPLATE PASS (${kind}): ${file} 含全部必填錨點，且無明顯空殼。"
