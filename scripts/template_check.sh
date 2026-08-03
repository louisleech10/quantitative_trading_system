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
