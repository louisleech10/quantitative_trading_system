#!/usr/bin/env bash
# template_check.sh — 機器驗證 SPEC/TODO 是否含 canonical 範本的必填錨點。
# 這是把「有沒有照範本」從『Claude 聲稱』變成『機器可驗』的關鍵；由 gate.sh 在派工/freeze 前呼叫。
#
# 用法：bash scripts/template_check.sh spec|todo|result|dext <file>
# 退出：0=合規；1=缺錨點(列出缺什麼)/檔不存在/用法錯。
#
# 誠實邊界：只驗「結構錨點存在」，不驗每段內容充實（那是 adversarial review 的事）。
# 但「結構在」是必要條件——擋掉我那種扁平 checklist / 漏 §G 的文件。

set -u
# SCRIPT_DIR:供 legacy manifest 查找(2026-07-20 制度案新增;本腳本原無此變數,set -u 下未定義會中止)
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# _lc_repo_rel:把任意路徑正規化為 repo-relative(canonical);repo 外的檔回傳絕對路徑(必不在 manifest→強制)
_lc_repo_rel() {
  _p="$(cd "$(dirname "${1}")" 2>/dev/null && pwd)/$(basename "${1}")" || _p="${1}"
  case "${_p}" in "${REPO_ROOT}/"*) printf '%s' "${_p#${REPO_ROOT}/}" ;; *) printf '%s' "${_p}" ;; esac
}
kind="${1:-}"; file="${2:-}"
[ -n "${kind}" ] && [ -n "${file}" ] || { echo "用法: template_check.sh spec|todo|result|dext <file>"; exit 1; }
[ -f "${file}" ] || { echo "ERROR: 檔不存在: ${file}"; exit 1; }

missing=""
need() { grep -qF "$1" "${file}" || missing="${missing}  · 缺錨點: $1  （$2）\n"; }
# 「A 或 B 擇一」：A 在就過；否則要求 B 出現（如 §G 缺則 §N 必須提到 §G）
need_or() { grep -qF "$1" "${file}" || grep -qF "$2" "${file}" || missing="${missing}  · 缺: $1（或於 $2 標 N/A）  （$3）\n"; }

# §A 段級 fact-scope 狀態機（Task 2.1 [A-1][A-2]）
check_sec_a_fact_scope() {
  local sec_a="$1"
  [ -n "${sec_a}" ] || return 0

  local fact_missing=""
  local sec_a_lines=()
  local sec_a_line_count=0
  local idx fact_scope=0 line prev_line next_line
  while IFS= read -r line; do
    sec_a_lines[sec_a_line_count]="${line}"
    sec_a_line_count=$((sec_a_line_count + 1))
  done <<EOF
${sec_a}
EOF

  idx=0
  while [ "${idx}" -lt "${sec_a_line_count}" ]; do
    line="${sec_a_lines[$idx]}"
    if printf '%s' "${line}" | grep -qE '^###[[:space:]]' \
       && printf '%s' "${line}" | grep -qE '已驗證事實|已確認'; then
      fact_scope=1
    elif printf '%s' "${line}" | grep -qE '^###[[:space:]]' \
         && ! printf '%s' "${line}" | grep -qE '已驗證事實|已確認'; then
      fact_scope=0
    elif printf '%s' "${line}" | grep -qE '^-[[:space:]]+\*\*' \
       && printf '%s' "${line}" | grep -qE '已驗證事實|已確認'; then
      fact_scope=1
    elif printf '%s' "${line}" | grep -qE '^-[[:space:]]+\*\*' \
         && ! printf '%s' "${line}" | grep -qE '已驗證事實|已確認'; then
      fact_scope=0
    fi
    if [ "${fact_scope}" -eq 1 ] \
       && printf '%s' "${line}" | grep -qE 'handoffs/|\.md' \
       && ! printf '%s' "${line}" | grep -qE 'DatetimeIndex|int64|float64|float16|dtype|ndarray|DataFrame|Series|raw_data|形狀|型別|單位|資料結構'; then
      : # 純檔案引用無型別斷言，不觸發
    elif [ "${fact_scope}" -eq 1 ] \
       && printf '%s' "${line}" | grep -qE 'DatetimeIndex|int64|float64|float16|dtype|ndarray|DataFrame|Series|raw_data|形狀|型別|單位|資料結構|pytest|npm|bash|python|exit|rc=|stdout|stderr|輸出|印出|passed|failed|sha256'; then
      prev_line=""
      next_line=""
      if [ "${idx}" -gt 0 ]; then
        prev_line="${sec_a_lines[$((idx - 1))]}"
      fi
      if [ "${idx}" -lt $((sec_a_line_count - 1)) ]; then
        next_line="${sec_a_lines[$((idx + 1))]}"
      fi
      if ! printf '%s\n%s\n%s' "${prev_line}" "${line}" "${next_line}" | grep -q 'FACT-RECEIPT:'; then
        fact_missing="${fact_missing}  · §A fact-scope 缺 FACT-RECEIPT: ${line}\n"
      fi
    fi
    idx=$((idx + 1))
  done

  if [ -n "${fact_missing}" ]; then
    missing="${missing}${fact_missing}"
  fi
}

case "${kind}" in
  spec)
    need "## §RISK" "風險分級"
    need "## §A"    "假設與待使用者確認"
    need "## §C"    "約束"
    need "## §P"    "Phase 與依賴"
    need "## §V"    "驗證策略與邊界"
    need "## §R"    "回退"
    need "## §N"    "N/A 登記"

    # per-Task 生命週期欄檢查（2026-07-20 制度改進案 GOV-NECESSITY-REVIEW-*）
    # SPEC §P 的 Task 格式為 **Task N.x — ...**（粗體），與 TODO 的 ### Task 不同，故獨立一段。
    # 機檢**只驗欄位存在**，語義正確性交 adversarial（gate metadata 無法證明答案內容）。
    # 追溯性豁免(2026-07-20 制度案;v2 改用明確 legacy manifest)
    # 判準=檔名**不在** scripts/template_lifecycle_legacy.txt → 視為新文件 → 兩欄強制。
    # v1 曾用「檔內有無『存活至』」啟發式,經 codex(gov-impl-stamp 輪 REJECTED)指出**可被新文件完全不寫該欄整體規避**,已廢。
    # 改 allowlist 後:新檔預設落入強制範圍;規避需手動把自己加進 manifest(留痕可稽核)。
    # v3:改 repo-relative path 比對(v2 basename 可被「同名不同路徑」規避,codex 實證)
    _lc_rel="$(_lc_repo_rel "${file}")"
    _lc_legacy=0
    if [ -f "${SCRIPT_DIR}/template_lifecycle_legacy.txt" ] \
       && grep -qxF "${_lc_rel}" "${SCRIPT_DIR}/template_lifecycle_legacy.txt" 2>/dev/null; then
      _lc_legacy=1
    fi
    if [ "${_lc_legacy}" -eq 0 ]; then
    spec_task_missing="$(awk '
      BEGIN { in_task=0; title=""; ntask=0 }
      # v3:heading 廣義化(codex 實證 `**Task` 以外變體可使檢查零 Task 而誤判合規)
      # 涵蓋行首 **Task 與 ##+ Task;**刻意不含** `- **Task` 項目符號形式——
      # 內文常有「- **Task 3.1 驗收須含…**」這類交叉引用,誤判會把區塊切斷(Claude 實測)
      /^(\*\*Task[ .0-9]|##+[[:space:]]*Task[ .0-9])/ {
        if (in_task) check_block()
        in_task=1; title=$0; has_s=0; has_o=0; has_v=0; has_b=0; has_x=0; ntask++
        next
      }
      /^### Phase|^## / { if (in_task) { check_block(); in_task=0 } }
      in_task {
        if ($0 ~ /存活至/) has_s=1
        if ($0 ~ /覆蓋風險/) has_o=1
        if ($0 ~ /驗證/) has_v=1
        if ($0 ~ /邊界/) has_b=1
        if ($0 ~ /不可做/) has_x=1
      }
      END {
        if (in_task) check_block()
        if (ntask == 0) printf "  · §P 偵測到 0 個 Task(heading 須為行首 `**Task N.x — …**` 或 `## Task`);零 Task 不得視為合規\n"
      }
      function check_block() {
        if (!has_s) printf "  · Task 缺欄「存活至」(產出最終保留到哪個 Phase): %s\n", title
        if (!has_o) printf "  · Task 缺欄「覆蓋風險」(後續 Phase 會否刪/覆蓋;不會寫「無」): %s\n", title
        if (!has_v) printf "  · Task 缺欄「驗證」: %s\n", title
        if (!has_b) printf "  · Task 缺欄「邊界」: %s\n", title
        if (!has_x) printf "  · Task 缺欄「不可做」: %s\n", title
      }
    ' "${file}")"
    if [ -n "${spec_task_missing}" ]; then
      missing="${missing}${spec_task_missing}\n"
    fi
    fi

    # §RISK RISK-HIT 宣告制（Task 2.2 [A-3]）
    sec_risk="$(awk '/^## §RISK/{f=1; print; next} f&&/^## /{f=0} f{print}' "${file}")"
    risk_hit_line="$(printf '%s\n' "${sec_risk}" | grep -E '^[[:space:]]*(-[[:space:]]+)?RISK-HIT:' | head -1 || true)"
    risk_hit_dup="$(printf '%s\n' "${sec_risk}" | grep -cE '^[[:space:]]*(-[[:space:]]+)?RISK-HIT:' || true)"
    if [ "${risk_hit_dup}" -gt 1 ]; then
      echo "WARN: §RISK 內 RISK-HIT: 重複宣告，機檢取第一行" >&2
    fi
    if [ -z "${risk_hit_line}" ]; then
      missing="${missing}  · §RISK 缺 RISK-HIT: 宣告行（格式 RISK-HIT: <a,b,c,d 子集|none>）\n"
    else
      risk_hit_val="${risk_hit_line#*RISK-HIT:}"
      risk_hit_val="$(printf '%s' "${risk_hit_val}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      risk_needs_g=0
      if printf '%s' "${risk_hit_val}" | grep -qE '(^|[,[:space:]])a([,[:space:]]|$)|(^|[,[:space:]])d([,[:space:]]|$)'; then
        risk_needs_g=1
      fi
      if [ "${risk_needs_g}" -eq 1 ]; then
        if ! grep -qF "## §G" "${file}"; then
          missing="${missing}  · RISK-HIT 含 a/d 但缺 ## §G（高風險數值 golden 必填）\n"
        else
          sec_g="$(awk '/^## §G/{f=1; print; next} f&&/^## /{f=0} f{print}' "${file}")"
          if ! printf '%s' "${sec_g}" | grep -qE 'atol|rtol|sha256'; then
            missing="${missing}  · §G 缺數值 golden token（atol|rtol|sha256 至少其一）\n"
          fi
        fi
        sec_n="$(awk '/^## §N/{f=1; print; next} f&&/^## /{f=0} f{print}' "${file}")"
        if printf '%s' "${sec_n}" | grep -qE '§G.*N/A|N/A.*§G'; then
          missing="${missing}  · RISK-HIT 含 a/d 時 §N 不得標 §G N/A 豁免\n"
        fi
      else
        need_or "## §G" "§G" "高風險必填；不適用則於 §N 標 N/A"
      fi
    fi

    # §A facts-resolved（C3 反制 + Task 2.4 [A-6] 待確認變體）
    sec_a="$(awk '/^## §A/{f=1; print; next} f&&/^## /{f=0} f{print}' "${file}")"
    if [ -n "${sec_a}" ]; then
      facts_resolved=0
      if printf '%s' "${sec_a}" | grep -qE '待[^：:]*確認[^：:]*[：:][[:space:]]*無|待[^：:]*確認[^：:]*[：:].*[本此]?任務?無|確認[：:][[:space:]]*本任務無|無[^。]*待[^：:]*確認|無待確認'; then
        facts_resolved=1
      fi
      while IFS= read -r confirm_line; do
        [ -n "${confirm_line}" ] || continue
        if printf '%s' "${confirm_line}" | grep -q '待回覆\|未確認\|無法確認'; then
          continue
        fi
        if printf '%s' "${confirm_line}" | grep -qE '[0-9]{4}-[0-9]{2}-[0-9]{2}|使用者'; then
          facts_resolved=1
        fi
      done <<EOF
$(printf '%s' "${sec_a}" | grep '已確認' || true)
EOF
      if [ "${facts_resolved}" -eq 0 ]; then
        missing="${missing}  · §A 未解事實：§A 須含『已確認…（使用者回覆+日期）』或明確『待確認：無』／『待使用者確認：本任務無』。C3 反制：缺只有使用者知道的事實時，不准在錯前提上把 SPEC 寫完就過機檢。\n"
      fi
      check_sec_a_fact_scope "${sec_a}"
    fi
    ;;
  result)
    need "STATIC_CHECK=" "RESULT 硬欄位 STATIC_CHECK"
    need "RUNTIME_CHECK=" "RESULT 硬欄位 RUNTIME_CHECK"
    need "MUTATION_CHECK=" "RESULT 硬欄位 MUTATION_CHECK"
    need "RECEIPTS=" "RESULT 硬欄位 RECEIPTS"
    need "OPEN_PENDING=" "RESULT 硬欄位 OPEN_PENDING"
    enum_bad=""
    while IFS= read -r chkline; do
      field="${chkline%%=*}"
      value="${chkline#*=}"
      value="$(printf '%s' "${value}" | sed 's/[[:space:]]*$//' | sed 's/^[[:space:]]*//')"
      case "${value}" in
        NOT_RUN|PASS|FAIL) ;;
        N/A:*) ;;
        *)
          enum_bad="${enum_bad}  · ${field} 枚舉外值: ${value}（允許 NOT_RUN|PASS|FAIL|N/A:reason）\n"
          ;;
      esac
    done <<EOF
$(grep -E '^(STATIC_CHECK|RUNTIME_CHECK|MUTATION_CHECK)=' "${file}" || true)
EOF
    if [ -n "${enum_bad}" ]; then
      missing="${missing}${enum_bad}"
    fi

    # Task 2.4 [A-5] RUNTIME PASS ⇒ RECEIPTS 非空
    runtime_pass="$(grep -E '^RUNTIME_CHECK=' "${file}" | head -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true)"
    receipts_line="$(grep -E '^RECEIPTS=' "${file}" | head -1 || true)"
    receipts_val="${receipts_line#RECEIPTS=}"
    receipts_val="$(printf '%s' "${receipts_val}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ "${runtime_pass}" = "PASS" ]; then
      case "${receipts_val}" in
        ""|'[]'|'[ ]'|'[" "]'|'[""]'|'[ ]')
          missing="${missing}  · RUNTIME_CHECK=PASS 時 RECEIPTS 不得為空（${receipts_line}）\n"
          ;;
      esac
      if printf '%s' "${receipts_val}" | grep -qE '^\[[[:space:]]*\]$|^\[[[:space:]]*"[[:space:]]*"\]$'; then
        missing="${missing}  · RUNTIME_CHECK=PASS 時 RECEIPTS 不得為空陣列或空白元素（${receipts_line}）\n"
      fi
    fi

    # Task 2.4 [A-5] MUTATION_CHECK=NOT_RUN ⇒ discussion 外禁 operational 極性
    mutation_val="$(grep -E '^MUTATION_CHECK=' "${file}" | head -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true)"
    if [ "${mutation_val}" = "NOT_RUN" ]; then
      in_discussion=0
      operational_bad=""
      while IFS= read -r res_line; do
        if [ "${in_discussion}" -eq 1 ]; then
          if printf '%s' "${res_line}" | grep -qE '^##[[:space:]]'; then
            in_discussion=0
          elif printf '%s' "${res_line}" | grep -q 'claim-context:'; then
            in_discussion=0
            continue
          else
            continue
          fi
        fi
        if printf '%s' "${res_line}" | grep -q 'claim-context:[[:space:]]*discussion'; then
          in_discussion=1
          continue
        fi
        if printf '%s' "${res_line}" | grep -q 'claim-context:'; then
          continue
        fi
        if printf '%s' "${res_line}" | grep -qE '^[[:space:]]*#'; then
          continue
        fi
        stripped="${res_line}"
        stripped="$(printf '%s' "${stripped}" | sed 's/`[^`]*`//g')"
        if printf '%s' "${stripped}" | grep -qE '已驗|DONE|全綠'; then
          operational_bad="${operational_bad}  · MUTATION_CHECK=NOT_RUN 時 discussion 外禁 operational 極性: ${res_line}\n"
        fi
      done < "${file}"
      if [ -n "${operational_bad}" ]; then
        missing="${missing}${operational_bad}"
      fi
    fi
    ;;
  todo)
    need "## §0" "全域規則與約束"
    need "## §B" "批次執行策略"
    need "### Task" "至少一個 Task 區塊"
    # 追溯性豁免同 spec 側(v2:legacy manifest;啟發式版可被整體規避已廢)
    _lc_rel="$(_lc_repo_rel "${file}")"
    todo_adopted=1
    if [ -f "${SCRIPT_DIR}/template_lifecycle_legacy.txt" ] \
       && grep -qxF "${_lc_rel}" "${SCRIPT_DIR}/template_lifecycle_legacy.txt" 2>/dev/null; then
      todo_adopted=0
    fi
    # Task 2.3 [A-4] per-Task 三欄分段檢查
    task_missing="$(awk -v adopted="${todo_adopted}" '
      BEGIN { in_task=0; title="" }
      /^### Task/ {
        if (in_task) check_block()
        in_task=1
        title=$0
        has_v=0; has_b=0; has_x=0; has_s=0; has_o=0
        next
      }
      in_task {
        if ($0 ~ /驗證/) has_v=1
        if ($0 ~ /邊界/) has_b=1
        if ($0 ~ /不可做/) has_x=1
        if ($0 ~ /存活至/) has_s=1
        if ($0 ~ /覆蓋風險/) has_o=1
      }
      END { if (in_task) check_block() }
      function check_block() {
        if (!has_v) printf "  · Task 缺欄「驗證」: %s\\n", title
        if (!has_b) printf "  · Task 缺欄「邊界」: %s\\n", title
        if (!has_x) printf "  · Task 缺欄「不可做」: %s\\n", title
        if (adopted && !has_s) printf "  · Task 缺欄「存活至」(2026-07-20 制度案;產出最終保留到哪個 Phase): %s\\n", title
        if (adopted && !has_o) printf "  · Task 缺欄「覆蓋風險」(2026-07-20 制度案;後續 Phase 會否刪/覆蓋,不會寫「無」): %s\\n", title
      }
    ' "${file}")"
    if [ -n "${task_missing}" ]; then
      missing="${missing}${task_missing}"
    fi
    ;;
  dext)
    # 凍結文件「D 延伸」檔（docs/<原檔 basename>.D-<NNN>.md）。
    # 錨點逐字取自 docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.2「延伸檔必填」——
    # 該節是 canonical 單一真相源，本處只做機器驗證，**不重列規則**（重列會漂移）。
    # （2026-08-03：v1.0 §2 已被 v2.0 §2.2 取代，模板內容不變；v1.0 檔頭有節號對照表。）
    # 出生理由（GOV-DEXT-TEMPLATE-KIND）：D-001 實戰時 `gate.sh dispatch --spec <D延伸檔>`
    #   走 `spec` kind → 要求完整 SPEC 錨點 → **永遠拒發 token**，只能改傳底本繞過。
    need "BASE:" "§2：原檔路徑 @ commit-sha"
    need "PREDECESSOR:" "§2：前一份生效中的延伸檔路徑，或 none（不得省略）"
    need "改什麼:" "§2：一句話"
    need "為什麼:" "§2：一句話，或指向 reconcile 路徑"
    need "## 觸及面宣告" "§2：給審查者對讀原檔用"
    need "新增:" "§2 觸及面宣告：原檔中實際存在的 heading 逐字，或 none"
    need "覆寫:" "§2 觸及面宣告：同上，或 none"
    need "依賴:" "§2 觸及面宣告：同上，或 none"
    need "## 內容" "§2：實際的修訂內容"
    need "## 戳記" "§2：GROK-R7-P1-01 — 缺此標題時 reconcile_stamps_check.sh 直接 FAIL"
    # 觸及面宣告三欄**不得留空**（§2 逐字：「無則寫 none，不得留空」）。
    # 只驗「冒號後有非空白字元」；是否為原檔實際 heading 屬語意，交審查者對讀。
    dext_blank="$(awk '
      /^[[:space:]]*(新增|覆寫|依賴):/ {
        v = $0
        sub(/^[[:space:]]*(新增|覆寫|依賴):[[:space:]]*/, "", v)
        gsub(/[[:space:]]+$/, "", v)
        if (v == "") { split($0, a, ":"); printf "  · 觸及面宣告欄留空: %s（§2 逐字「無則寫 none，不得留空」）\\n", a[1] }
      }' "${file}")"
    if [ -n "${dext_blank}" ]; then
      missing="${missing}${dext_blank}"
    fi
    # BASE 須帶 commit-sha（§2：「用 git rev-parse HEAD 取，寫下當時的值」）。
    # 只驗「有一段 ≥7 位 hex」——不驗該 sha 是否可解析（那需要 git，且延伸檔可能先於 commit 寫成）。
    if ! grep -qE '^[[:space:]]*BASE:.*[0-9a-f]{7,}' "${file}"; then
      missing="${missing}  · BASE 缺 commit-sha（§2：git rev-parse HEAD 取，須寫下當時的值；格式 <原檔路徑> @ <sha>）\n"
    fi
    ;;
  *) echo "ERROR: kind 必須是 spec|todo|result|dext"; exit 1 ;;
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
#
# ⚠️ kind=dext 收窄為「『驗證』出現在 bullet **開頭當標籤**」才檢查；spec/todo/result 維持原判準不變。
#    理由（實測，非推測）：本檢查針對 SPEC/TODO 的結構化「驗證欄」而設，判準是「bullet 行含『驗證』」。
#    D 延伸檔的 `## 內容` 是自由散文，敘述「改了什麼／不改什麼」時會自然提到「驗證」二字。
#    首個真實案例 docs/P16_COMMITTEE_DEBT_SPEC.D-001.md:192
#      「- 不改 `gate.sh register-output` 本身的任何驗證」
#    ——那是一條「明文不做」宣告，不是驗證欄，卻被判空殼。
#    **這是為新 kind 定範圍，不是放寬既有 kind**：spec/todo/result 走的分支逐位元組未動，
#    且 dext 仍保留「真的寫成驗證欄」時的檢查（`- 驗證…` / `- **驗證**…`）。
#    誠實邊界：dext 的 `## 內容` 若把空話驗證寫在句中而非行首標籤，本層抓不到 → 交 adversarial。
_hollow3_re='^[[:space:]]*[-*].*驗證'
if [ "${kind}" = "dext" ]; then
  # 用 [*][*] 而非 \*\*：動態正則字串裡的反斜線會先被 awk 當字串跳脫處理（gawk 會警告），
  # 中括號類別不含反斜線，跨 awk 實作行為一致。
  _hollow3_re='^[[:space:]]*[-*][[:space:]]*([*][*])?驗證'
fi
if awk -v re="${_hollow3_re}" '
    $0 ~ re {
      if ($0 !~ /[0-9]|pytest|assert|==|<=|>=|!=|atol|rtol|sha256|grep|exit|\.py|\.json|\.h5|\.csv|\.parquet|npm|jest|vitest|expect|toHaveBeen|\.ts|\.tsx/) { found=1 }
    }
    END { exit(found?0:1) }' "${file}"; then
  hollow="${hollow}  · 驗證欄不可證偽：『驗證』bullet 缺具體 token（數字/pytest/==/atol/.py/sha256…），疑似『確認正確』式空話\n"
fi

# 註：非表格的「空段」未做機械檢查（易誤擋 inline 內容/子段）→ 交 coverage_check（缺項）+ adversarial（不同模型讀實際內容）。

# ===========================================================================
# 票 B-16 擴充 A/B/C（GOVB1 Task 1.5）—— **一律 append，禁重排既有行**
#   test_doc_format_precheck.py 以替換原始碼子字串做 mutation，重排會使其轉紅（B4 踩過）。
#
# 🔴 三個判準全部**行首錨定 + 排除 code fence**，不掃自然語言。
#   出處：handoffs/20260809-govb1-b5-impl-r1-brief.md §0 定案 1（防第六次結構性死鎖）。
#   實測依據（2026-08-09 現跑，非推測）：
#     `^[[:blank:]]*ASSERT` / `^[[:blank:]]*函式：` / `^[[:blank:]]*SCOPE-CLAIM:`
#     對凍結之 GOVB1 SPEC 與 TODO **皆 0 命中** ⇒ 不自鎖。
#
# 🔴 行首錨定用 `[[:blank:]]`（ASCII 空白＋TAB），**不得用 `[[:space:]]`**
#   〔`COMPOSER-R1-P2-01`，2026-08-09 複驗成立〕：
#   POSIX `[[:space:]]` 在本環境**含 NBSP(U+00A0) 與全形空白(U+3000)** ⇒
#   從網頁／Word 貼上、看起來像散文縮排的
#   `<NBSP>ASSERT bash scripts/gate.sh dispatch … THEN rc=0` **會被匹配並執行**。
#   實測：`[[:space:]]` → NBSP/全形皆命中；`[[:blank:]]` → 皆不命中，空白/TAB 仍命中。
#   （BOM U+FEFF 兩者皆不命中，本來就安全。）
# 🔴 **禁用 `[ \t]` 代替**：本平台實測 sed 完全不替換、grep 認不得 TAB
#   卻**誤放行字面反斜線** ⇒ 比原病更糟。
#     反例：**未錨定**的 `ASSERT ` 在 TODO 有 **33 個命中**，其中一條是
#     `ASSERT bash scripts/gate.sh dispatch …` ⇒ 照 TODO 偽碼直譯會在**每次
#     template_check 時真的發 token、寫稽核日誌**。錨定是承重的，不是風格。
# ===========================================================================

# _tc_live_lines <file> — 正規化 CRLF + 去除 code fence 區塊後的內容（供三個判準共用）
#   fence 有界集合＝``` 或 ~~~（各 3 個以上），比照 B4 之 fence 規則。
#   🔴 fence 須追蹤**字元與長度**並在未閉合時 fail-closed〔`CODEX-R2-P1-01`〕：
#     初版用單一 toggle ⇒ ① 未閉合 fence **吞到 EOF**，其後宣告靜默漏檢（fail-open）
#     ② ``` 與 ~~~ 混用會錯配 ③ 4 個以上反引號之 fence 亦被當同一種。
#   🔴 BOM(U+FEFF) 先剝除：否則首行之 `ASSERT`／`SCOPE-CLAIM:` 靜默不被選取。
#   未閉合 ⇒ 於 stderr 標記並**回非零**，由呼叫端轉為失敗（不得靜默略過）。
_tc_live_lines() {
  tr -d '\r' < "${1}" | sed -e '1s/^\xEF\xBB\xBF//' | awk '
    {
      line = $0
      t = line; sub(/^[ \t]+/, "", t)
      ch = ""; n = 0
      if (substr(t, 1, 3) == "```") { ch = "`" }
      else if (substr(t, 1, 3) == "~~~") { ch = "~" }
      if (ch != "") {
        while (substr(t, n + 1, 1) == ch) n++
        if (!infence) { infence = 1; fch = ch; flen = n; next }
        # 收合條件：同字元且長度不短於開啟者（CommonMark 規則）
        if (ch == fch && n >= flen) { infence = 0; next }
        next   # 不同字元／較短 ⇒ 仍在 fence 內，內容不算宣告
      }
      if (!infence) print
    }
    END { if (infence) { print "TEMPLATE-FENCE-UNCLOSED" > "/dev/stderr"; exit 3 } }'
}

# _tc_live_or_die <file> — 取 live 行；fence 未閉合 ⇒ 回非零（呼叫端須轉失敗）
_tc_live_or_die() {
  _tl_out="$(_tc_live_lines "${1}" 2>/dev/null)"
  _tl_rc=$?
  printf '%s\n' "${_tl_out}"
  return "${_tl_rc}"
}

# _tc_ere_escape — 把任意字串轉為 ERE 字面量
#   TODO 偽碼把 `${1}` 直接嵌進 regex ⇒ `f.oo` 誤命中 `fXoo`、`f*` 誤命中 `f`（三方實測）。
_tc_ere_escape() {
  printf '%s' "${1}" | sed -e 's/[\\^$.[|()*+?{]/\\&/g' -e 's/\]/\\]/g'
}

# _func_exists <name> <file> — 檔內是否**定義**了該函式（四種合法形態全命中）
#   TODO 偽碼 `^[[:space:]]*(def |function )?${1}[[:space:]]*\(` 漏接
#   `function foo {`（POSIX 無括號形），三方逐字實跑一致。
#   邊界②「須先剝除 `#` 起始行」**已由 `^` 錨點滿足**（codex 實測兩種註解皆 rc=1）⇒ 不另加剝除。
_func_exists() {
  _fe_n="$(_tc_ere_escape "${1}")"
  _fe_f="${2}"
  [ -f "${_fe_f}" ] || return 1
  grep -qE "^[[:space:]]*def[[:space:]]+${_fe_n}[[:space:]]*\(" "${_fe_f}" && return 0
  grep -qE "^[[:space:]]*${_fe_n}[[:space:]]*\([[:space:]]*\)[[:space:]]*\{" "${_fe_f}" && return 0
  grep -qE "^[[:space:]]*function[[:space:]]+${_fe_n}([[:space:]]*\([[:space:]]*\))?[[:space:]]*\{" "${_fe_f}" && return 0
  return 1
}

# _check_scope_claim <file> — C：封閉文法之宣告完整性（**不執行** DERIVE 命令）
#   文法：SCOPE-CLAIM:<id> <subject> DERIVE:<executable command>
_check_scope_claim() {
  _sc_out=""
  _sc_seen=""
  while IFS= read -r _sc_l; do
    case "${_sc_l}" in
      *SCOPE-CLAIM:*) : ;;
      *) continue ;;
    esac
    printf '%s' "${_sc_l}" | grep -qE '^[[:blank:]]*SCOPE-CLAIM:' || continue
    _sc_body="$(printf '%s' "${_sc_l}" | sed -e 's/^[[:blank:]]*SCOPE-CLAIM:[[:space:]]*//')"
    _sc_id="$(printf '%s' "${_sc_body}" | awk '{print $1}')"
    if ! printf '%s' "${_sc_id}" | grep -qE '^[A-Za-z0-9_-]+$'; then
      _sc_out="${_sc_out}  · SCOPE-CLAIM <id> 不合文法（須 [A-Za-z0-9_-]+）: ${_sc_id:-<空>}\n"
      continue
    fi
    case " ${_sc_seen} " in
      *" ${_sc_id} "*) _sc_out="${_sc_out}  · SCOPE-CLAIM <id> 重複: ${_sc_id}\n"; continue ;;
    esac
    _sc_seen="${_sc_seen} ${_sc_id}"
    _sc_rest="$(printf '%s' "${_sc_body}" | sed -e 's/^[A-Za-z0-9_-]*[[:space:]]*//')"
    _sc_n="$(printf '%s\n' "${_sc_rest}" | grep -oE 'DERIVE:' | wc -l | tr -d '[:space:]')"
    if [ "${_sc_n}" != "1" ]; then
      _sc_out="${_sc_out}  · SCOPE-CLAIM ${_sc_id}: DERIVE: 須恰一個（實得 ${_sc_n}）\n"
      continue
    fi
    _sc_sub="$(printf '%s' "${_sc_rest}" | sed -e 's/DERIVE:.*$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    _sc_cmd="$(printf '%s' "${_sc_rest}" | sed -e 's/^.*DERIVE://' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -n "${_sc_sub}" ] || _sc_out="${_sc_out}  · SCOPE-CLAIM ${_sc_id}: <subject> 為空\n"
    [ -n "${_sc_cmd}" ] || _sc_out="${_sc_out}  · SCOPE-CLAIM ${_sc_id}: DERIVE 命令為空\n"
  done <<EOF
$(_tc_live_lines "${1}")
EOF
  [ -z "${_sc_out}" ] && return 0
  printf '%b' "${_sc_out}"
  return 1
}

# _run_assert_lines <file> — A：抽 `^ASSERT <argv…> THEN rc=<n>` 行並**執行**，比對 rc
#
# 🔴 整行封閉文法〔`CODEX-R2-P1-03`〕：`THEN rc=` 須**恰一個且位於行尾**。
#   初版用貪婪 `sed 's/.*THEN rc=\(…\).*/\1/'` ⇒ `ASSERT false THEN rc=0 THEN rc=1`
#   取**最後**一個 rc，執行 `false` 得 1、期望 1 ⇒ **畸形行變假綠**（codex 實測）。
#
# 🔴 **禁 `eval`，改逐字 argv 執行**〔`CODEX-R2-P1-04`〕：
#   初版 `( eval "${cmd}" )` ⇒ 命令可含 `;`／`&&`／`|`／重導向／`$(…)`，
#   codex 實證 `ASSERT : > <tmp>/marker THEN rc=0` **真的建了檔**。
#   錨定與 fence 只是「哪些行被選中」，**擋不住被選中那行做什麼**。
#   現行＝正向字元集合（`[A-Za-z0-9_./=:@,+-]` 與空白），命中集合外字元即**判失敗**，
#   且以 `set --` 拆詞後直接執行，不經 shell 再解析。
#
# 🔴 pending **預設拒絕**，須呼叫端明示 opt-in〔`CODEX-R2-P1-02`〕：
#   composer 判「受檢檔自宣告可接受」、codex 判「守衛強度下降」——採較嚴者。
#   文件自己寫一行 `新建：` 就能為自己開 pending，權威來源等於受檢物本身。
#   現行：`TEMPLATE_CHECK_ALLOW_PENDING=1` 才可能 pending，且仍須三條件全成立。
#   預設關閉 ⇒ 凍結文件路徑永不 pend；此為 fail-closed 方向。
_TC_ASSERT_SAFE_CHARS='^[A-Za-z0-9_./=:@,+ 	-]*$'
# 🔴 字元集合**不足以**封閉〔codex 於 B5-STAMP-R2 REJECTED 並實證〕：
#     `ASSERT env FOO=bar /usr/bin/touch <marker> THEN rc=0` → rc=0 且 marker **真的建立**
#     `ASSERT ../../../../usr/bin/true THEN rc=0`            → rc=0，路徑穿越成功
#   字元集合只擋 shell 元字元／glob，**擋不住「執行任意命令」這件事本身**。
#   ⇒ 追加兩道封閉：①首 token 須在**封閉白名單**內 ②任何 token 不得為絕對路徑或含 `..`。
#   誠實邊界：白名單內之 `bash <repo 內腳本>` 仍會執行該腳本——那是 A 的**設計目的**
#   （規格內檢查條件落筆即跑）；封閉的是「跑什麼」的來源，不是「不跑」。
_TC_ASSERT_CMD_ALLOW='bash python3 pytest grep true false test'

# ── T0 止血（2026-08-12；consult 20260812-govassert-x-consult-r1 三家一致）──────
# 出生事故：某 SPEC 的 ASSERT 寫成 `bash scripts/gov_check.sh --no-probe …`
#   ⇒ 本函式**真的執行**它 ⇒ 整套 1521 個測試被當成「文件檢查」跑起來
#   ⇒ 吃光 per-user process 上限（實測 ulimit -u = 1333），連 `ps` 都 fork 不出來。
#   更糟：`doc_format_precheck.sh` 是 Write/Edit 的 PostToolUse hook 且會呼叫本檔
#   ⇒ **要編輯該文件去移除那條 ASSERT，存檔又會再次引爆 ⇒ 文件自鎖**，只能 `mv` 脫困。
#
# 兩層防線（**不動 `gate.sh` 之預設行為**——那是真正的驗收點，關掉會成保護真空）：
#   ① TEMPLATE_CHECK_NO_EXEC=1 ⇒ 文法／白名單／路徑檢查照跑，**只跳過執行**。
#      由 `doc_format_precheck.sh`（寫檔 hook）設定；gate/freeze 不設，行為逐字不變。
#   ② 逐行 timeout ⇒ 逾時**判 FAIL**（fail-closed，非略過），無論 ① 是否啟用。
#
# 🔴 具名殘留：kill 只送給直接子程序，**孫程序可能存活**（POSIX sh 無 job control，
#   背景子程序不必然自成 process group）。backstop＝`bash scripts/proc_guard.sh --clean`。
#   完整修法（process-group 覆蓋）歸後續完整管線。
# 🔴 秒數為 **PROVISIONAL**：codex 要求依 duration manifest 之
#   `ceil(max(max_duration, P99×1.25))` 定稿；在取得 receipt 前暫定 60s，且**拒絕空值**。
#   秒數取值與驗證**一律在 `_run_assert_lines` 內就地完成**（見該函式開頭）——
#   不在此設檔頭常數：既有測試會把該函式單獨抽出 eval，檔頭常數屆時不存在，
#   在 `set -u` 下會整支炸掉且無輸出（主委實測，24 條測試同時轉紅）。

_run_assert_lines() {
  _ra_file="${1}"
  _ra_out=""
  # 🔴 函式須自足：既有測試會把本函式**單獨抽出 eval**，屆時檔頭常數不存在，
  #   在 `set -u` 下直接炸且無輸出（主委實測踩到）。故在此就地取值並自帶預設。
  _ra_to="${_TC_ASSERT_TIMEOUT_SEC:-${TEMPLATE_CHECK_ASSERT_TIMEOUT_SEC:-60}}"
  case "${_ra_to}" in ''|*[!0-9]*) _ra_to=60 ;; esac
  [ "${_ra_to}" -gt 0 ] 2>/dev/null || _ra_to=60
  _ra_live="$(_tc_live_or_die "${_ra_file}")" || {
    printf '  · code fence 未閉合 ⇒ 其後宣告無法判定（fail-closed）\n'
    return 1
  }
  _ra_new="$(printf '%s\n' "${_ra_live}" \
    | grep -E '^[[:blank:]]*新建：' | grep -oE '`[^`]+`' | tr -d '`')"
  while IFS= read -r _ra_l; do
    printf '%s' "${_ra_l}" | grep -qE '^[[:blank:]]*ASSERT[[:space:]]' || continue
    # 整行文法：ASSERT <argv…> THEN rc=<n>$（THEN rc= 恰一個且在行尾）
    _ra_nthen="$(printf '%s\n' "${_ra_l}" | grep -oE 'THEN[[:space:]]+rc=' | wc -l | tr -d '[:space:]')"
    if [ "${_ra_nthen}" != "1" ] \
       || ! printf '%s' "${_ra_l}" | grep -qE 'THEN[[:space:]]+rc=[0-9]+[[:blank:]]*$'; then
      _ra_out="${_ra_out}  · ASSERT 行不合文法（須恰一個且位於行尾之 'THEN rc=<n>'）: ${_ra_l}\n"
      continue
    fi
    _ra_cmd="$(printf '%s' "${_ra_l}" | sed -e 's/^[[:blank:]]*ASSERT[[:space:]]*//' -e 's/[[:space:]]*THEN[[:space:]]*rc=[0-9]*[[:blank:]]*$//')"
    _ra_exp="$(printf '%s' "${_ra_l}" | sed -n 's/.*THEN[[:space:]]*rc=\([0-9][0-9]*\)[[:blank:]]*$/\1/p')"
    if [ -z "${_ra_cmd}" ] || [ -z "${_ra_exp}" ]; then
      _ra_out="${_ra_out}  · ASSERT 行無法解析（須 'ASSERT <cmd> THEN rc=<n>'）: ${_ra_l}\n"
      continue
    fi
    # 正向字元集合：集合外字元（; & | > < ` $ ( ) 引號 等）一律判失敗，不執行
    if ! printf '%s' "${_ra_cmd}" | grep -qE "${_TC_ASSERT_SAFE_CHARS}"; then
      _ra_out="${_ra_out}  · ASSERT 命令含集合外字元（禁 shell 元字元／重導向／命令替換）: ${_ra_cmd}\n"
      continue
    fi
    # ① 首 token 須在封閉白名單內（擋 env／touch／任意二進位）
    _ra_head="$(printf '%s' "${_ra_cmd}" | awk '{print $1}')"
    case " ${_TC_ASSERT_CMD_ALLOW} " in
      *" ${_ra_head} "*) : ;;
      *) _ra_out="${_ra_out}  · ASSERT 命令不在白名單（允許: ${_TC_ASSERT_CMD_ALLOW}）: ${_ra_head}\n"
         continue ;;
    esac
    # ② 任何 token 不得為絕對路徑或含 `..`（擋路徑穿越與 repo 外執行）
    _ra_bad=""
    for _ra_tok in ${_ra_cmd}; do
      case "${_ra_tok}" in
        /*|*..*) _ra_bad="${_ra_tok}"; break ;;
      esac
    done
    if [ -n "${_ra_bad}" ]; then
      _ra_out="${_ra_out}  · ASSERT 含絕對路徑或 '..'（禁 repo 外／路徑穿越）: ${_ra_bad}\n"
      continue
    fi
    # 目標路徑＝命令中第一個看起來像 repo 路徑的 token
    _ra_tgt="$(printf '%s' "${_ra_cmd}" | tr ' ' '\n' | grep -E '^[A-Za-z0-9_./-]+\.(sh|py)$' | head -1)"
    if [ -n "${_ra_tgt}" ] && [ ! -e "${_ra_tgt}" ]; then
      if [ "${TEMPLATE_CHECK_ALLOW_PENDING:-0}" != "1" ]; then
        _ra_out="${_ra_out}  · ASSERT 標的不存在且**未開放 pending**（預設拒絕）: ${_ra_tgt}\n"
        continue
      fi
      case " $(printf '%s' "${_ra_new}" | tr '\n' ' ') " in
        *" ${_ra_tgt} "*)
          echo "  · ASSERT pending（caller 已 opt-in 且標的列於本檔「新建：」）: ${_ra_tgt}"
          continue ;;
        *)
          _ra_out="${_ra_out}  · ASSERT 標的不存在且**未列於本檔「新建：」**⇒ 不得 pending: ${_ra_tgt}\n"
          continue ;;
      esac
    fi
    # 🔴 逐字 argv 執行，並**固定 PATH／清除注入型環境變數**
    #   〔codex 於 B5-STAMP-R3 REJECTED 並實證〕：白名單比對的是 **token 名**，
    #   解析卻走 PATH ⇒ 把同名 `bash` 置於 PATH 前端即可執行 repo 外程式，白名單被繞過。
    #   固定順序：系統目錄在前（`bash`/`grep`/`true` 必為系統版），
    #   repo venv 在後僅供 `pytest`；`REPO_ROOT` 由腳本位置導出，不取自環境。
    #   併清 `BASH_ENV`／`ENV`（bash 啟動時會 source）與 `*_PRELOAD`（動態載入注入）。
    # 🔴 T0 止血①：寫檔 hook 路徑只驗文法，不執行（見檔頭常數區之出生事故）
    # 🔴〔CODEX-R1-P1-02〕不得**靜默**跳過：文法與白名單都過、只是結果會錯的
    #   ASSERT（例如 `ASSERT false THEN rc=0`）在本路徑不再被判失。
    #   那是路 A 的實質語意損失，必須**大聲**印出來，不能看起來像驗過了。
    #   非致命（不進 _ra_out ⇒ 不改 rc）：致命會讓既有文件在寫檔當下全部鎖死。
    #   受影響行之集合由 tests/governance/test_gov_check_cheap_first.py 之
    #   test_executable_assert_lines_are_a_frozen_named_set 凍住 ⇒ 不會靜默增生。
    if [ "${TEMPLATE_CHECK_NO_EXEC:-0}" = "1" ]; then
      printf '  · ASSERT 未驗證（本路徑不執行任意命令，路 A）: %s\n' "${_ra_cmd}" >&2
      continue
    fi
    # 🔴 T0 止血②：逐行 timeout，逾時 fail-closed（判 FAIL，不略過）
    ( set -f; IFS=' 	'; set -- ${_ra_cmd}
      [ "$#" -gt 0 ] || exit 1
      PATH="/usr/bin:/bin:/usr/sbin:/sbin:${REPO_ROOT}/venv/bin"
      export PATH
      unset BASH_ENV ENV CDPATH LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH
      exec "$@" ) >/dev/null 2>&1 &
    _ra_pid=$!
    _ra_waited=0
    while [ "${_ra_waited}" -lt "${_ra_to}" ] && kill -0 "${_ra_pid}" 2>/dev/null; do
      sleep 1
      _ra_waited=$((_ra_waited + 1))
    done
    if kill -0 "${_ra_pid}" 2>/dev/null; then
      kill -TERM "${_ra_pid}" 2>/dev/null
      sleep 1
      kill -KILL "${_ra_pid}" 2>/dev/null
      wait "${_ra_pid}" 2>/dev/null
      _ra_out="${_ra_out}  · ASSERT 逾時 ${_ra_to}s ⇒ fail-closed（勿於 ASSERT 呼叫治理閘門腳本）: ${_ra_cmd}\n"
      continue
    fi
    wait "${_ra_pid}"
    _ra_rc=$?
    [ "${_ra_rc}" = "${_ra_exp}" ] || \
      _ra_out="${_ra_out}  · ASSERT rc 不符（期望 ${_ra_exp} 實得 ${_ra_rc}）: ${_ra_cmd}\n"
  done <<EOF
${_ra_live}
EOF
  [ -z "${_ra_out}" ] && return 0
  printf '%b' "${_ra_out}"
  return 1
}

# ---- 接線：只對 docs/*SPEC*.md｜docs/*TODO*.md 套用（handoffs/ 委員產出一律不套，Task 1.2 教訓）
#   TEMPLATE_CHECK_EXT_SCOPE=force 供測試強制啟用——它**只會擴大**受檢範圍，
#   不可能弱化任何既有檢查，故非逃生口。
_tc_rel="$(_lc_repo_rel "${file}")"
_tc_ext=0
case "${_tc_rel}" in
  docs/*SPEC*.md|docs/*TODO*.md) _tc_ext=1 ;;
esac
[ "${TEMPLATE_CHECK_EXT_SCOPE:-}" = "force" ] && _tc_ext=1
if [ "${_tc_ext}" -eq 1 ] && { [ "${kind}" = "spec" ] || [ "${kind}" = "todo" ]; }; then
  _tc_msg="$(_check_scope_claim "${file}")" || missing="${missing}${_tc_msg}\n"
  _tc_msg="$(_run_assert_lines "${file}")" || missing="${missing}${_tc_msg}\n"
  while IFS= read -r _tc_fn; do
    [ -n "${_tc_fn}" ] || continue
    _tc_name="$(printf '%s' "${_tc_fn}" | sed -e 's/^[[:blank:]]*函式：[[:space:]]*//' -e 's/[[:space:]].*$//' -e 's/`//g' -e 's/()$//')"
    [ -n "${_tc_name}" ] || continue
    _tc_hit=0
    for _tc_src in scripts/*.sh scripts/*.py; do
      [ -e "${_tc_src}" ] || continue
      if _func_exists "${_tc_name}" "${_tc_src}"; then _tc_hit=1; break; fi
    done
    [ "${_tc_hit}" -eq 1 ] || \
      missing="${missing}  · 宣告之函式不存在於 scripts/: ${_tc_name}\n"
  done <<EOF
$(_tc_live_lines "${file}" | grep -E '^[[:blank:]]*函式：')
EOF
fi

if [ -n "${missing}" ] || [ -n "${hollow}" ]; then
  echo "TEMPLATE FAIL (${kind}): ${file}"
  [ -n "${missing}" ] && { echo "【缺必填錨點】"; printf "%b" "${missing}"; }
  [ -n "${hollow}" ]  && { echo "【空殼/敷衍偵測】"; printf "%b" "${hollow}"; }
  result_tpl="RESULT_TEMPLATE.md"
  spec_tpl="SPEC_TEMPLATE.md"
  todo_tpl="TODO_GENERATION_PROMPT.md"
  tpl="${spec_tpl}"
  if [ "${kind}" = "todo" ]; then tpl="${todo_tpl}"; fi
  if [ "${kind}" = "result" ]; then tpl="${result_tpl}"; fi
  if [ "${kind}" = "dext" ]; then
    # dext 的範本不在 templates/，在凍結程序文件本身（canonical 單一真相源）
    echo "  → 依 docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.2「延伸檔必填」補齊結構與內容。"
    exit 1
  fi
  echo "  → 依 templates/${tpl} 補齊結構與內容。"
  exit 1
fi
echo "TEMPLATE PASS (${kind}): ${file} 含全部必填錨點，且無明顯空殼。"
