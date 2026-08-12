#!/usr/bin/env bash
# gen_fact_key_blocks.sh — 票 B-25 事實單一來源：生成器 ＋ 漂移檢查（Task 2.1）
#
# 模式：
#   （無參數）  將全部 fact-key 之 generated block 印到 stdout（決定性；供 sha 比對）
#   --check     重新生成並與宿主檔內既有區塊 diff；不一致 ⇒ rc≠0
#   --write     以重新生成的內容就地覆寫宿主檔內既有區塊（邊界標記須已存在）
#
# 環境變數：
#   GOVB1_FACTKEY_ROOT  宿主檔查找根目錄（預設 `.`）。供測試指向 fixture 目錄。
#                       只影響「去哪裡找宿主檔」，不影響註冊表位置。
#
# 註冊表＝與本腳本同目錄之 fact_keys.json；schema 定義寫在該檔 `_schema` 內（唯一定義處）。
#
# 決定性契約（缺一即 diff 恆紅 ⇒ 機制退化成噪音〔COMPOSER-R1-P2-03〕）：
#   · LC_ALL=C 固定 collation —— 禁依賴環境 locale
#     🔴 實測（2026-08-09，本機 macOS）：`a-y / B-x / _z` 三列
#        LC_ALL=C        → B-x _z a-y
#        LC_ALL=en_US.UTF-8 → _z a-y B-x
#        ⇒ 拿掉 LC_ALL=C 會使輸出隨環境改變，T-2.1-M1 據此可證偽。
#   · 全程 LF；不輸出 BOM；不含時間戳、不含任何隨執行時間或環境改變之欄位
#
# fail-closed 點（皆非靜默放行）：
#   註冊表缺失／非 JSON 物件／key 名不合法／缺 jq／缺 target／target 為絕對路徑或含 ..／
#   rows 型別不符／宿主檔不存在／邊界標記缺失或不成對／
#   columns 非法（空、含空字串、重複、含 | 或任何控制字元）／列長與 columns 欄數不符／
#   render 非 {tsv,table}／render=table 但缺 columns／儲存格含控制字元（table 另禁 |）
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REG="${SCRIPT_DIR}/fact_keys.json"

# 保留鍵字面集合寫死於此（非由註冊表自證；自證＝無檢查）
_FK_RESERVED='_schema'
# fact-key 名稱字元集合：限縮至此，故可安全嵌入 grep/sed 正則而無需跳脫
_FK_KEY_RE='^[a-z0-9][a-z0-9-]*$'
# render 模式封閉集合（寫死於此，非由註冊表自證）。未宣告者一律 tsv。
_FK_RENDER_MODES='tsv table'

_fk_die() { printf '%s\n' "$*" >&2; exit 1; }

_fk_preflight() {
  command -v jq >/dev/null 2>&1 \
    || _fk_die "gen_fact_key_blocks: 缺 jq → fail-closed"
  [ -f "${REG}" ] \
    || _fk_die "gen_fact_key_blocks: 缺註冊表 ${REG} → fail-closed"
  LC_ALL=C jq -e 'type == "object"' "${REG}" >/dev/null 2>&1 \
    || _fk_die "gen_fact_key_blocks: 註冊表 ${REG} 非合法 JSON 物件 → fail-closed"
}

_fk_raw_keys() { LC_ALL=C jq -r 'keys[]' "${REG}"; }

# 非保留鍵即 fact-key；名稱不合法 ⇒ 整體 fail-closed（不得只跳過該筆）
_fk_validate_keys() {
  _fkv_bad=""
  while IFS= read -r _fkv_k; do
    [ -n "${_fkv_k}" ] || continue
    case "${_fkv_k}" in "${_FK_RESERVED}") continue ;; esac
    printf '%s' "${_fkv_k}" | LC_ALL=C grep -qE "${_FK_KEY_RE}" \
      || _fkv_bad="${_fkv_bad}${_fkv_k}"$'\n'
  done < <(_fk_raw_keys)
  [ -z "${_fkv_bad}" ] || {
    printf 'gen_fact_key_blocks: fact-key 名稱不合法（須符 %s）→ fail-closed:\n%s' \
      "${_FK_KEY_RE}" "${_fkv_bad}" >&2
    return 1
  }
}

_fk_keys() {
  while IFS= read -r _fkk_k; do
    [ -n "${_fkk_k}" ] || continue
    case "${_fkk_k}" in "${_FK_RESERVED}") continue ;; esac
    printf '%s\n' "${_fkk_k}"
  done < <(_fk_raw_keys)
}

# 票 B-25 站 2.5 Task 1.1：一個 fact-key 可宣告 ≥1 個宿主檔。
#   `target` 型別 string ⇒ 單元素序列；array of string ⇒ 逐筆；其餘型別 fail-closed。
#   🔴 路徑檢查逐筆套用（不得只驗第一筆）；空陣列與重複路徑皆 fail-closed。
#   🔴 projection oracle：同一 key 之所有 target 共用**同一份** `_fk_gen_block` 輸出，
#      故各宿主區塊內容必逐位元組相同；任一宿主漂移即由 `_fk_check` 逐筆比對抓出。
_fk_targets() {   # $1=key -> stdout: repo 相對路徑，一行一筆
  _fkt_ty="$(LC_ALL=C jq -r --arg k "$1" '.[$k].target | type' "${REG}" 2>/dev/null)" || _fkt_ty=""
  case "${_fkt_ty}" in
    string)
      _fkt_list="$(LC_ALL=C jq -r --arg k "$1" '.[$k].target // empty' "${REG}")" || return 1 ;;
    array)
      LC_ALL=C jq -e --arg k "$1" '.[$k].target | all(.[]; type == "string")' \
        "${REG}" >/dev/null 2>&1 \
        || { echo "gen_fact_key_blocks: key ${1} 之 target 陣列含非字串元素 → fail-closed" >&2
             return 1; }
      _fkt_list="$(LC_ALL=C jq -r --arg k "$1" '.[$k].target[]' "${REG}")" || return 1 ;;
    *)
      echo "gen_fact_key_blocks: key ${1} 之 target 型別不符（須 string 或 array of string）→ fail-closed" >&2
      return 1 ;;
  esac
  [ -n "${_fkt_list}" ] || {
    echo "gen_fact_key_blocks: key ${1} 缺 target 或 target 為空陣列 → fail-closed" >&2; return 1; }
  # 重複路徑：同檔兩組標記語意未定義 ⇒ fail-closed
  _fkt_n="$(printf '%s\n' "${_fkt_list}" | LC_ALL=C wc -l | tr -d ' ')"
  _fkt_u="$(printf '%s\n' "${_fkt_list}" | LC_ALL=C sort -u | LC_ALL=C wc -l | tr -d ' ')"
  [ "${_fkt_n}" = "${_fkt_u}" ] || {
    echo "gen_fact_key_blocks: key ${1} 之 target 含重複路徑 → fail-closed" >&2; return 1; }
  # 🔴 逐筆套用路徑檢查
  _fkt_rc=0
  while IFS= read -r _fkt_t; do
    [ -n "${_fkt_t}" ] || continue
    case "${_fkt_t}" in
      /*)   echo "gen_fact_key_blocks: key ${1} 之 target 不得為絕對路徑：${_fkt_t}" >&2; _fkt_rc=1 ;;
      *..*) echo "gen_fact_key_blocks: key ${1} 之 target 不得含 ..：${_fkt_t}" >&2; _fkt_rc=1 ;;
    esac
  done <<EOF
${_fkt_list}
EOF
  [ "${_fkt_rc}" = "0" ] || return 1
  printf '%s\n' "${_fkt_list}"
}

_fk_validate_rows() {   # $1=key
  LC_ALL=C jq -e --arg k "$1" \
    '.[$k].rows | type == "array" and all(.[]; type == "array" and all(.[]; type == "string"))' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: key ${1} 之 rows 型別不符（須為字串陣列之陣列）→ fail-closed" >&2
         return 1; }
}

# 票 B-25「判準資料化」之前置（待辦清單 `WL-01`）：欄位宣告與表格投影。
#
# 出處：`x-consult-r12` J-1（codex＋composer 同判，證偽主委 assumed①）——
#   「`.rows[]|@tsv` 只有平面列，沒有〔現行／已廢〕欄」⇒ 表格型判準無法入註冊表。
#   該限制是「同 Task 內互斥判準偵測」與「改法段須有 FACT-RECEIPT」兩條檢查的唯一阻塞。
#
# 兩個選填欄位（皆為**加法**；未宣告者行為與擴充前逐位元組相同）：
#   columns  字串陣列。非空、元素非空、不重複、不含 `|`／tab／換行。
#            一經宣告，rows 每列長度須**恰等於**欄數 ⇒ 掉欄／多欄當場 fail-closed
#            （擴充前無此不變式：列長不一致會靜默產出參差的 TSV）。
#   render   "tsv"（預設）｜"table"（markdown 表格）。
#            "table" 須有 columns——無表頭的表格不是表格 ⇒ fail-closed。
#
# 🔴 兩種 render **共用同一個排序點**（`_fk_rows_tsv`）：
#   換 render 不得換順序，否則同一份資料在不同宿主呈現次序不同＝新的漂移源。
#   排序點只有一處亦是 T-2.1-M1 兩條 mutation 的錨點前提（錨點須唯一，見測試檔註解）。
_fk_render_of() {   # $1=key -> stdout: render 模式（未宣告 ⇒ tsv）
  LC_ALL=C jq -r --arg k "$1" '.[$k].render // "tsv"' "${REG}"
}

_fk_validate_shape() {   # $1=key；columns／render 之封閉驗證（全 fail-closed）
  _fksh_rc=0
  _fksh_mode="tsv"
  _fksh_rty="$(LC_ALL=C jq -r --arg k "$1" \
                 '.[$k] | if has("render") then (.render | type) else "absent" end' \
                 "${REG}" 2>/dev/null)" || _fksh_rty=""
  case "${_fksh_rty}" in
    absent) : ;;
    string)
      _fksh_mode="$(LC_ALL=C jq -r --arg k "$1" '.[$k].render' "${REG}")" || return 1
      case " ${_FK_RENDER_MODES} " in
        *" ${_fksh_mode} "*) : ;;
        *) echo "gen_fact_key_blocks: key ${1} 之 render='${_fksh_mode}' 不在 {${_FK_RENDER_MODES}} → fail-closed" >&2
           _fksh_rc=1; _fksh_mode="tsv" ;;
      esac ;;
    *)
      echo "gen_fact_key_blocks: key ${1} 之 render 型別不符（須字串）→ fail-closed" >&2
      _fksh_rc=1 ;;
  esac

  _fksh_cty="$(LC_ALL=C jq -r --arg k "$1" \
                 '.[$k] | if has("columns") then (.columns | type) else "absent" end' \
                 "${REG}" 2>/dev/null)" || _fksh_cty=""
  if [ "${_fksh_cty}" = "absent" ]; then
    [ "${_fksh_mode}" != "table" ] || {
      echo "gen_fact_key_blocks: key ${1} render=table 但未宣告 columns（無表頭）→ fail-closed" >&2
      _fksh_rc=1; }
  else
    # 🔴 禁字元用**封閉集合**（`|` ∪ 全部控制字元），不是列舉黑名單〔CODEX-R1-P1-01〕：
    #   初版只列 `| \t \n`，漏了 CR。表頭**不經 @tsv**（見 `_fk_gen_block` 的 columns 那兩行），
    #   raw CR 會把表頭拆成兩行 ⇒ 產出 malformed markdown；而 `--check` 比的是字串，
    #   宿主同樣壞掉即兩邊相符 ⇒ rc=0 靜默放行。codex 以 `columns:["a\rb","c"]` 實跑重現
    #   （emit rc=0、stdout hex 含 `7c20610d62207c`、check rc=0）。
    #   儲存格走 `@tsv` 會把 CR 轉義成字面 `\r` 故不受此害——**表頭與儲存格路徑不同**，
    #   這正是只補一處會漏另一處的原因，故兩處都改用同一個封閉集合。
    LC_ALL=C jq -e --arg k "$1" '
      .[$k].columns
      | type == "array"
        and length > 0
        and all(.[]; type == "string" and length > 0 and (test("[|[:cntrl:]]") | not))
        and (length == (unique | length))
    ' "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: key ${1} 之 columns 非法（須非空字串陣列；元素非空、不重複、不含 | 或任何控制字元）→ fail-closed" >&2
           _fksh_rc=1; }
    LC_ALL=C jq -e --arg k "$1" '
      (.[$k].columns | length) as $n | .[$k].rows | all(.[]; length == $n)
    ' "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: key ${1} 有列之欄數與 columns 宣告不符 → fail-closed" >&2
           _fksh_rc=1; }
  fi

  # 儲存格字元限制：同上改用封閉集合（全部控制字元）。tab／換行破壞 @tsv 的「一列一行」
  # 語義；其餘控制字元 @tsv 不轉義、會原樣進入產出。既有四 key 實測零命中，故非放寬。
  LC_ALL=C jq -e --arg k "$1" '.[$k].rows | all(.[][]; test("[[:cntrl:]]") | not)' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: key ${1} 之儲存格含控制字元（破壞逐列語義）→ fail-closed" >&2
         _fksh_rc=1; }
  if [ "${_fksh_mode}" = "table" ]; then
    LC_ALL=C jq -e --arg k "$1" '.[$k].rows | all(.[][]; test("[|]") | not)' \
      "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: key ${1} render=table 之儲存格含 |（會切碎表格）→ fail-closed" >&2
           _fksh_rc=1; }
  fi
  return "${_fksh_rc}"
}

# 🔴 唯一排序點。兩種 render 皆經此函式，故下一行的排序管線在本檔**只出現一次**——
#   T-2.1-M1a／M1b 以字串取代做 mutation 且只換第一處，出現兩次即打錯位置而空心。
#   🔴 本註解刻意**不複述**該管線的字面文字：複述本身就會變成第二處
#   （2026-08-12 WL-01 實際犯過一次，由 test_wl01_sort_anchor_stays_unique_in_generator 抓到）。
#   LC_ALL=C 為決定性支點（見檔頭實測）；拿掉即 T-2.1-M1 轉紅。
_fk_rows_tsv() {   # $1=key -> stdout: @tsv 後 LC_ALL=C 排序
  LC_ALL=C jq -r --arg k "$1" '.[$k].rows[] | @tsv' "${REG}" | LC_ALL=C sort
}

_fk_gen_block() {   # $1=key -> stdout（決定性）
  # 🔴 每一步都須 `|| return 1`〔CODEX-R1-P1-03〕：
  #   前版最後一行是 printf ⇒ **函式 rc 恆為 0**，jq／sort 失敗被吞掉。
  #   `--check` 又只比對字串，於是「生成失敗但輸出恰好相符」＝靜默通過。
  printf '<!-- BEGIN GENERATED: %s -->\n' "$1" || return 1
  _fkg_mode="$(_fk_render_of "$1")" || return 1
  if [ "${_fkg_mode}" = "table" ]; then
    LC_ALL=C jq -r --arg k "$1" '.[$k].columns | "| " + join(" | ") + " |"' "${REG}" || return 1
    LC_ALL=C jq -r --arg k "$1" '.[$k].columns | map("---") | "|" + join("|") + "|"' "${REG}" || return 1
    # 欄數已由 `_fk_validate_shape` 鎖成與 columns 相等；此處只做格式化，不再猜欄數
    _fk_rows_tsv "$1" \
      | LC_ALL=C awk -F'\t' '{ line = "|"; for (i = 1; i <= NF; i++) line = line " " $i " |"; print line }' \
      || return 1
  else
    _fk_rows_tsv "$1" || return 1
  fi
  printf '<!-- END GENERATED: %s -->\n' "$1" || return 1
}

_fk_root() { printf '%s\n' "${GOVB1_FACTKEY_ROOT:-.}"; }

# 回傳 0＝標記恰好成對；非 0＝缺失/重複（已印訊息，含檔名與 key）
_fk_markers_ok() {   # $1=key $2=宿主檔路徑 $3=顯示用相對路徑
  _fkm_nb="$(LC_ALL=C grep -c -- "^<!-- BEGIN GENERATED: ${1} -->$" "$2")" || _fkm_nb=0
  _fkm_ne="$(LC_ALL=C grep -c -- "^<!-- END GENERATED: ${1} -->$" "$2")" || _fkm_ne=0
  [ "${_fkm_nb}" = "1" ] && [ "${_fkm_ne}" = "1" ] && return 0
  echo "FACTKEY MARKER: ${1} in ${3}（BEGIN=${_fkm_nb} END=${_fkm_ne}，須各恰 1）→ fail-closed" >&2
  return 1
}

# 未登記之 generated block〔CODEX-R1-P1-02〕
# 病：宿主檔內可另貼一組 `<!-- BEGIN GENERATED: 別的key -->`，它長得像機械產物、
#     讀者會當成權威，但註冊表根本不知道它 ⇒ 永遠不會被比對。
# 範圍＝**已登記 target 之集合**（封閉、可由註冊表導出）。刻意不掃全庫：
#   那是啟發式，須附誤擋率 receipt 才可上線（`票 B-23` 同紀律）。
# 誠實邊界：生成器不知道的**其他檔**內的第三份副本仍擋不到（既有具名殘留）。
# 全部已登記 target 之去重集合（跨 key）。同一檔宿主兩個 key 時只掃一次，避免重複報。
_fk_all_targets() {
  _fka_keys="$(_fk_keys)" || return 1
  _fka_rc=0; _fka_out=""
  while IFS= read -r _fka_k; do
    [ -n "${_fka_k}" ] || continue
    _fka_t="$(_fk_targets "${_fka_k}")" || { _fka_rc=1; continue; }
    _fka_out="${_fka_out}${_fka_t}
"
  done <<EOF
${_fka_keys}
EOF
  [ "${_fka_rc}" = "0" ] || return 1
  printf '%s' "${_fka_out}" | LC_ALL=C sort -u
}

_fk_reject_unregistered_blocks() {
  _fkr_root="$(_fk_root)"; _fkr_rc=0
  _fkr_keys="$(_fk_keys)" || return 1
  _fkr_tgts="$(_fk_all_targets)" || return 1
  while IFS= read -r _fkr_tgt; do
    [ -n "${_fkr_tgt}" ] || continue
    _fkr_path="${_fkr_root}/${_fkr_tgt}"
    [ -f "${_fkr_path}" ] || continue      # 缺檔已由 _fk_check 具名報過，不重複
    while IFS= read -r _fkr_found; do
      [ -n "${_fkr_found}" ] || continue
      printf '%s\n' "${_fkr_keys}" | grep -qxF "${_fkr_found}" && continue
      echo "FACTKEY UNREGISTERED BLOCK: '${_fkr_found}' in ${_fkr_tgt}（不在 ${REG}）→ fail-closed" >&2
      _fkr_rc=1
    done <<EOF
$(LC_ALL=C sed -n 's/^<!-- BEGIN GENERATED: \(.*\) -->$/\1/p' "${_fkr_path}")
EOF
  done <<EOF
${_fkr_tgts}
EOF
  return "${_fkr_rc}"
}

# 票 B-25 站 2.5 Task 1.2：`_schema` 四項封閉集合宣告之驗證。
# 🔴 唯一語義（r5 CODEX-R5-P1-02）：
#   · 註冊表**無任何 fact-key** ⇒ 不套用本檢查（既有「空註冊表 rc=0」契約不變）
#   · 註冊表**有 ≥1 fact-key** ⇒ 四欄必須存在且合法，否則 fail-closed
# 不得刪 test_empty_registry_is_rc_zero_not_failure，也不得放寬 fail-closed。
_FK_SCHEMA_SETS='status_enum status_keys status_scope status_scope_grandfathered'

_fk_validate_schema_sets() {
  _fkss_keys="$(_fk_keys)" || return 1
  [ -n "${_fkss_keys}" ] || return 0        # 無 fact-key ⇒ 無事可做
  _fkss_rc=0
  for _fkss_f in ${_FK_SCHEMA_SETS}; do
    LC_ALL=C jq -e --arg f "${_fkss_f}" \
      '._schema[$f] | type == "array" and length > 0 and all(.[]; type == "string")' \
      "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: _schema.${_fkss_f} 缺席／非陣列／為空／含非字串 → fail-closed" >&2
           _fkss_rc=1; }
  done
  [ "${_fkss_rc}" = "0" ] || return 1
  # status_keys 所列 key 須為已註冊 fact-key（自證＝無檢查）
  while IFS= read -r _fkss_sk; do
    [ -n "${_fkss_sk}" ] || continue
    printf '%s\n' "${_fkss_keys}" | LC_ALL=C grep -qxF "${_fkss_sk}" || {
      echo "gen_fact_key_blocks: _schema.status_keys 含未註冊 key '${_fkss_sk}' → fail-closed" >&2
      _fkss_rc=1; }
  done <<EOF
$(LC_ALL=C jq -r '._schema.status_keys[]' "${REG}" 2>/dev/null)
EOF
  # status_scope 禁 wildcard（r3 CODEX-R3-P1-02：三種寫法得三種集合）
  while IFS= read -r _fkss_sc; do
    [ -n "${_fkss_sc}" ] || continue
    case "${_fkss_sc}" in
      *'*'*|*'?'*|*'['*)
        echo "gen_fact_key_blocks: _schema.status_scope 不得含 wildcard：${_fkss_sc} → fail-closed" >&2
        _fkss_rc=1 ;;
    esac
  done <<EOF
$(LC_ALL=C jq -r '._schema.status_scope[]' "${REG}" 2>/dev/null)
EOF
  return "${_fkss_rc}"
}

_fk_emit_all() {
  _fk_validate_keys || return 1
  # 判準 schema 之語意檢查在三條路徑都要跑（emit／--check／--write）——
  # 只掛在 --check 時，單獨刪 criteria_keys 於 emit 仍 rc=0〔WL-02 r2 自驗發現〕
  _fk_validate_criteria || return 1
  _fke_rc=0
  while IFS= read -r _fke_k; do
    [ -n "${_fke_k}" ] || continue
    _fk_validate_rows "${_fke_k}" || { _fke_rc=1; continue; }
    _fk_validate_shape "${_fke_k}" || { _fke_rc=1; continue; }
    _fk_gen_block "${_fke_k}" || _fke_rc=1
  done < <(_fk_keys)
  return "${_fke_rc}"
}

# 票 B-25 站 2.5 Task 2.1：手寫狀態偵測器。
#
# 範圍＝`_schema.status_scope` 宣告之 path/prefix 展開 **減去** `status_scope_grandfathered`。
# 🔴 列舉器必含未追蹤檔（r2 CODEX-R2-P1-01／COMPOSER-R2-P1-03 實跑證明 `git ls-files`
#    不含未追蹤路徑 ⇒ 首次 `git add` 前可手寫狀態而 --check 仍為 0）。
# 🔴 不得把 status_scope 字串原樣當 git pathspec（r3 CODEX-R3-P1-02：
#    `白話說明/第`→0 筆、`白話說明/第*`→4 筆、`白話說明/`→9 筆，三種寫法三種集合）
#    ⇒ 先列舉全樹，再在腳本內依 exact／directory-prefix 兩種編碼過濾。
# 🔴 非 git 樹 ⇒ fail-closed，不得靜默退回「只掃 target」。
_fk_scope_files() {   # stdout: 範圍內檔案（相對 root），一行一筆
  _fks_root="$(_fk_root)"
  git -C "${_fks_root}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "FACTKEY SCAN: ${_fks_root} 非 git 工作樹 ⇒ fail-closed（不得靜默退回只掃 target）" >&2
    return 1; }
  _fks_scope="$(LC_ALL=C jq -r '._schema.status_scope[]' "${REG}")" || return 1
  _fks_gf="$(LC_ALL=C jq -r '._schema.status_scope_grandfathered[]' "${REG}")" || return 1
  # 🔴 NUL-safe（r6 CODEX-R6-P1-03：不帶 -z 時，含換行之檔名會被逐行解析切碎而漏掃，
  #    codex 以 `docs/hidden<LF>name.md` 實跑得 rc=0 ⇒ 可構造之 fail-open）。
  #    先把路徑內的換行編碼成 \001，再把 NUL 轉成換行；用到路徑時解碼回來。
  #    順序不可顛倒（先轉 NUL 會使含換行的路徑碰撞）。
  _fks_all="$(git -C "${_fks_root}" -c core.quotePath=false \
                ls-files --cached --others --exclude-standard -z \
              | tr '\n' '\001' | tr '\0' '\n')" || return 1
  # 🔴 多行值經**檔案**餵入 awk，不走 -v：BSD awk 的 -v 值不接受換行
  #    （實測 macOS：`awk: newline in string ... at source line 1`）。此為平台事實，
  #    與 `_fk_write` 的 blkfile 同一坑；主委 2026-08-10 在本檔內再犯一次。
  _fks_sf="${TMPDIR:-/tmp}/.factkey-scope.$$"; _fks_gff="${TMPDIR:-/tmp}/.factkey-gf.$$"
  printf '%s\n' "${_fks_scope}" > "${_fks_sf}"
  printf '%s\n' "${_fks_gf}"    > "${_fks_gff}"
  printf '%s\n' "${_fks_all}" | LC_ALL=C awk -v sf="${_fks_sf}" -v gff="${_fks_gff}" '
    BEGIN {
      n = 0
      while ((getline line < sf) > 0) if (line != "") S[++n] = line
      close(sf)
      while ((getline line < gff) > 0) if (line != "") EX[line] = 1
      close(gff)
    }
    {
      if ($0 == "" || ($0 in EX)) next
      hit = 0
      for (i = 1; i <= n; i++) {
        p = S[i]; if (p == "") continue
        if (p ~ /\/$/) { if (index($0, p) == 1) hit = 1 }   # directory prefix（必以 / 結尾）
        else          { if ($0 == p)            hit = 1 }   # exact path
      }
      if (hit) print
    }'
  _fks_rc=$?
  rm -f "${_fks_sf}" "${_fks_gff}"
  return "${_fks_rc}"
}

# 識別碼集合＝`_schema.status_keys` 所列 key 之 rows 第 2 欄（封閉、可由註冊表導出）。
# 刻意排除 governance-execution-order：其第 2 欄為站名，併入會放大誤擋。
_fk_status_ids() {
  LC_ALL=C jq -r '. as $r | ._schema.status_keys[] as $k | $r[$k].rows[][1]' "${REG}" \
    | LC_ALL=C sort -u
}

_fk_reject_handwritten_status() {
  # 🔴 與 `_fk_validate_schema_sets` 同一語義（r5 CODEX-R5-P1-02）：
  #    無任何 fact-key ⇒ 無事可做、rc=0；既有「空註冊表 rc=0」契約不變。
  _fkh_keys="$(_fk_keys)" || return 1
  [ -n "${_fkh_keys}" ] || return 0
  _fkh_root="$(_fk_root)"
  _fkh_files="$(_fk_scope_files)" || return 1
  [ -n "${_fkh_files}" ] || return 0
  _fkh_rc=0
  # 非 regular file 一律 fail-closed（不遞迴、不略過）：一人遞迴另一人拒絕即集合不一致
  while IFS= read -r _fkh_f; do
    [ -n "${_fkh_f}" ] || continue
    _fkh_p="${_fkh_root}/$(printf '%s' "${_fkh_f}" | tr '\001' '\n')"
    if [ -L "${_fkh_p}" ]; then
      echo "FACTKEY SCAN: ${_fkh_f} 為 symlink ⇒ fail-closed" >&2; _fkh_rc=1; continue
    fi
    [ -f "${_fkh_p}" ] || {
      echo "FACTKEY SCAN: ${_fkh_f} 非 regular file（submodule／缺檔）⇒ fail-closed" >&2
      _fkh_rc=1; }
  done <<EOF
${_fkh_files}
EOF
  [ "${_fkh_rc}" = "0" ] || return 1

  # 🔴 同上：多行值走檔案，不走 -v（BSD awk 限制）
  _fkh_idf="${TMPDIR:-/tmp}/.factkey-ids.$$"; _fkh_ef="${TMPDIR:-/tmp}/.factkey-enum.$$"
  _fk_status_ids > "${_fkh_idf}" || { rm -f "${_fkh_idf}"; return 1; }
  LC_ALL=C jq -r '._schema.status_enum[]' "${REG}" > "${_fkh_ef}" || {
    rm -f "${_fkh_idf}" "${_fkh_ef}"; return 1; }
  _fkh_out="$(
    while IFS= read -r _fkh_f; do
      [ -n "${_fkh_f}" ] || continue
      _fkh_real="$(printf '%s' "${_fkh_f}" | tr '\001' '\n')"
      # 🔴 合法區塊 ＝「該 key 已註冊，且本檔為該 key 之 target」（r6 CODEX-R6-P1-02）。
      #    否則非宿主檔可貼一組**假的** BEGIN/END GENERATED 把手寫狀態藏進去，
      #    codex 以 `docs/other.md` 內假區塊＋`ZZID ✅` 實跑得 rc=0 ⇒ 可構造之 fail-open。
      _fkh_legal=""
      while IFS= read -r _fkh_k; do
        [ -n "${_fkh_k}" ] || continue
        _fk_targets "${_fkh_k}" 2>/dev/null | LC_ALL=C grep -qxF -- "${_fkh_real}" \
          && _fkh_legal="${_fkh_legal} ${_fkh_k}"
      done <<EOF3
${_fkh_keys}
EOF3
      # 🔴 `rel` 傳**編碼版**（換行仍為 \001）：BSD awk 的 -v 值不接受換行，
      #    傳解碼後路徑會得 `awk: newline in string`（主委 2026-08-10 第三次踩同一坑）。
      #    awk 內再轉成可讀標記 `<LF>`。
      LC_ALL=C awk -v idf="${_fkh_idf}" -v ef="${_fkh_ef}" -v rel="${_fkh_f}" \
                   -v legal="${_fkh_legal}" '
        # 🔴 邊界判定用「原始行 ＋ 絕對位置」，不得切片後重判
        #    （r4 CODEX-R4-P1-01：切片會丟失左側前文，B3RB3R 誤抽）
        function has_token(s, t,   off, rest, p, st, pre, post) {
          off = 0; rest = s
          while ((p = index(rest, t)) > 0) {
            st   = off + p
            pre  = (st == 1) ? "" : substr(s, st - 1, 1)
            post = substr(s, st + length(t), 1)
            if (pre !~ /[0-9A-Za-z_-]/ && post !~ /[0-9A-Za-z_-]/) return 1
            off  = st + length(t) - 1
            rest = substr(s, off + 1)
          }
          return 0
        }
        BEGIN {
          ni = 0; ne = 0
          while ((getline line < idf) > 0) if (line != "") I[++ni] = line
          close(idf)
          while ((getline line < ef) > 0) if (line != "") E[++ne] = line
          close(ef)
          nl = split(legal, L, " ")
          for (i = 1; i <= nl; i++) if (L[i] != "") LEGAL[L[i]] = 1
          gsub(/\001/, "<LF>", rel)
        }
        # 只有「已註冊且本檔為其 target」之 key 才算合法區塊；假區塊之標記行按一般行處理
        /^<!-- BEGIN GENERATED: .* -->$/ {
          k = $0
          sub(/^<!-- BEGIN GENERATED: /, "", k); sub(/ -->$/, "", k)
          if (k in LEGAL) { inblk = 1; next }
          printf "FACTKEY FAKE BLOCK: %s:%d 未登記或非本檔之生成標記 '\''%s'\'' → fail-closed\n", rel, FNR, k
          next
        }
        /^<!-- END GENERATED: .* -->$/ {
          k = $0
          sub(/^<!-- END GENERATED: /, "", k); sub(/ -->$/, "", k)
          if (k in LEGAL) { inblk = 0 }
          next
        }
        inblk { next }
        {
          ehit = ""
          for (j = 1; j <= ne; j++) if (E[j] != "" && index($0, E[j])) { ehit = E[j]; break }
          if (ehit == "") next
          ihit = ""
          for (j = 1; j <= ni; j++) if (I[j] != "" && has_token($0, I[j])) { ihit = I[j]; break }
          if (ihit == "") next
          printf "FACTKEY HANDWRITTEN STATUS: %s:%d 識別碼=%s 狀態=%s\n", rel, FNR, ihit, ehit
        }
      ' "${_fkh_root}/${_fkh_real}"
    done <<EOF2
${_fkh_files}
EOF2
  )" || { rm -f "${_fkh_idf}" "${_fkh_ef}"; return 1; }
  rm -f "${_fkh_idf}" "${_fkh_ef}"
  [ -z "${_fkh_out}" ] || {
    printf '%s\n' "${_fkh_out}" >&2
    echo "FACTKEY: 區塊外手寫狀態／假生成標記（改資料檔＋--write，或改為指向區塊之指標）→ fail-closed" >&2
    return 1; }
  return 0
}

# ==========================================================================
# WL-02（票 B-25 判準資料化）— 判準表之三道檢查
#
# 設計出處：`handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md`（三家 consult）。
# 主委原提案的三處落法被逐一推翻並改寫，摘要：
#   · 掃散文抽「條件→期望」：實測零訊號（封閉抽取 146 配對、三種分組衝突皆 0）⇒ **不做**。
#   · membership 用「有生成區塊即進管制」：不封閉——未登記檔可貼假區塊且根本不被掃
#     〔CODEX-R1-P1-02〕⇒ 改為**只認註冊表登記之 target**。
#   · 禁寫 pattern 用 `rc` 字面：可被同義寫法繞過，且 docs/ 內已存在該用法
#     〔COMPOSER-R1-P1-01／GROK-R1-P1-02〕⇒ 改為**封閉白名單**。
#
# 🔴 具名殘留（三家一致，**不得宣稱互斥判準已封死**）：
#   不同條件字串描述同一物理事件時鍵不相等 ⇒ 衝突偵測靜默放行。出生事故那型仍靠人。
#   完整殘留清單見 docs/GOV_CRITERIA_REGISTRY.md。
#
# 期望結束狀態之陳述形態：**封閉白名單**（擴充須改本行，非無限往黑名單加）。
#
# 🔴 涵蓋集合是**實測導出**，不是想像列舉〔票 B-23 同紀律〕。
#   r2 三家各自掃 docs/ 證偽了主委「六種足以涵蓋實務」之 assumed：
#   `CODEX-R2-P1-01`（`rc 由 0 變為非 0`）／`COMPOSER-R2-P1-01`（`→ exit N`、`退出碼 N`）／
#   `GROK-R2-P1-01`（`Exit code:` 類 ≥58 行、`退出碼` 4 行、`結束碼` 1 行、`非零退出` 1 行）。
#   下列集合即依該三份掃描結果補齊。
#
# 🔴 **具名殘留（誠實邊界，不得宣稱已封閉實務同義寫法）**：
#   本白名單只涵蓋下列具名形態。**關係型／轉換型**陳述（如「最終結束狀態與第一份一致」、
#   「由通過變為不通過」）刻意**不**納入——那需要理解語意，一納入就變成無限黑名單。
#   該類仍靠 review。見 docs/GOV_CRITERIA_REGISTRY.md 殘留 6。
#
# 涵蓋形態（與 _FK_RC_CLAIM_FORMS 一一對應，測試以集合相等鎖死）：
#   rc 後接 = == 不等號 != : 是 為 ／ rc 不變 ／ returncode 後接 = == != 不等號 ／
#   exit code（不分大小寫）／exit 數字 ／ 退出碼 ／ 結束碼 ／ 非零退出
_FK_RC_CLAIM_RES='rc[[:space:]]*(=|==|≠|!=|:|是|為)|rc[[:space:]]*不變|returncode[[:space:]]*(=|==|≠|!=)|[Ee]xit[[:space:]]*[Cc]ode|exit[[:space:]]+[0-9]+|退出碼|結束碼|非零退出'
# 供測試以集合相等鎖死涵蓋面（新增形態須同時改兩處，否則測試轉紅）
_FK_RC_CLAIM_FORMS='rc-op rc-unchanged returncode-op exit-code exit-n exitcode-zh endcode-zh nonzero-zh'

_fk_criteria_keys() { LC_ALL=C jq -r '._schema.criteria_keys[]? // empty' "${REG}"; }

# 角色→欄索引。以 columns 名稱查位置，不寫死索引〔可換欄序而不改碼〕。
_fk_role_idx() {   # $1=key $2=role -> stdout: 0-based 欄索引；找不到回非 0
  LC_ALL=C jq -er --arg k "$1" --arg r "$2" '
    (._schema.criteria_column_roles[$r]) as $name
    | if $name == null then error("role-undeclared")
      else (.[$k].columns | index($name)) end
    | if . == null then error("column-missing") else . end
  ' "${REG}" 2>/dev/null
}

# 🔴 判準 schema 是**一整組**，不得單獨刪其中一項〔CODEX-R2-P1-02〕：
#   原版以「有沒有 criteria_keys」決定要不要跑三道檢查 ⇒ **單獨刪掉 criteria_keys 即靜默停用**，
#   codex 實跑得 rc=0。修法＝四欄任一存在即四欄全需存在且合法（整組刪除＝該註冊表宣稱無判準，
#   由延伸檔集合相等測試 test_registry_key_set_equals_amendment_declaration 承接）。
_FK_CRITERIA_SCHEMA_FIELDS='criteria_keys criteria_status_enum criteria_column_roles criteria_live_status'

_fk_criteria_schema_present() {   # 0＝至少一欄存在
  for _fkcp_f in ${_FK_CRITERIA_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkcp_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 && return 0
  done
  return 1
}

_fk_validate_criteria() {   # 判準表語意檢查（狀態列舉封閉 ＋ 同範圍同條件不得相異期望）
  _fk_criteria_schema_present || return 0        # 整組缺席＝無判準，合法
  _fkvc_rc=0
  for _fkvc_f in ${_FK_CRITERIA_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkvc_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: _schema 已宣告部分判準欄，但缺 ${_fkvc_f} → fail-closed（判準 schema 為一整組，不得單獨刪）" >&2
           _fkvc_rc=1; }
  done
  [ "${_fkvc_rc}" = "0" ] || return 1
  _fkvc_keys="$(_fk_criteria_keys)" || return 1
  [ -n "${_fkvc_keys}" ] || {
    echo "gen_fact_key_blocks: _schema.criteria_keys 為空 → fail-closed（空清單會使三道判準檢查全部靜默停用）" >&2
    return 1; }
  LC_ALL=C jq -e '._schema.criteria_status_enum
                  | type == "array" and length > 0 and all(.[]; type == "string")' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: _schema.criteria_status_enum 非法 → fail-closed" >&2
         return 1; }
  # 🔴 「現行」以**具名欄位**宣告，不以 enum 的位置承載語義〔GROK-R2-P2-01／CODEX-R2-P1-02〕：
  #    原版取 enum[0]，把 enum 重排即只對「已廢」列做互斥檢查，現行互斥靜默放行。
  _fkvc_live="$(LC_ALL=C jq -r '._schema.criteria_live_status // empty' "${REG}")"
  [ -n "${_fkvc_live}" ] || {
    echo "gen_fact_key_blocks: _schema.criteria_live_status 缺席或為空 → fail-closed" >&2
    return 1; }
  LC_ALL=C jq -e --arg l "${_fkvc_live}" '._schema.criteria_status_enum | index($l) != null' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: criteria_live_status='${_fkvc_live}' 不在 criteria_status_enum 內 → fail-closed" >&2
         return 1; }
  while IFS= read -r _fkvc_k; do
    [ -n "${_fkvc_k}" ] || continue
    printf '%s\n' "$(_fk_keys)" | LC_ALL=C grep -qxF "${_fkvc_k}" || {
      echo "gen_fact_key_blocks: criteria_keys 含未註冊 key '${_fkvc_k}' → fail-closed" >&2
      _fkvc_rc=1; continue; }
    _fkvc_bad=""
    for _fkvc_role in id scope condition expect status oracle; do
      _fk_role_idx "${_fkvc_k}" "${_fkvc_role}" >/dev/null 2>&1 \
        || _fkvc_bad="${_fkvc_bad} ${_fkvc_role}"
    done
    [ -z "${_fkvc_bad}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvc_k} 缺角色欄（criteria_column_roles 未宣告或 columns 無該欄）:${_fkvc_bad} → fail-closed" >&2
      _fkvc_rc=1; continue; }
    _fkvc_si="$(_fk_role_idx "${_fkvc_k}" status)" || { _fkvc_rc=1; continue; }
    # ① 狀態列舉封閉：未知值 fail-closed〔CODEX-R1-P1-03〕
    # 🔴 `"${REG}"` 之後**不得**接同一行的排序管線：那串是 T-2.1-M1a／M1b 的 mutation 錨點，
    #    多一處就會讓那兩條打到這裡而非生成排序（空心）。既有 `_fk_status_ids` 亦用換行寫法。
    #    2026-08-13 WL-02 施工時再犯一次，由 test_wl01_sort_anchor_stays_unique_in_generator 抓到。
    _fkvc_unknown="$(LC_ALL=C jq -r --arg k "${_fkvc_k}" --argjson si "${_fkvc_si}" '
      (._schema.criteria_status_enum) as $e
      | .[$k].rows[] | select((.[$si] | IN($e[]) | not)) | .[$si]' "${REG}" \
      | LC_ALL=C sort -u)"
    [ -z "${_fkvc_unknown}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvc_k} 之狀態值不在 criteria_status_enum 內 → fail-closed:" >&2
      printf '%s\n' "${_fkvc_unknown}" | sed 's/^/    /' >&2
      _fkvc_rc=1; }
    # ② 同適用範圍同條件不得有相異期望（只看現行者；已廢列刻意不參與）
    _fkvc_sci="$(_fk_role_idx "${_fkvc_k}" scope)" || { _fkvc_rc=1; continue; }
    _fkvc_ci="$(_fk_role_idx "${_fkvc_k}" condition)" || { _fkvc_rc=1; continue; }
    _fkvc_ei="$(_fk_role_idx "${_fkvc_k}" expect)" || { _fkvc_rc=1; continue; }
    _fkvc_conf="$(LC_ALL=C jq -r \
      --arg k "${_fkvc_k}" --argjson sci "${_fkvc_sci}" --argjson ci "${_fkvc_ci}" \
      --argjson ei "${_fkvc_ei}" --argjson si "${_fkvc_si}" --arg live "${_fkvc_live}" '
      [ .[$k].rows[] | select(.[$si] == $live) ]
      | group_by([.[$sci], .[$ci]])
      | map(select((map(.[$ei]) | unique | length) > 1))
      | .[] | "  \(.[0][$sci]) ／ \(.[0][$ci]) ⇒ 期望值 " + (map(.[$ei]) | unique | join("、"))
    ' "${REG}")" || { _fkvc_rc=1; continue; }
    [ -z "${_fkvc_conf}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvc_k} 有互斥判準（同適用範圍同條件、狀態為現行、期望相異）→ fail-closed:" >&2
      printf '%s\n' "${_fkvc_conf}" >&2
      _fkvc_rc=1; }
  done <<EOF
${_fkvc_keys}
EOF
  return "${_fkvc_rc}"
}

# ③ 判準宿主之生成區塊外不得陳述期望結束狀態。
#   範圍＝**只有** criteria key 之 target（membership 靠登記，不靠有沒有區塊）。
#   豁免＝該檔**全部**合法生成區塊，非只判準區塊〔COMPOSER-R1-P1-03：
#   多 key 宿主只豁免判準區塊會誤擋並存的事實表〕。
_fk_reject_rc_claims_outside_blocks() {
  _fkrr_keys="$(_fk_criteria_keys)" || return 1
  [ -n "${_fkrr_keys}" ] || return 0
  _fkrr_root="$(_fk_root)"; _fkrr_rc=0
  _fkrr_all="$(_fk_keys)" || return 1
  while IFS= read -r _fkrr_k; do
    [ -n "${_fkrr_k}" ] || continue
    _fkrr_tgts="$(_fk_targets "${_fkrr_k}")" || { _fkrr_rc=1; continue; }
    while IFS= read -r _fkrr_t; do
      [ -n "${_fkrr_t}" ] || continue
      _fkrr_p="${_fkrr_root}/${_fkrr_t}"
      [ -f "${_fkrr_p}" ] || continue        # 缺檔已由 _fk_check 具名報過
      _fkrr_legal=""
      while IFS= read -r _fkrr_lk; do
        [ -n "${_fkrr_lk}" ] || continue
        _fk_targets "${_fkrr_lk}" 2>/dev/null | LC_ALL=C grep -qxF -- "${_fkrr_t}" \
          && _fkrr_legal="${_fkrr_legal} ${_fkrr_lk}"
      done <<EOF2
${_fkrr_all}
EOF2
      _fkrr_hit="$(LC_ALL=C awk -v legal="${_fkrr_legal}" -v res="${_FK_RC_CLAIM_RES}" -v rel="${_fkrr_t}" '
        BEGIN { nl = split(legal, L, " "); for (i = 1; i <= nl; i++) if (L[i] != "") LEGAL[L[i]] = 1 }
        /^<!-- BEGIN GENERATED: .* -->$/ {
          k = $0; sub(/^<!-- BEGIN GENERATED: /, "", k); sub(/ -->$/, "", k)
          if (k in LEGAL) { inblk = 1 }
          next }
        /^<!-- END GENERATED: .* -->$/ {
          k = $0; sub(/^<!-- END GENERATED: /, "", k); sub(/ -->$/, "", k)
          if (k in LEGAL) { inblk = 0 }
          next }
        inblk { next }
        $0 ~ res { printf "  %s:%d %s\n", rel, FNR, $0 }
      ' "${_fkrr_p}")"
      [ -z "${_fkrr_hit}" ] || {
        echo "gen_fact_key_blocks: 判準宿主 ${_fkrr_t} 於生成區塊外陳述期望結束狀態（改寫為判準 ID 指標）→ fail-closed:" >&2
        printf '%s\n' "${_fkrr_hit}" >&2
        _fkrr_rc=1; }
    done <<EOF
${_fkrr_tgts}
EOF
  done <<EOF3
${_fkrr_keys}
EOF3
  return "${_fkrr_rc}"
}

_fk_check() {
  _fk_validate_keys || return 1
  _fk_validate_schema_sets || return 1
  _fkc_root="$(_fk_root)"; _fkc_rc=0
  while IFS= read -r _fkc_k; do
    [ -n "${_fkc_k}" ] || continue
    _fk_validate_rows "${_fkc_k}" || { _fkc_rc=1; continue; }
    _fk_validate_shape "${_fkc_k}" || { _fkc_rc=1; continue; }
    _fkc_tgts="$(_fk_targets "${_fkc_k}")" || { _fkc_rc=1; continue; }
    # 🔴 生成結果先落變數並**驗 rc**，不得直接塞進 `[ = "$(...)" ]`〔CODEX-R1-P1-03〕：
    #   命令替換內的 rc 會被丟掉 ⇒ 生成失敗卻只比字串＝靜默通過。
    # 🔴 projection oracle：**只生成一次**，對每個 target 比對同一份內容
    #   ⇒ 兩宿主各自自洽但彼此不同時，必有一方 DRIFT。
    _fkc_want="$(_fk_gen_block "${_fkc_k}")" || {
      echo "FACTKEY GEN FAILED: ${_fkc_k}（生成器自身失敗，未與宿主檔比對）→ fail-closed" >&2
      _fkc_rc=1; continue; }
    while IFS= read -r _fkc_tgt; do
      [ -n "${_fkc_tgt}" ] || continue
      _fkc_path="${_fkc_root}/${_fkc_tgt}"
      [ -f "${_fkc_path}" ] || {
        echo "FACTKEY MISSING TARGET: ${_fkc_k} → ${_fkc_path} → fail-closed" >&2
        _fkc_rc=1; continue; }
      _fk_markers_ok "${_fkc_k}" "${_fkc_path}" "${_fkc_tgt}" || { _fkc_rc=1; continue; }
      _fkc_cur="$(sed -n "/^<!-- BEGIN GENERATED: ${_fkc_k} -->$/,/^<!-- END GENERATED: ${_fkc_k} -->$/p" \
                    "${_fkc_path}")"
      [ "${_fkc_cur}" = "${_fkc_want}" ] || {
        echo "FACTKEY DRIFT: ${_fkc_k} in ${_fkc_tgt}（宿主檔與 ${REG} 不一致；跑 --write 重生成）" >&2
        _fkc_rc=1; }
    done <<EOF
${_fkc_tgts}
EOF
  done < <(_fk_keys)
  # 未登記之 generated block 一律拒〔CODEX-R1-P1-02〕
  _fk_reject_unregistered_blocks || _fkc_rc=1
  # 生成區塊外之手寫狀態一律拒（票 B-25 站 2.5 Task 2.1）
  _fk_reject_handwritten_status || _fkc_rc=1
  # 判準表語意 ＋ 判準宿主之區塊外期望陳述（WL-02）
  _fk_validate_criteria || _fkc_rc=1
  _fk_reject_rc_claims_outside_blocks || _fkc_rc=1
  return "${_fkc_rc}"
}

_fk_write() {
  _fk_validate_keys || return 1
  _fk_validate_schema_sets || return 1
  _fk_validate_criteria || return 1
  _fkw_root="$(_fk_root)"; _fkw_rc=0
  while IFS= read -r _fkw_k; do
    [ -n "${_fkw_k}" ] || continue
    _fk_validate_rows "${_fkw_k}" || { _fkw_rc=1; continue; }
    _fk_validate_shape "${_fkw_k}" || { _fkw_rc=1; continue; }
    _fkw_tgts="$(_fk_targets "${_fkw_k}")" || { _fkw_rc=1; continue; }
    while IFS= read -r _fkw_tgt; do
    [ -n "${_fkw_tgt}" ] || continue
    _fkw_path="${_fkw_root}/${_fkw_tgt}"
    [ -f "${_fkw_path}" ] || {
      echo "FACTKEY MISSING TARGET: ${_fkw_k} → ${_fkw_path} → fail-closed" >&2
      _fkw_rc=1; continue; }
    # 🔴 --write 不會憑空建立標記：宿主檔須先由人放置一組空的 BEGIN/END。
    #    理由＝避免生成器對任意文件做位置不明的追加寫入。
    _fk_markers_ok "${_fkw_k}" "${_fkw_path}" "${_fkw_tgt}" || { _fkw_rc=1; continue; }
    # 🔴 區塊經檔案餵入 awk，不走 -v：BSD awk 的 -v 值不接受換行
    #    （實測 macOS：awk: newline in string ...）。此為平台事實，勿改回 -v。
    _fkw_blkf="${_fkw_path}.factkey-blk.$$"
    _fk_gen_block "${_fkw_k}" > "${_fkw_blkf}" || {
      rm -f "${_fkw_blkf}"; _fkw_rc=1; continue; }
    _fkw_tmp="${_fkw_path}.factkey.$$"
    LC_ALL=C awk \
      -v b="<!-- BEGIN GENERATED: ${_fkw_k} -->" \
      -v e="<!-- END GENERATED: ${_fkw_k} -->" \
      -v blkfile="${_fkw_blkf}" '
        $0 == b { while ((getline line < blkfile) > 0) print line; close(blkfile); skip = 1; next }
        skip && $0 == e { skip = 0; next }
        skip { next }
        { print }
      ' "${_fkw_path}" > "${_fkw_tmp}" \
      && mv "${_fkw_tmp}" "${_fkw_path}" \
      || { echo "gen_fact_key_blocks: 寫入失敗 ${_fkw_path}" >&2
           rm -f "${_fkw_tmp}" "${_fkw_blkf}"; _fkw_rc=1; continue; }
    rm -f "${_fkw_blkf}"
    echo "FACTKEY WROTE: ${_fkw_k} → ${_fkw_tgt}"
    done <<EOF
${_fkw_tgts}
EOF
  done < <(_fk_keys)
  return "${_fkw_rc}"
}

_fk_preflight

# 多餘參數 fail-closed：`--check --write` 這種寫法不得被靜默當成 --check
[ "$#" -le 1 ] || {
  echo "gen_fact_key_blocks: 只接受 0 或 1 個參數（收到 $#）→ fail-closed" >&2
  exit 2
}

case "${1-}" in
  "")        _fk_emit_all; exit $? ;;
  --check)   _fk_check;    exit $? ;;
  --write)   _fk_write;    exit $? ;;
  -h|--help)
    sed -n '2,20p' "${BASH_SOURCE[0]}"
    exit 0 ;;
  *)
    echo "gen_fact_key_blocks: 未知參數 '${1}'（可用：--check｜--write｜--help）→ fail-closed" >&2
    exit 2 ;;
esac
