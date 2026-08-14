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

# 🔴 jq 的 rc **不得丟棄**〔r2 三家皆觀察到之偶發紅，主委實驗定案根因〕：
#   原版兩處以 `< <(_fk_raw_keys)` 讀取，process substitution 的 rc 拿不到 ⇒
#   jq 偶發失敗（資源／fork 壓力）被靜默當成「註冊表沒有任何 fact-key」。
#   後果**兩個方向都有**：
#     · `_fk_validate_criteria`／`_fk_validate_mechanism` ⇒ 所有 key 被判「未註冊」＝假紅
#       （三家看到的正是這兩行訊息；主委以 `_fk_raw_keys(){ return 1; }` 實驗完全重現）
#     · `_fk_validate_schema_sets`／`_fk_reject_handwritten_status` 的「無 fact-key ⇒ rc=0」
#       語意 ⇒ **靜默放行＝假綠**。同一個 bug 在不同路徑分別造成假紅與假綠。
#   ⇒ 一律先落變數驗 rc。空輸出（真的空註冊表）仍合法，只有 rc≠0 才 fail-closed。
_fk_raw_keys() { LC_ALL=C jq -r 'keys[]' "${REG}"; }

_fk_raw_keys_checked() {   # stdout: 原始 key 清單；jq 非零 ⇒ 印訊息並回非 0
  _fkrk_out="$(_fk_raw_keys)" || {
    echo "gen_fact_key_blocks: 讀取 fact-key 清單失敗（jq 非零）→ fail-closed（不得當成『沒有任何 fact-key』）" >&2
    return 1
  }
  printf '%s\n' "${_fkrk_out}"
}

# 非保留鍵即 fact-key；名稱不合法 ⇒ 整體 fail-closed（不得只跳過該筆）
_fk_validate_keys() {
  _fkv_bad=""
  _fkv_raw="$(_fk_raw_keys_checked)" || return 1
  while IFS= read -r _fkv_k; do
    [ -n "${_fkv_k}" ] || continue
    case "${_fkv_k}" in "${_FK_RESERVED}") continue ;; esac
    printf '%s' "${_fkv_k}" | LC_ALL=C grep -qE "${_FK_KEY_RE}" \
      || _fkv_bad="${_fkv_bad}${_fkv_k}"$'\n'
  done <<EOF
${_fkv_raw}
EOF
  [ -z "${_fkv_bad}" ] || {
    printf 'gen_fact_key_blocks: fact-key 名稱不合法（須符 %s）→ fail-closed:\n%s' \
      "${_FK_KEY_RE}" "${_fkv_bad}" >&2
    return 1
  }
}

_fk_keys() {
  _fkk_raw="$(_fk_raw_keys_checked)" || return 1
  while IFS= read -r _fkk_k; do
    [ -n "${_fkk_k}" ] || continue
    case "${_fkk_k}" in "${_FK_RESERVED}") continue ;; esac
    printf '%s\n' "${_fkk_k}"
  done <<EOF
${_fkk_raw}
EOF
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
  # 判準／機制 schema 之語意檢查在三條路徑都要跑（emit／--check／--write）——
  # 只掛在 --check 時，單獨刪 criteria_keys 於 emit 仍 rc=0〔WL-02 r2 自驗發現〕。
  # 🔴「檢查只掛在其中一條路徑上」是本 epic 反覆出現的形態（一天內四個位置），
  #    新增任何檢查前先問「同一種輸入有沒有第二條處理路徑」。
  _fk_validate_criteria || return 1
  _fk_validate_mechanism || return 1
  _fk_validate_enforcement || return 1
  _fke_rc=0
  # 🔴 不用 `< <(_fk_keys)`：process substitution 的 rc 拿不到（見 _fk_raw_keys_checked 註解）
  _fke_keys="$(_fk_keys)" || return 1
  while IFS= read -r _fke_k; do
    [ -n "${_fke_k}" ] || continue
    _fk_validate_rows "${_fke_k}" || { _fke_rc=1; continue; }
    _fk_validate_shape "${_fke_k}" || { _fke_rc=1; continue; }
    _fk_gen_block "${_fke_k}" || _fke_rc=1
  done <<EOF
${_fke_keys}
EOF
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
# 實作已抽為 `_fk_role_idx_of`（WL-03 起機制表共用同一支）；本函式維持既有呼叫介面。
_fk_role_idx() { _fk_role_idx_of "$1" "$2" criteria_column_roles; }

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
  _fkvc_all="$(_fk_keys)" || return 1        # 🔴 迴圈外取一次並驗 rc（原本每圈重跑且吞 rc）
  while IFS= read -r _fkvc_k; do
    [ -n "${_fkvc_k}" ] || continue
    printf '%s\n' "${_fkvc_all}" | LC_ALL=C grep -qxF "${_fkvc_k}" || {
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

# ==========================================================================
# WL-03（票 B-25 機制證據登記）— 機制表資料列驗證 ＋ opt-in 宿主之改法子樹掃描
#
# 設計出處：`handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md`（三家 consult）。
# 主委原提案「掃改法段抽反引號 span，首 token 像可執行檔即要求 FACT-RECEIPT」
# 被三家各自實測否決（誤擋率 80–93%；誤擋物幾乎全是文件路徑、finding ID、旗標、
# 驗證指令）⇒ 本落法**不掃散文**，receipt／assumed 只對**登記表的資料列**驗證。
#
# 🔴 三處關鍵修正（皆由實測推翻主委 assumed 而來，勿改回）：
#   ① token 用**字面封閉表**，不用 PATH 探測——本機 `setsid` 不在 PATH
#      〔GROK-R1-P1-03／CODEX-R1-P1-03 各自實跑 PATH 查詢得非零〕，
#      以「可執行檔名」做候選反而會**漏掉出生事故本身**。
#      🔴 本註解刻意**不寫出**任何 PATH 查詢指令的字面——
#      test_wl03_token_matching_is_literal_table_not_path_probe 掃的是本區段全文，
#      連註解裡的字面都算命中（施工當下即被自己的測試抓到一次）。
#   ② 子樹起點釘死 `- 改法`，**禁全檔搜「改法」二字**〔COMPOSER-R1-P0-01〕：
#      本庫 `^#+.*改法` 標題僅 3 個（掃標題＝零訊號），`- 改法` 子彈列才可定位。
#      子樹須涵蓋**續行**——只比對「同行含改法」會漏掉續行上的機制〔GROK-R1-P1-03〕。
#   ③ 宿主 membership 靠**顯式 opt-in 清單**，不靠檔名樣式〔CODEX-R1-P1-02〕：
#      「凡含 FACT-RECEIPT」回掃 53 檔＝溯及既往；「凡新建 GOV*」＝未封閉 glob。
#
# 🔴 誠實邊界（必須連同交付物一起宣告，否則就是「做了一個看起來有在防的東西」）：
#   現樹訊號**近零**——五個 opt-in 宿主之改法子樹平台 token 命中＝0（施工前實測）。
#   價值在**面向未來**：日後於這些宿主寫入未驗機制時當場轉紅。
#   本規則**不清理**歷史內容，也**不對未登記檔案**有任何攔截力（具名殘留）。
_FK_MECHANISM_SCHEMA_FIELDS='mechanism_keys mechanism_status_enum mechanism_live_status mechanism_column_roles mechanism_scope mechanism_tokens'

# 證據欄封閉格式（前綴集合寫死於此，非由註冊表自證）：
#   receipt:<repo 相對路徑>   該檔須實際存在 ⇒ 「宣稱實跑但沒有東西可查」當場紅
#   assumed:<非空理由>        顯式未驗標記；允許，但可由生成區塊機械盤點
_FK_EVIDENCE_FORMS='receipt assumed'

# 🔴 receipt 路徑相對 `_fk_root()`，**即正在驗的那棵樹**〔CODEX-R1-P1-03〕。
#   初版讓它相對生成器所在的 repo（`SCRIPT_DIR/..`），理由是遷就 fixture ——**那是錯的**：
#   `GOVB1_FACTKEY_ROOT` 指向別的根時，receipt 在該根缺失、卻被生成器自身 repo 的同名檔
#   遮蔽 ⇒ codex 以 decoy 實跑得 rc=0。同一種輸入走兩個 root，正是本 epic 反覆出現的形態。
#   代價＝fixture 須自備 receipt 檔（已補），這是應該的：fixture 就該代表一棵完整的樹。

_fk_mechanism_keys() { LC_ALL=C jq -r '._schema.mechanism_keys[]? // empty' "${REG}"; }

# 角色→欄索引（通用）。以 columns 名稱查位置，不寫死索引。
#   $3＝`_schema` 內的角色對應表欄名（criteria_column_roles／mechanism_column_roles）
_fk_role_idx_of() {   # $1=key $2=role $3=roles欄名 -> stdout: 0-based 欄索引
  LC_ALL=C jq -er --arg k "$1" --arg r "$2" --arg rf "$3" '
    (._schema[$rf][$r]) as $name
    | if $name == null then error("role-undeclared")
      else (.[$k].columns | index($name)) end
    | if . == null then error("column-missing") else . end
  ' "${REG}" 2>/dev/null
}

_fk_mech_role_idx() { _fk_role_idx_of "$1" "$2" mechanism_column_roles; }

_fk_mechanism_schema_present() {   # 0＝至少一欄存在
  for _fkmp_f in ${_FK_MECHANISM_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkmp_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 && return 0
  done
  return 1
}

# 已登記且狀態為現行之 token 集合（供宿主掃描比對）
_fk_registered_tokens() {
  _fkrt_keys="$(_fk_mechanism_keys)" || return 1
  _fkrt_live="$(LC_ALL=C jq -r '._schema.mechanism_live_status // empty' "${REG}")" || return 1
  while IFS= read -r _fkrt_k; do
    [ -n "${_fkrt_k}" ] || continue
    _fkrt_ti="$(_fk_mech_role_idx "${_fkrt_k}" token)" || return 1
    _fkrt_si="$(_fk_mech_role_idx "${_fkrt_k}" status)" || return 1
    LC_ALL=C jq -r --arg k "${_fkrt_k}" --argjson ti "${_fkrt_ti}" \
      --argjson si "${_fkrt_si}" --arg live "${_fkrt_live}" \
      '.[$k].rows[] | select(.[$si] == $live) | .[$ti]' "${REG}" || return 1
  done <<EOF
${_fkrt_keys}
EOF
}

_fk_validate_mechanism() {   # 機制表資料列之封閉驗證（不觸宿主檔，故三條路徑皆可掛）
  _fk_mechanism_schema_present || return 0      # 整組缺席＝無機制登記，合法
  _fkvm_rc=0
  # 🔴 schema 為**一整組**，不得單獨刪其中一項〔WL-02 CODEX-R2-P1-02 同型〕：
  #   以「有沒有 mechanism_keys」決定要不要跑檢查 ⇒ 單獨刪它即靜默停用全部檢查。
  for _fkvm_f in ${_FK_MECHANISM_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkvm_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: _schema 已宣告部分機制欄，但缺 ${_fkvm_f} → fail-closed（機制 schema 為一整組，不得單獨刪）" >&2
           _fkvm_rc=1; }
  done
  [ "${_fkvm_rc}" = "0" ] || return 1

  for _fkvm_f in mechanism_keys mechanism_status_enum mechanism_scope mechanism_tokens; do
    LC_ALL=C jq -e --arg f "${_fkvm_f}" \
      '._schema[$f] | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)' \
      "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: _schema.${_fkvm_f} 非法（須非空字串陣列）→ fail-closed" >&2
           _fkvm_rc=1; }
  done
  [ "${_fkvm_rc}" = "0" ] || return 1

  _fkvm_live="$(LC_ALL=C jq -r '._schema.mechanism_live_status // empty' "${REG}")"
  [ -n "${_fkvm_live}" ] || {
    echo "gen_fact_key_blocks: _schema.mechanism_live_status 缺席或為空 → fail-closed" >&2
    return 1; }
  LC_ALL=C jq -e --arg l "${_fkvm_live}" '._schema.mechanism_status_enum | index($l) != null' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: mechanism_live_status='${_fkvm_live}' 不在 mechanism_status_enum 內 → fail-closed" >&2
         return 1; }

  # opt-in 宿主清單：exact path、禁 wildcard、禁目錄前綴（opt-in 必須逐檔顯式）
  while IFS= read -r _fkvm_sc; do
    [ -n "${_fkvm_sc}" ] || continue
    case "${_fkvm_sc}" in
      *'*'*|*'?'*|*'['*)
        echo "gen_fact_key_blocks: _schema.mechanism_scope 不得含 wildcard：${_fkvm_sc} → fail-closed" >&2
        _fkvm_rc=1 ;;
      */)
        echo "gen_fact_key_blocks: _schema.mechanism_scope 須為 exact path，不得為目錄前綴：${_fkvm_sc} → fail-closed（opt-in 必須逐檔顯式）" >&2
        _fkvm_rc=1 ;;
      /*|*..*)
        echo "gen_fact_key_blocks: _schema.mechanism_scope 不得為絕對路徑或含 ..：${_fkvm_sc} → fail-closed" >&2
        _fkvm_rc=1 ;;
    esac
  done <<EOF
$(LC_ALL=C jq -r '._schema.mechanism_scope[]' "${REG}" 2>/dev/null)
EOF

  _fkvm_all="$(_fk_keys)" || return 1        # 🔴 同上：迴圈外取一次並驗 rc
  while IFS= read -r _fkvm_k; do
    [ -n "${_fkvm_k}" ] || continue
    printf '%s\n' "${_fkvm_all}" | LC_ALL=C grep -qxF "${_fkvm_k}" || {
      echo "gen_fact_key_blocks: mechanism_keys 含未註冊 key '${_fkvm_k}' → fail-closed" >&2
      _fkvm_rc=1; continue; }
    _fkvm_bad=""
    for _fkvm_role in id token scope evidence finding status; do
      _fk_mech_role_idx "${_fkvm_k}" "${_fkvm_role}" >/dev/null 2>&1 \
        || _fkvm_bad="${_fkvm_bad} ${_fkvm_role}"
    done
    [ -z "${_fkvm_bad}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvm_k} 缺角色欄（mechanism_column_roles 未宣告或 columns 無該欄）:${_fkvm_bad} → fail-closed" >&2
      _fkvm_rc=1; continue; }
    _fkvm_ii="$(_fk_mech_role_idx "${_fkvm_k}" id)"       || { _fkvm_rc=1; continue; }
    _fkvm_ti="$(_fk_mech_role_idx "${_fkvm_k}" token)"    || { _fkvm_rc=1; continue; }
    _fkvm_ei="$(_fk_mech_role_idx "${_fkvm_k}" evidence)" || { _fkvm_rc=1; continue; }
    _fkvm_si="$(_fk_mech_role_idx "${_fkvm_k}" status)"   || { _fkvm_rc=1; continue; }

    # ① 狀態列舉封閉
    _fkvm_unknown="$(LC_ALL=C jq -r --arg k "${_fkvm_k}" --argjson si "${_fkvm_si}" '
      (._schema.mechanism_status_enum) as $e
      | .[$k].rows[] | select((.[$si] | IN($e[]) | not)) | .[$si]' "${REG}" \
      | LC_ALL=C sort -u)"
    [ -z "${_fkvm_unknown}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvm_k} 之狀態值不在 mechanism_status_enum 內 → fail-closed:" >&2
      printf '%s\n' "${_fkvm_unknown}" | sed 's/^/    /' >&2
      _fkvm_rc=1; }

    # ② 機制 token 須在封閉表內（防筆誤：登記了但掃描仍紅，作者卻以為已登記）
    _fkvm_offtab="$(LC_ALL=C jq -r --arg k "${_fkvm_k}" --argjson ti "${_fkvm_ti}" '
      (._schema.mechanism_tokens) as $t
      | .[$k].rows[] | select((.[$ti] | IN($t[]) | not)) | .[$ti]' "${REG}" \
      | LC_ALL=C sort -u)"
    [ -z "${_fkvm_offtab}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvm_k} 之平台機制不在 _schema.mechanism_tokens 封閉表內 → fail-closed:" >&2
      printf '%s\n' "${_fkvm_offtab}" | sed 's/^/    /' >&2
      _fkvm_rc=1; }

    # ③ 機制 ID 唯一（重複 ID ⇒ 指標語義未定義）
    _fkvm_dup="$(LC_ALL=C jq -r --arg k "${_fkvm_k}" --argjson ii "${_fkvm_ii}" \
      '.[$k].rows | group_by(.[$ii]) | map(select(length > 1)) | .[] | .[0][$ii]' "${REG}" \
      | LC_ALL=C sort -u)"
    [ -z "${_fkvm_dup}" ] || {
      echo "gen_fact_key_blocks: key ${_fkvm_k} 有重複機制ID → fail-closed:" >&2
      printf '%s\n' "${_fkvm_dup}" | sed 's/^/    /' >&2
      _fkvm_rc=1; }

    # ④ 證據欄格式封閉 ＋ receipt 指向之檔須存在
    while IFS= read -r _fkvm_ev; do
      [ -n "${_fkvm_ev}" ] || continue
      _fkvm_pfx="${_fkvm_ev%%:*}"; _fkvm_val="${_fkvm_ev#*:}"
      case " ${_FK_EVIDENCE_FORMS} " in
        *" ${_fkvm_pfx} "*) : ;;
        *) echo "gen_fact_key_blocks: key ${_fkvm_k} 之證據 '${_fkvm_ev}' 前綴不在 {${_FK_EVIDENCE_FORMS}} → fail-closed" >&2
           _fkvm_rc=1; continue ;;
      esac
      [ -n "${_fkvm_val}" ] && [ "${_fkvm_val}" != "${_fkvm_ev}" ] || {
        echo "gen_fact_key_blocks: key ${_fkvm_k} 之證據 '${_fkvm_ev}' 缺冒號後之內容 → fail-closed" >&2
        _fkvm_rc=1; continue; }
      [ "${_fkvm_pfx}" = "receipt" ] || continue
      case "${_fkvm_val}" in
        /*|*..*)
          echo "gen_fact_key_blocks: key ${_fkvm_k} 之 receipt 路徑不得為絕對路徑或含 ..：${_fkvm_val} → fail-closed" >&2
          _fkvm_rc=1; continue ;;
      esac
      # 🔴 symlink 一律拒〔CODEX-R1-P2-04〕：`-f` 會跟隨連結，故 `docs/link.md -> ../外部檔`
      #   可讓 receipt 指向 repo 之外，codex 實跑得 rc=0。與 `_fk_reject_handwritten_status`
      #   對 symlink 的處置同一紀律（那裡也是先判 `-L` 再判 regular file）。
      if [ -L "$(_fk_root)/${_fkvm_val}" ]; then
        echo "gen_fact_key_blocks: key ${_fkvm_k} 之 receipt 為 symlink：${_fkvm_val} → fail-closed（可指向 repo 外，證據不可稽核）" >&2
        _fkvm_rc=1; continue
      fi
      [ -f "$(_fk_root)/${_fkvm_val}" ] || {
        echo "gen_fact_key_blocks: key ${_fkvm_k} 之 receipt 指向不存在之檔：${_fkvm_val} → fail-closed（宣稱實跑但無物可查）" >&2
        _fkvm_rc=1; }
    done <<EOF
$(LC_ALL=C jq -r --arg k "${_fkvm_k}" --argjson ei "${_fkvm_ei}" '.[$k].rows[] | .[$ei]' "${REG}")
EOF
  done <<EOF
$(_fk_mechanism_keys)
EOF
  return "${_fkvm_rc}"
}

# opt-in 宿主之 `- 改法` 子樹掃描：命中封閉表之 token 若未登記為現行 ⇒ fail-closed。
# 🔴 缺檔 fail-closed，**不得靜默略過**——「缺檔＝略過」正是 G-7 上一輪被抓到的 fail-open。
_fk_reject_unregistered_mechanisms() {
  _fk_mechanism_schema_present || return 0
  _fkru_root="$(_fk_root)"; _fkru_rc=0
  _fkru_toks="$(LC_ALL=C jq -r '._schema.mechanism_tokens[]' "${REG}" | tr '\n' ' ')" || return 1
  _fkru_reg="$(_fk_registered_tokens | LC_ALL=C sort -u | tr '\n' ' ')" || return 1
  while IFS= read -r _fkru_f; do
    [ -n "${_fkru_f}" ] || continue
    _fkru_p="${_fkru_root}/${_fkru_f}"
    [ -f "${_fkru_p}" ] || {
      echo "gen_fact_key_blocks: mechanism_scope 所列宿主不存在：${_fkru_f} → fail-closed（缺檔不得靜默略過）" >&2
      _fkru_rc=1; continue; }
    _fkru_hit="$(LC_ALL=C awk -v toks="${_fkru_toks}" -v reg="${_fkru_reg}" -v rel="${_fkru_f}" '
      # 邊界判定用原始行＋絕對位置（與 _fk_reject_handwritten_status 同一形態）
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
        nt = split(toks, T, " ")
        nr = split(reg, R, " "); for (i = 1; i <= nr; i++) if (R[i] != "") REG[R[i]] = 1
      }
      # 🔴 子樹起點：`- 改法`，允許**實測導出**之裝飾前綴〔GROK-R1-P2-01〕。
      #   opt-in 宿主內實際存在 `- 🔴 **改法` 與 `- **改法` 兩種寫法，原正則整段漏掃。
      #   本集合與 `_FK_RC_CLAIM_FORMS` 同一紀律：**具名、實測導出、擴充須改本行**，
      #   不得改成「任意前綴」——`- 見 改法 一節` 那類會被誤判為起點。
      #   🔴 已在子樹內時，**更深縮排**的起點不得覆寫 boundary〔CODEX-R2-P1-01〕：
      #   `- 改法：` ／ `  - 改法：內層步驟` ／ `  - 外層續行用 X` 這種寫法，
      #   內層起點會把 start_indent 抬到 2，使其後的同級續行（縮排 2）當場被判終止 ⇒ 漏掃。
      #   r2 三家中僅 codex 構造出此形（另兩家判「無第四旁路」，係未測此形態）。
      /^[[:space:]]*- (🔴[[:space:]]+)?(\*\*)?改法/ {
        match($0, /^[[:space:]]*/)
        if (!insub || RLENGTH <= start_indent) start_indent = RLENGTH
        insub = 1
      }
      # 🔴 終點＝**單一封閉判準**：第一個「縮排 ≤ 起點縮排、且非空」之行。
      #   原版列了四個條件（同級 bullet／標題／粗體段首／空行），三家各自實構出三個旁路：
      #     · 巢狀 `- ` 提前截斷〔CODEX-R1-P1-01／GROK-R1-P1-01／COMPOSER-R1-P1-01，三家全員〕
      #       —— 本庫慣用「`- 改法：` 底下掛縮排子彈」，起點下一行即截斷（GOVB25:143、DISPATCH:288）
      #     · 空行提前截斷〔GROK-R1-P1-02〕—— 多段改法之第二段整段漏掃
      #     · 粗體段首那行本身不被掃〔COMPOSER-R1-P1-02〕
      #   改用縮排判準後前兩者一併消失：續行必然縮排更深，這是 markdown 的結構事實，
      #   不是又一條列舉。空行不終止（縮排視為未定義，沿用 insub）。
      #   🔴 具名殘留：縮排 0 之粗體段首仍終止且**不掃該行**——它是新段落的慣例標記，
      #   納入會把 `- 驗證：` 那類行也算進改法子樹而製造新的誤擋。見登記表殘留 7。
      insub && !/^[[:space:]]*- (🔴[[:space:]]+)?(\*\*)?改法/ {
        if ($0 !~ /^[[:space:]]*$/) {
          match($0, /^[[:space:]]*/)
          if (RLENGTH <= start_indent) insub = 0
        }
      }
      insub {
        for (i = 1; i <= nt; i++) {
          if (T[i] == "" || !has_token($0, T[i])) continue
          if (T[i] in REG) continue
          printf "  %s:%d 平台機制 %s 未登記為現行\n", rel, FNR, T[i]
        }
      }
    ' "${_fkru_p}")"
    [ -z "${_fkru_hit}" ] || {
      echo "gen_fact_key_blocks: opt-in 宿主 ${_fkru_f} 之改法子樹使用未登記之平台機制（登記到 governance-mechanism 並附 receipt: 或 assumed:）→ fail-closed:" >&2
      printf '%s\n' "${_fkru_hit}" >&2
      _fkru_rc=1; }
  done <<EOF
$(LC_ALL=C jq -r '._schema.mechanism_scope[]' "${REG}" 2>/dev/null)
EOF
  return "${_fkru_rc}"
}

# ==========================================================================
# 產出端覆蓋登記表 — 使用者 2026-08-13 定死之憲法級規則的機械強制點
#
# 使用者逐字：「治理的所有票，包含已經做過和正在做和未來的實作，都要在產出端擋下，
#   這才能當已完成，除非像 G-7 和 pytest 等可以說明為何不該放在產出端，
#   這任務完成檢查在所有治理 epic 中都適用，你要想辦法卡住，不能漏。」
#
# 🔴 「不能漏」的落法＝檢查 ④：把**票能不能標收案**跟**它的檢查在不在產出端**綁死。
#   任何票要標收案，必先在 `governance-enforcement` 登記其掛載點；
#   掛不到產出端就得寫出為什麼。這不是文件宣告，是這裡的 fail-closed。
#
# 🔴 檢查 ② 是**機械對證**不是自我宣稱：宣告「產出端」者，其掛載點必須在
#   `.claude/settings.json` 的 hooks 裡真的找得到（event＋matcher＋command 三者都要對上）。
#   否則本表會退化成「大家都說自己有做」的散文目錄——那正是本 epic 反覆治的病。
_FK_ENFORCEMENT_SCHEMA_FIELDS='enforcement_keys enforcement_side_enum enforcement_producer_side enforcement_column_roles enforcement_settings_path enforcement_closed_status enforcement_ticket_roles enforcement_ticket_allowlist'

# 🔴 收案字面**寫死於此**，非由註冊表自證——自證＝無檢查（同 `_FK_RESERVED` 之紀律）。
#   r1 三家全員實構出「規則被它所管制的資料自己關掉」：
#     · `COMPOSER-R1-P0-01`／`GROK-R1-P1-02`：把 `enforcement_closed_status` 改成票表用不到的
#       字面（如 `CLOSED`），所有仍標收案的票即脫離綁定，`--check` 全綠。
#     · `COMPOSER-R1-P0-02`：整組 `enforcement_*` 欄與 key 一併刪除 ⇒ 四道檢查靜默跳過。
#     · `CODEX-R1-P0-01`：關閉狀態／schema presence／票列全由同一份可變 JSON 自己宣告。
#   ⇒ 啟用判定改為**由票表反推**：只要任一狀態 key 的資料列出現此字面，
#     enforcement schema 就**必須完整存在**，且其 closed_status 必須等於此值。
#     刪 schema 不再等於關閉規則——那會直接 fail-closed。
_FK_CLOSED_STATUS='收案'

# 🔴 S2.1：綁定不再只認「收案」單一字面——status_enum 裡另有數個同表「已完成」之值，
#   把票標成其中任一即可脫離收案綁定（grok 實構之繞法）。改以**完成語意封閉集合**判定。
#   仍寫死於生成器（非由註冊表自證），理由同 _FK_CLOSED_STATUS：自證＝無檢查。
#   ⚠️ 「部分完成」**刻意不列入**：依 S0.2 定義它是「驗收未全達成」，不是完成語意。
_FK_COMPLETED_STATUSES='收案 已落地 已完成'

# 票表中是否存在標為**任一完成語意**之列（不依賴 enforcement schema，故無法被其缺席繞過）
_fk_has_closed_ticket() {
  _fkhc_json="$(printf '%s\n' ${_FK_COMPLETED_STATUSES} | LC_ALL=C jq -R . | LC_ALL=C jq -sc .)"
  LC_ALL=C jq -e --argjson cs "${_fkhc_json}" '
    (._schema.status_keys // []) as $sk
    | [ $sk[] as $k | (.[$k].rows // [])[] | .[] ] as $vals
    | any($cs[]; . as $c | $vals | index($c) != null)
  ' "${REG}" >/dev/null 2>&1
}

# 豁免理由之佔位符黑名單（**刻意極小**：只擋明顯空殼，充分性由 review 判定，見登記表殘留 4）
_FK_WAIVER_PLACEHOLDERS='— - 無 n/a N/A TBD tbd 待填 ?'
# 🔴 S6.1 理由体例之具名段（唯一定義處；檢查 ⑧ 與登記表說明皆取用此四值）
_FK_ENF_MARK_PRE='PreToolUse不可：'
_FK_ENF_MARK_POST='PostToolUse不可：'
_FK_ENF_MARK_PART='部分閘：'
_FK_ENF_MARK_IMPL='實作位置：'

_fk_enforcement_keys() { LC_ALL=C jq -r '._schema.enforcement_keys[]? // empty' "${REG}"; }

_fk_enf_role_idx() { _fk_role_idx_of "$1" "$2" enforcement_column_roles; }

_fk_enforcement_schema_present() {
  for _fkep_f in ${_FK_ENFORCEMENT_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkep_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 && return 0
  done
  return 1
}

# 掛載點對證：`<event>:<matcher>:<command 片段>`；matcher 內多工具以半形逗號分隔
# （不用 `|`——render=table 儲存格禁 `|`，產出端守衛已於上線當天實際擋下一次）。
_fk_mount_exists() {   # $1=掛載點字串 → rc=0 表示 settings.json 內確實有
  _fkme_ev="${1%%:*}"; _fkme_rest="${1#*:}"
  _fkme_mt="${_fkme_rest%%:*}"; _fkme_cmd="${_fkme_rest#*:}"
  [ -n "${_fkme_ev}" ] && [ -n "${_fkme_mt}" ] && [ -n "${_fkme_cmd}" ] || return 1
  [ "${_fkme_cmd}" != "${_fkme_rest}" ] || return 1        # 三段都要有
  _fkme_sp="$(LC_ALL=C jq -r '._schema.enforcement_settings_path' "${REG}")" || return 1
  # 🔴 settings.json 相對 **repo root**（腳本父目錄），不是 `_fk_root()`——
  #   與 WL-03 的 receipt 刻意相反，理由不同：receipt 是「被驗那棵樹」的資產，
  #   而 hook 掛載是**主控端環境**的事實，fixture 樹裡本來就不該有 settings.json。
  #   若改成 `_fk_root()`，所有 fixture 測試會因缺該檔而整批誤紅。
  _fkme_repo="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
  _fkme_path="${_fkme_repo}/${_fkme_sp}"
  # 🔴 rc=2 ＝**環境不完整**，與 rc=1「掛載點不存在」語意分開：
  #   settings.json 是**主控端環境**的事實；在不含它的 repo 副本（既有測試的最小 fixture）
  #   上問「掛載點在不在」無從回答，一律判紅會讓那些測試恆紅。
  #   🔴 S1.2 已收窄此 fail-open（原為：檔不存在即 rc=2 略過 ⇒ 刪掉 settings.json 即跳過對證，
  #   codex 判「大聲印出不是阻擋」）。現行拆成兩種、以**目錄是否存在**判別，此判準封閉可判定：
  #     · 承載目錄存在、settings.json 不存在 ⇒ **環境異常**（被刪／改名）⇒ rc=3 ⇒ fail-closed
  #     · 承載目錄本身不存在 ⇒ 真的不是主控端環境（fixture 樹／委員沙箱）⇒ rc=2 ⇒ 略過
  #   如此既堵住「刪檔即跳過」，又不讓沒有 .claude/ 的最小 fixture 整批誤紅。
  if [ ! -f "${_fkme_path}" ]; then
    _fkme_dir="$(dirname -- "${_fkme_path}")"
    [ -d "${_fkme_dir}" ] && return 3
    return 2
  fi
  # 🔴 片段須為 repo 內**實際存在且可執行**的腳本路徑
  #   〔GROK-R1-P1-01 實構：`contains` 下短子串如 `sh`／`a`／`bash` 對真實 settings.json
  #    即判「掛載存在」，等於任何新列都能自動過關〕
  # 🔴 S3.1：command 段允許**帶參數**（如 `scripts/ts_stamp.sh OUT`）——
  #   原本對整段要求 `*.sh` 結尾，使任何帶參數的 hook 都無法登記（實測 PostToolUse 之
  #   ts_stamp.sh OUT 與 UserPromptSubmit 皆卡在此）。改為只對**第一個 token**（腳本路徑）
  #   施加 `.sh` 與存在性判準；完整字串仍用於 startswith 比對，故偽造空間未擴大。
  _fkme_cmd_head="${_fkme_cmd%% *}"
  case "${_fkme_cmd_head}" in
    *.sh) : ;;
    *)    return 1 ;;
  esac
  # 判準用 `-f` 不用 `-x`：hook 以 `bash <path>` 呼叫，**不依賴執行位**
  #   （實測 `doc_format_precheck.sh` 即無執行位卻正常運作）⇒ 要求 `-x` 是與呼叫方式不符的判準。
  #   封閉性由「`.sh` 結尾 ＋ 檔案存在 ＋ command 以 `bash <片段>` 起頭」三者共同保證。
  [ -f "${_fkme_repo}/${_fkme_cmd_head}" ] || return 1
  # matcher 以逗號分隔還原成 settings.json 內的 `|` 形式後比對
  _fkme_mt_pipe="$(printf '%s' "${_fkme_mt}" | tr ',' '|')"
  # 🔴 command 須**以 `bash <片段>` 起頭**，不是「含有該子串」
  #   〔CODEX-R1-P0-02／COMPOSER-R1-P1-03 實構：把 hook 換成 `echo …factkey_write_guard.sh`
  #    或永遠 rc=0 的 noop 但保留子字串，即可偽造掛載證明〕
  #   誠實邊界：這只擋掉「換成別的指令」，擋不掉「腳本被掏空」——見登記表殘留 3。
  # 🔴 S3.1：matcher 段為 `-` 表示「該事件本來就沒有 matcher」。
  #   實測 .claude/settings.json：UserPromptSubmit／Stop／SessionStart 三個事件的項目**無 matcher 欄**
  #   （它們不針對工具）⇒ 原本一律比 `.matcher == $mt` 會使這類 runtime 檢查**永遠無法登記**，
  #   進而被誤判為「應前移卻未前移」。此即 S3.1 要修的洞，非放寬。
  LC_ALL=C jq -e --arg ev "${_fkme_ev}" --arg mt "${_fkme_mt_pipe}" --arg cmd "${_fkme_cmd}" '
    (.hooks[$ev] // [])
    | any(.[]; (if $mt == "-" then (.matcher == null) else (.matcher == $mt) end)
               and ((.hooks // []) | any(.[]; (.command // "") | startswith("bash " + $cmd))))
  ' "${_fkme_path}" >/dev/null 2>&1
}

_fk_validate_enforcement() {
  # 🔴 啟用判定由**票表**反推，不由 enforcement schema 自證（見 _FK_CLOSED_STATUS 註解）：
  #   票表有收案列 ⇒ schema 必須完整；沒有收案列且 schema 整組缺席 ⇒ 才算未啟用。
  if _fk_has_closed_ticket; then
    _fk_enforcement_schema_present || {
      echo "gen_fact_key_blocks: 票表存在標為『${_FK_CLOSED_STATUS}』之列，但 _schema 完全沒有產出端覆蓋宣告 → fail-closed" >&2
      echo "  規則（使用者 2026-08-13 定死）：治理票要標收案，其檢查必須擋在產出端；刪掉 schema 不等於關閉本規則。" >&2
      return 1; }
  else
    _fk_enforcement_schema_present || return 0      # 無收案票且整組缺席＝未啟用，合法
  fi
  _fkve_rc=0
  for _fkve_f in ${_FK_ENFORCEMENT_SCHEMA_FIELDS}; do
    LC_ALL=C jq -e --arg f "${_fkve_f}" '._schema | has($f)' "${REG}" >/dev/null 2>&1 \
      || { echo "gen_fact_key_blocks: _schema 已宣告部分產出端覆蓋欄，但缺 ${_fkve_f} → fail-closed（本 schema 為一整組）" >&2
           _fkve_rc=1; }
  done
  [ "${_fkve_rc}" = "0" ] || return 1

  # 🔴 closed_status 必須等於寫死值，封死「改字面即脫鉤」〔COMPOSER-R1-P0-01／GROK-R1-P1-02〕
  _fkve_cs="$(LC_ALL=C jq -r '._schema.enforcement_closed_status' "${REG}")"
  [ "${_fkve_cs}" = "${_FK_CLOSED_STATUS}" ] || {
    echo "gen_fact_key_blocks: enforcement_closed_status='${_fkve_cs}' 不等於生成器寫死之收案字面 '${_FK_CLOSED_STATUS}' → fail-closed（改字面即脫鉤，已由委員實構）" >&2
    return 1; }
  LC_ALL=C jq -e --arg c "${_FK_CLOSED_STATUS}" '._schema.status_enum | index($c) != null' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: 收案字面 '${_FK_CLOSED_STATUS}' 不在 status_enum 內 → fail-closed" >&2
         return 1; }
  # 🔴 S2.1：completed_statuses 須**恰等於**生成器寫死之集合（同理封死「改集合即脫鉤」）
  _fkve_cslist="$(printf '%s\n' ${_FK_COMPLETED_STATUSES} | LC_ALL=C jq -R . | LC_ALL=C jq -sc 'sort')"
  _fkve_declared="$(LC_ALL=C jq -c '._schema.enforcement_completed_statuses // [] | sort' "${REG}")" || {
    echo "gen_fact_key_blocks: 讀取 enforcement_completed_statuses 失敗 → fail-closed" >&2; return 1; }
  [ "${_fkve_declared}" = "${_fkve_cslist}" ] || {
    echo "gen_fact_key_blocks: enforcement_completed_statuses=${_fkve_declared} 不等於生成器寫死之完成語意集合 ${_fkve_cslist} → fail-closed" >&2
    echo "  （S2.1：綁定改認集合而非單一字面；改資料即脫鉤之路徑一併封死）" >&2
    return 1; }
  LC_ALL=C jq -e --argjson cs "${_fkve_cslist}" '._schema.status_enum as $e | all($cs[]; . as $c | $e | index($c) != null)' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: 完成語意集合中有值不在 status_enum 內 → fail-closed" >&2
         return 1; }

  _fkve_side="$(LC_ALL=C jq -r '._schema.enforcement_producer_side' "${REG}")"
  LC_ALL=C jq -e --arg s "${_fkve_side}" '._schema.enforcement_side_enum | index($s) != null' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: enforcement_producer_side='${_fkve_side}' 不在 enforcement_side_enum 內 → fail-closed" >&2
         return 1; }

  _fkve_keys="$(_fk_enforcement_keys)" || return 1
  [ -n "${_fkve_keys}" ] || {
    echo "gen_fact_key_blocks: _schema.enforcement_keys 為空 → fail-closed（空清單會使四道檢查全部靜默停用）" >&2
    return 1; }
  _fkve_all="$(_fk_keys)" || return 1

  while IFS= read -r _fkve_k; do
    [ -n "${_fkve_k}" ] || continue
    printf '%s\n' "${_fkve_all}" | LC_ALL=C grep -qxF "${_fkve_k}" || {
      echo "gen_fact_key_blocks: enforcement_keys 含未註冊 key '${_fkve_k}' → fail-closed" >&2
      _fkve_rc=1; continue; }
    _fkve_bad=""
    for _fkve_role in id ticket mount side waiver; do
      _fk_enf_role_idx "${_fkve_k}" "${_fkve_role}" >/dev/null 2>&1 \
        || _fkve_bad="${_fkve_bad} ${_fkve_role}"
    done
    [ -z "${_fkve_bad}" ] || {
      echo "gen_fact_key_blocks: key ${_fkve_k} 缺角色欄（enforcement_column_roles）:${_fkve_bad} → fail-closed" >&2
      _fkve_rc=1; continue; }
    _fkve_ii="$(_fk_enf_role_idx "${_fkve_k}" id)"     || { _fkve_rc=1; continue; }
    _fkve_mi="$(_fk_enf_role_idx "${_fkve_k}" mount)"  || { _fkve_rc=1; continue; }
    _fkve_si="$(_fk_enf_role_idx "${_fkve_k}" side)"   || { _fkve_rc=1; continue; }
    _fkve_wi="$(_fk_enf_role_idx "${_fkve_k}" waiver)" || { _fkve_rc=1; continue; }

    # ① 強制側封閉列舉
    _fkve_unknown="$(LC_ALL=C jq -r --arg k "${_fkve_k}" --argjson si "${_fkve_si}" '
      (._schema.enforcement_side_enum) as $e
      | .[$k].rows[] | select((.[$si] | IN($e[]) | not)) | .[$si]' "${REG}" \
      | LC_ALL=C sort -u)"
    [ -z "${_fkve_unknown}" ] || {
      echo "gen_fact_key_blocks: key ${_fkve_k} 之強制側不在 enforcement_side_enum 內 → fail-closed:" >&2
      printf '%s\n' "${_fkve_unknown}" | sed 's/^/    /' >&2
      _fkve_rc=1; }

    # ②③ 逐列：產出端 ⇒ 掛載點須真的存在；豁免 ⇒ 理由非空且非佔位符
    # 🔴 jq rc 不得被 command substitution 吞掉〔CODEX-R1-P1-04〕：語法錯誤會被迴圈末 rc 蓋掉，
    #    形成另一個空心檢查。這是本 session 第三個同型（前兩個：_fk_raw_keys、收案綁定 jq）。
    _fkve_rows="$(LC_ALL=C jq -r --arg k "${_fkve_k}" --argjson ii "${_fkve_ii}" \
       --argjson mi "${_fkve_mi}" --argjson si "${_fkve_si}" --argjson wi "${_fkve_wi}" \
       '.[$k].rows[] | [.[$ii], .[$mi], .[$si], .[$wi]] | @tsv' "${REG}")" || {
      echo "gen_fact_key_blocks: key ${_fkve_k} 之逐列抽取失敗（jq 非零）→ fail-closed" >&2
      _fkve_rc=1; continue; }
    while IFS='	' read -r _fkve_id _fkve_mount _fkve_sd _fkve_wv; do
      [ -n "${_fkve_id}" ] || continue
      if [ "${_fkve_sd}" = "${_fkve_side}" ]; then
        _fk_mount_exists "${_fkve_mount}"
        case "$?" in
          0) : ;;
          2) # 承載目錄本身不存在＝真的非主控端環境（fixture／沙箱）：大聲說，不判紅
             echo "gen_fact_key_blocks: ${_fkve_id} 之掛載點未對證——本樹無 hook 設定之承載目錄（非主控端環境）⇒ 略過對證。真主控端仍會驗。" >&2 ;;
          3) # 🔴 S1.2：承載目錄在、設定檔不在 ⇒ 環境異常，判紅（原本此路與 rc=2 合流，是 fail-open）
             echo "gen_fact_key_blocks: ${_fkve_id} 之掛載點無法對證——hook 設定之承載目錄存在，但設定檔缺失 → fail-closed" >&2
             echo "  這不是「非主控端環境」，而是設定檔被刪或改名；此路徑原與略過合流，" >&2
             echo "  等於刪掉設定檔即可跳過全部掛載點對證（S1.2 已封）。" >&2
             _fkve_rc=1 ;;
          *) echo "gen_fact_key_blocks: ${_fkve_id} 宣告為${_fkve_side}，但掛載點在 settings.json 內不存在：${_fkve_mount} → fail-closed（禁自我宣稱）" >&2
             _fkve_rc=1 ;;
        esac
      else
        _fkve_hit=0
        for _fkve_ph in ${_FK_WAIVER_PLACEHOLDERS}; do
          [ "${_fkve_wv}" = "${_fkve_ph}" ] && _fkve_hit=1 && break
        done
        [ -n "${_fkve_wv}" ] && [ "${_fkve_hit}" = "0" ] || {
          echo "gen_fact_key_blocks: ${_fkve_id} 為豁免但豁免理由為空或佔位符 → fail-closed" >&2
          _fkve_rc=1; }
      fi
    done <<EOF
${_fkve_rows}
EOF
  done <<EOF2
${_fkve_keys}
EOF2

  # ④ 🔴 收案綁定 —— 本規則的「卡住」之處
  _fkve_tk="$(LC_ALL=C jq -r '._schema.enforcement_ticket_roles.key' "${REG}")"
  printf '%s\n' "${_fkve_all}" | LC_ALL=C grep -qxF "${_fkve_tk}" || {
    echo "gen_fact_key_blocks: enforcement_ticket_roles.key '${_fkve_tk}' 未註冊 → fail-closed" >&2
    return 1; }
  # 🔴 jq 錯誤**不得吞掉**：原版帶 `2>/dev/null`，jq 失敗時結果為空 ⇒ 靜默放行＝假綠。
  #   （同型於本 epic 定案過的「jq rc 被 process substitution 吞掉」根因。）
  # 🔴 欄名先綁成 `$tcol`：不可在 `index(...)` 的參數位置寫 `._schema…`——
  #   該處的 `.` 已被 pipe 改成 `$e.columns`，會取到 null 而使整條檢查恆綠。
  #   初版即如此，反例只因 DRIFT 而紅，**險些把空心檢查當成通過**（訊息斷言才抓到）。
  # 🔴 S2.1：判定改用**完成語意集合**（原為單一 $closed 字面，把票標成 已落地／已完成 即可繞過）
  _fkve_missing="$(LC_ALL=C jq -er --arg tk "${_fkve_tk}" --argjson cs "${_fkve_cslist}" '
    ._schema.enforcement_column_roles.ticket as $tcol
    | ._schema.enforcement_ticket_roles as $tr
    | [ ._schema.enforcement_keys[] as $ek
        | .[$ek] as $e
        | ($e.columns | index($tcol)) as $ti
        | $e.rows[] | .[$ti] ] as $covered
    | (.[$tk].columns | index($tr.id)) as $idi
    | (.[$tk].columns | index($tr.status)) as $sti
    | [ .[$tk].rows[] | select(.[$sti] as $s | ($cs | index($s)) != null) | .[$idi] ]
    | map(select(. as $t | ($covered | index($t)) == null))
    | join("\n")' "${REG}")" || {
    echo "gen_fact_key_blocks: 收案綁定檢查之 jq 失敗 → fail-closed（不得當成『沒有未覆蓋的票』）" >&2
    return 1; }
  [ -z "${_fkve_missing}" ] || {
    echo "gen_fact_key_blocks: 下列票已標『$(LC_ALL=C jq -r '._schema.enforcement_closed_status' "${REG}")』但未在 ${_fkve_tk%%-*}-enforcement 登記產出端覆蓋 → fail-closed:" >&2
    printf '%s\n' "${_fkve_missing}" | sed 's/^/    /' >&2
    echo "  規則（使用者 2026-08-13 定死）：治理票要標收案，其檢查必須擋在產出端；" >&2
    echo "  擋不了就在 governance-enforcement 具名寫出為什麼（如 G-7 需 commit、pytest 十分鐘級）。" >&2
    return 1; }

  # ⑦ 🔴 S3.2 判定型分類：每列之「判定型」須在 enforcement_kind_enum 內，
  #   且與強制側一致——產出端列不得填 n/a（那等於沒分類）、豁免列必須是 n/a
  #   （豁免不涉產出端掛載階段，填內容型／一致性型是語意錯置）。
  _fkve_kindbad="$(LC_ALL=C jq -er '
    . as $root
    | $root._schema.enforcement_column_roles.kind as $kcol
    | $root._schema.enforcement_kind_enum as $kenum
    | $root._schema.enforcement_column_roles.side as $scol
    | $root._schema.enforcement_column_roles.id as $icol
    | $root._schema.enforcement_producer_side as $pside
    | [ $root._schema.enforcement_keys[] as $ek
        | $root[$ek] as $e
        | ($e.columns | index($kcol)) as $ki
        | ($e.columns | index($scol)) as $si
        | ($e.columns | index($icol)) as $ii
        | $e.rows[]
        | { id: .[$ii], kind: .[$ki], side: .[$si] } ]
    | map(. as $row | select(
        ($row.kind == null)
        or (($kenum | index($row.kind)) == null)
        or ($row.side == $pside and $row.kind == "n/a")
        or ($row.side != $pside and $row.kind != "n/a")
      ))
    | map("\(.id)（強制側=\(.side) 判定型=\(.kind // "缺")）")
    | join("\n")' "${REG}")" || {
    echo "gen_fact_key_blocks: 判定型分類檢查之 jq 失敗 → fail-closed" >&2; return 1; }
  [ -z "${_fkve_kindbad}" ] || {
    echo "gen_fact_key_blocks: 下列列之「判定型」不合法或與強制側不一致 → fail-closed:" >&2
    printf '%s\n' "${_fkve_kindbad}" | sed 's/^/    /' >&2
    echo "  規則（S3.2）：產出端列須為 內容型 或 一致性型；豁免列須為 n/a。" >&2
    echo "  判準：只看這一次的編輯內容能否判定對錯？能＝內容型，否＝一致性型。" >&2
    return 1; }

  # ⑧ 🔴 S6.1 豁免理由体例 ＋ 引用對證（兩條，皆封閉可判定）
  #
  #   (a) **体例**：豁免列的理由必須**同時**寫出兩側各自不可行的理由。
  #       病根：S4.3 一口氣填 16 則，理由全寫成「輸入為完整文件，非單次編輯內容」——
  #       那只證明**不能 PreToolUse**，完全沒有證明**不能 PostToolUse**。
  #       反例就在同一棵樹上：factkey_write_guard 也要看整棵樹，照樣掛 PostToolUse。
  #       ⇒ 本檢查要求兩段分開寫，寫不出「PostToolUse 也不行」就不該是豁免。
  #       產出端列則須寫出「實作位置」，否則 S4.2 要求的「檢查位置紀錄（檔:行）」會在
  #       改判為產出端的當下消失。
  #
  #   (b) **引用對證**：理由中 `部分閘：`／`實作位置：` 之後的 `<檔>:<行>` 引用，
  #       該行不得為註解或空行、檔案須存在。
  #       🔴 這條是拿人命換的：S4.4 三家複驗打回五則不實登記，其中 E-011 填的 :408
  #       落在**註解區塊首行**；S6.1 重掃又抓到四處同型（E-014／E-015／E-019／E-020）。
  #       同一種錯誤犯第六次就不該再靠人眼——判準本身封閉，直接機械化。
  #
  #   🔴 引用一律對 **repo root** 解析（與掛載點對證同理，與 `_fk_root()` 刻意相反）：
  #     被引用的是**主控端現樹**的實作行，不是 fixture 樹的資產；對 fixture 解析會整批誤紅。
  _fkve_repo2="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
  _fkve_formbad=""; _fkve_refbad=""
  _fkve_wrows="$(LC_ALL=C jq -er '
    . as $root
    | $root._schema.enforcement_column_roles as $r
    | [ $root._schema.enforcement_keys[] as $ek
        | $root[$ek] as $e
        | ($e.columns | index($r.id)) as $ii
        | ($e.columns | index($r.side)) as $si
        | ($e.columns | index($r.waiver)) as $wi
        | $e.rows[]
        | [ .[$ii], .[$si], .[$wi] ] | @tsv ]
    | join("\n")' "${REG}")" || {
    echo "gen_fact_key_blocks: 豁免理由体例檢查之 jq 失敗 → fail-closed" >&2; return 1; }
  while IFS='	' read -r _fkve_wid _fkve_wsd _fkve_wtx; do
    [ -n "${_fkve_wid}" ] || continue
    if [ "${_fkve_wsd}" = "${_fkve_side}" ]; then
      case "${_fkve_wtx}" in
        *"${_FK_ENF_MARK_IMPL}"*) : ;;
        *) _fkve_formbad="${_fkve_formbad}${_fkve_wid}（產出端列缺「${_FK_ENF_MARK_IMPL}」）"$'\n' ;;
      esac
    else
      for _fkve_mk in "${_FK_ENF_MARK_PRE}" "${_FK_ENF_MARK_POST}" "${_FK_ENF_MARK_PART}"; do
        case "${_fkve_wtx}" in
          *"${_fkve_mk}"*) : ;;
          *) _fkve_formbad="${_fkve_formbad}${_fkve_wid}（豁免列缺「${_fkve_mk}」）"$'\n' ;;
        esac
      done
    fi
    # (b) 只驗**具名段之後**的引用：`原填 X 為誤填` 這類更正紀錄刻意不受檢
    #
    # 🔴 只在**主控端環境**驗，判別式與掛載點對證**共用同一個**（`.claude/settings.json`
    #   在不在 —— `_fk_mount_exists` 也正是有它才真的比對），不另造概念。
    #   被引用的是主控端現樹的實作行；測試沙箱只複製生成器本身
    #   （見 test_govb1_factkey_gen.py 之 `_sandbox`），對它解析會把每一條碼證
    #   都判成「檔案不存在」⇒ 整批誤紅。體例檢查 (a) 不讀檔，故沙箱仍照驗。
    [ -f "${_fkve_repo2}/.claude/settings.json" ] || continue
    _fkve_tail=""
    case "${_fkve_wtx}" in *"${_FK_ENF_MARK_PART}"*) _fkve_tail="${_fkve_wtx#*"${_FK_ENF_MARK_PART}"}" ;; esac
    case "${_fkve_wtx}" in *"${_FK_ENF_MARK_IMPL}"*) _fkve_tail="${_fkve_tail} ${_fkve_wtx#*"${_FK_ENF_MARK_IMPL}"}" ;; esac
    [ -n "${_fkve_tail}" ] || continue
    # 🔴 marker 在場但**零引用**必須擋（CODEX-R2-P0-01 於隔離副本實構：把所有豁免列改成
    #   `部分閘：沒有引用` 且不含任何 `<檔>:<行>`，--write 與 --check 皆 rc=0
    #   ⇒ ⑧ 退化成「字串在不在」的形式檢查，擋不住空殼碼證）。
    #   適用條件封閉：`實作位置：` 一律須有引用；`部分閘：` 僅在其值以「有」起頭時須有。
    #   （`部分閘：無` 是合法且常見的答案，強制它附引用會逼人捏造。）
    _fkve_need=0
    case "${_fkve_wtx}" in *"${_FK_ENF_MARK_IMPL}"*) _fkve_need=1 ;; esac
    case "${_fkve_wtx}" in
      *"${_FK_ENF_MARK_PART}有"*) _fkve_need=1 ;;
    esac
    # 🔴 副檔名不限 .sh/.py（COMPOSER-R2-P1-01：原正則只抽這兩種，
    #   於是 `部分閘：有——handoffs/x.md:99` 這種假碼證完全不受檢）。
    _fkve_refs="$(printf '%s' "${_fkve_tail}" \
                  | LC_ALL=C grep -oE '[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+' || true)"
    if [ "${_fkve_need}" -eq 1 ] && [ -z "${_fkve_refs}" ]; then
      _fkve_refbad="${_fkve_refbad}${_fkve_wid}: 具名段宣稱有實作／部分閘，卻無任何 <檔>:<行> 引用"$'\n'
    fi
    for _fkve_ref in ${_fkve_refs}; do
      _fkve_rf="${_fkve_ref%%:*}"; _fkve_rl="${_fkve_ref##*:}"
      if [ ! -f "${_fkve_repo2}/${_fkve_rf}" ]; then
        _fkve_refbad="${_fkve_refbad}${_fkve_wid}: ${_fkve_ref} → 檔案不存在"$'\n'; continue
      fi
      _fkve_rtxt="$(LC_ALL=C awk -v n="${_fkve_rl}" 'NR==n' "${_fkve_repo2}/${_fkve_rf}")"
      case "${_fkve_rtxt}" in
        ''|[[:space:]]*'#'*|'#'*)
          _fkve_rnear="$(LC_ALL=C awk -v s="${_fkve_rl}" 'NR>=s && $0 !~ /^[[:space:]]*#/ && NF>0 {print NR; exit}' \
                          "${_fkve_repo2}/${_fkve_rf}")"
          _fkve_refbad="${_fkve_refbad}${_fkve_wid}: ${_fkve_ref} → 該行為註解或空行（最近可執行碼＝:${_fkve_rnear:-無}）"$'\n' ;;
      esac
    done
  done <<EOF3
${_fkve_wrows}
EOF3
  [ -z "${_fkve_formbad}" ] || {
    echo "gen_fact_key_blocks: 下列列之理由不符 S6.1 体例 → fail-closed:" >&2
    printf '%s' "${_fkve_formbad}" | sed 's/^/    /' >&2
    echo "  豁免列須同時寫「${_FK_ENF_MARK_PRE}…」「${_FK_ENF_MARK_POST}…」「${_FK_ENF_MARK_PART}…」；" >&2
    echo "  產出端列須寫「${_FK_ENF_MARK_IMPL}<檔:行>」。" >&2
    echo "  理由：只說「輸入是完整文件」僅證明不能 PreToolUse，不能證明不能 PostToolUse。" >&2
    _fkve_rc=1; }
  [ -z "${_fkve_refbad}" ] || {
    echo "gen_fact_key_blocks: 下列引用之行號落在註解／空行或檔案不存在 → fail-closed:" >&2
    printf '%s' "${_fkve_refbad}" | sed 's/^/    /' >&2
    echo "  引用要指向**可執行碼**；指到註解等於沒有碼證（S4.4 已打回一次，S6.1 又抓到四處）。" >&2
    _fkve_rc=1; }
  # ⑨ 🔴 enforcement_note 不得提及**已不存在的 fact-key**（CODEX-R3-P2-01）
  #   病根：note 是 schema 內的散文，最容易變成過期副本——它一度同時寫著
  #   「四道檢查」（實際八道）與 S0.6 已刪除的來源 key。主委第一次修訂只改了前者，
  #   把作廢 key 留在「原文指向 X，已刪除」的歷史括註裡 ⇒ grep 仍然找得到，
  #   codex 據此拒簽戳記。歷史敘事屬 docs/GOV_ENFORCEMENT_REGISTRY.md，不屬 schema。
  #   判準封閉可導出：note 內任何 `governance-<名>` token 都必須是本註冊表現存的 key。
  _fkve_note="$(LC_ALL=C jq -r '._schema.enforcement_note // ""' "${REG}")" || {
    echo "gen_fact_key_blocks: 讀取 enforcement_note 失敗 → fail-closed" >&2; return 1; }
  _fkve_ghostkey=""
  for _fkve_tok in $(printf '%s' "${_fkve_note}" | LC_ALL=C grep -oE 'governance-[a-z0-9-]+' | LC_ALL=C sort -u); do
    printf '%s\n' "${_fkve_all}" | LC_ALL=C grep -qxF "${_fkve_tok}" \
      || _fkve_ghostkey="${_fkve_ghostkey}${_fkve_tok} "
  done
  [ -z "${_fkve_ghostkey}" ] || {
    echo "gen_fact_key_blocks: enforcement_note 提及不存在之 fact-key → fail-closed: ${_fkve_ghostkey}" >&2
    echo "  schema 的散文不得保留作廢來源（連「原文指向 X」這種歷史括註也不行——grep 仍會找到）。" >&2
    echo "  歷史敘事寫進 docs/GOV_ENFORCEMENT_REGISTRY.md，不要留在 schema。" >&2
    _fkve_rc=1; }

  [ "${_fkve_rc}" -eq 0 ] || return 1

  # ⑥ 🔴 S2.2 提前預警：**尚未**標完成、但已在推進中的票，若無產出端覆蓋登記，先講。
  #   ⚠️ 本條**刻意只警告不判紅**，與 S1.2 的「大聲印出不是阻擋」不同性質：
  #     · S1.2 那條該紅——它是「檢查自己失效」，放行等於沒有檢查。
  #     · 本條不該紅——「部分完成」依 S0.2 定義本就不需覆蓋；判紅會讓所有推進中的票全紅，
  #       等於逼人不要記錄真實狀態。價值在於**提前告知**，而非再加一道閘。
  #   目的：避免「做到最後一刻才發現缺覆蓋」——那正是使用者要治的、留到下一關才擋的摩擦。
  _fkve_pending="$(LC_ALL=C jq -er --arg tk "${_fkve_tk}" '
    ._schema.enforcement_column_roles.ticket as $tcol
    | ._schema.enforcement_ticket_roles as $tr
    | [ ._schema.enforcement_keys[] as $ek
        | .[$ek] as $e
        | ($e.columns | index($tcol)) as $ti
        | $e.rows[] | .[$ti] ] as $covered
    | (.[$tk].columns | index($tr.id)) as $idi
    | (.[$tk].columns | index($tr.status)) as $sti
    | [ .[$tk].rows[] | select(.[$sti] == "部分完成") | .[$idi] ]
    | map(select(. as $t | ($covered | index($t)) == null))
    | join(" ")' "${REG}" 2>/dev/null)" || _fkve_pending=""
  [ -z "${_fkve_pending}" ] || {
    # 🔴 用詞刻意避開「登記產出端覆蓋」字串：既有測試以該子串斷言「非完成票不被要求覆蓋」，
    #   本預警若沿用同一措辭會讓那些測試誤紅（實測撞到兩條）。訊息語意不變。
    echo "gen_fact_key_blocks: 〔S2.2 預警・不判紅〕下列票為『部分完成』，其產出端覆蓋尚未在登記表列出：" >&2
    printf '    %s\n' "${_fkve_pending}" >&2
    echo "    ⇒ 這些票**現在**不受阻擋；但要標完成前必須先在 governance-enforcement 補列，" >&2
    echo "      否則屆時會被第④道收案綁定擋下。提前告知，避免最後一刻才發現。" >&2; }

  # ⑤ 🔴 S1.1 封死幽靈票 —— 對應票欄之值須在「票全集 ∪ 非票標的白名單」內
  #   allowlist 須存在且為字串陣列（缺欄即 fail-closed，不得因缺欄而略過整條檢查）。
  LC_ALL=C jq -e '._schema.enforcement_ticket_allowlist
                  | type == "array" and (length >= 0)
                  and (map(type == "string" and length > 0) | all)' "${REG}" >/dev/null 2>&1 || {
    echo "gen_fact_key_blocks: _schema.enforcement_ticket_allowlist 缺席或非字串陣列 → fail-closed" >&2
    return 1; }
  # 🔴 全程以 `. as $root` 取值：不可在 index() 參數位置寫 `._schema…`——
  #   該處的 `.` 已被前段 pipe 改寫，會取到 null 而使整條檢查恆綠（本檔 ④ 已踩過一次）。
  _fkve_ghost="$(LC_ALL=C jq -er '
    . as $root
    | $root._schema.enforcement_column_roles.ticket as $tcol
    | $root._schema.enforcement_ticket_allowlist as $allow
    | $root._schema.enforcement_ticket_roles as $tr
    | ($root[$tr.key].columns | index($tr.id)) as $idi
    | [ $root[$tr.key].rows[] | .[$idi] ] as $universe
    | [ $root._schema.enforcement_keys[] as $ek
        | $root[$ek] as $e
        | ($e.columns | index($tcol)) as $ti
        | $e.rows[] | .[$ti] ]
    | unique
    | map(select(. as $v
                 | ($universe | index($v)) == null
                 and ($allow | index($v)) == null))
    | join("\n")' "${REG}")" || {
    echo "gen_fact_key_blocks: 幽靈票檢查之 jq 失敗 → fail-closed（不得當成『沒有幽靈票』）" >&2
    return 1; }
  [ -z "${_fkve_ghost}" ] || {
    echo "gen_fact_key_blocks: governance-enforcement 之「對應票」欄含**票全集外之值** → fail-closed:" >&2
    printf '%s\n' "${_fkve_ghost}" | sed 's/^/    /' >&2
    echo "  修：①若為真票，先登記進 ${_fkve_tk}（票 SoT）②若為非票標的（如判準代號、測試套件），" >&2
    echo "  　　須顯式加入 _schema.enforcement_ticket_allowlist 並在測試之集合相等表同步（禁靜默新增）。" >&2
    return 1; }
  return "${_fkve_rc}"
}

_fk_check() {
  _fk_validate_keys || return 1
  _fk_validate_schema_sets || return 1
  _fkc_root="$(_fk_root)"; _fkc_rc=0
  _fkc_keys="$(_fk_keys)" || return 1        # 🔴 rc 不得經 process substitution 丟失
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
  done <<EOF2
${_fkc_keys}
EOF2
  # 未登記之 generated block 一律拒〔CODEX-R1-P1-02〕
  _fk_reject_unregistered_blocks || _fkc_rc=1
  # 生成區塊外之手寫狀態一律拒（票 B-25 站 2.5 Task 2.1）
  _fk_reject_handwritten_status || _fkc_rc=1
  # 判準表語意 ＋ 判準宿主之區塊外期望陳述（WL-02）
  _fk_validate_criteria || _fkc_rc=1
  _fk_reject_rc_claims_outside_blocks || _fkc_rc=1
  # 機制表語意 ＋ opt-in 宿主之改法子樹未登記機制（WL-03）
  _fk_validate_mechanism || _fkc_rc=1
  _fk_validate_enforcement || _fkc_rc=1
  _fk_reject_unregistered_mechanisms || _fkc_rc=1
  return "${_fkc_rc}"
}

_fk_write() {
  _fk_validate_keys || return 1
  _fk_validate_schema_sets || return 1
  _fk_validate_criteria || return 1
  _fk_validate_mechanism || return 1
  _fk_validate_enforcement || return 1
  # 🔴 `--write` 也跑宿主子樹掃描〔COMPOSER-R1-P2-01〕：本路徑本來就讀寫宿主檔，
  #   漏掛會讓「單跑 --write」的本地流程暫時綠。emit 刻意不掛——它是純 stdout 投影、
  #   不讀宿主檔，掛上去等於憑空要求一棵樹。此差異列為登記表殘留 8，並有測試釘住。
  _fk_reject_unregistered_mechanisms || return 1
  _fkw_root="$(_fk_root)"; _fkw_rc=0
  _fkw_keys="$(_fk_keys)" || return 1        # 🔴 rc 不得經 process substitution 丟失
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
  done <<EOF2
${_fkw_keys}
EOF2
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
