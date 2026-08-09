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
#   rows 型別不符／宿主檔不存在／邊界標記缺失或不成對
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REG="${SCRIPT_DIR}/fact_keys.json"

# 保留鍵字面集合寫死於此（非由註冊表自證；自證＝無檢查）
_FK_RESERVED='_schema'
# fact-key 名稱字元集合：限縮至此，故可安全嵌入 grep/sed 正則而無需跳脫
_FK_KEY_RE='^[a-z0-9][a-z0-9-]*$'

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

_fk_target() {   # $1=key -> stdout: repo 相對路徑
  _fkt_t="$(LC_ALL=C jq -r --arg k "$1" '.[$k].target // empty' "${REG}")" || return 1
  [ -n "${_fkt_t}" ] || {
    echo "gen_fact_key_blocks: key ${1} 缺 target → fail-closed" >&2; return 1; }
  case "${_fkt_t}" in
    /*)   echo "gen_fact_key_blocks: key ${1} 之 target 不得為絕對路徑：${_fkt_t}" >&2; return 1 ;;
    *..*) echo "gen_fact_key_blocks: key ${1} 之 target 不得含 ..：${_fkt_t}" >&2; return 1 ;;
  esac
  printf '%s\n' "${_fkt_t}"
}

_fk_validate_rows() {   # $1=key
  LC_ALL=C jq -e --arg k "$1" \
    '.[$k].rows | type == "array" and all(.[]; type == "array" and all(.[]; type == "string"))' \
    "${REG}" >/dev/null 2>&1 \
    || { echo "gen_fact_key_blocks: key ${1} 之 rows 型別不符（須為字串陣列之陣列）→ fail-closed" >&2
         return 1; }
}

_fk_gen_block() {   # $1=key -> stdout（決定性）
  # 🔴 每一步都須 `|| return 1`〔CODEX-R1-P1-03〕：
  #   前版最後一行是 printf ⇒ **函式 rc 恆為 0**，jq／sort 失敗被吞掉。
  #   `--check` 又只比對字串，於是「生成失敗但輸出恰好相符」＝靜默通過。
  printf '<!-- BEGIN GENERATED: %s -->\n' "$1" || return 1
  # 🔴 LC_ALL=C 為決定性支點（見檔頭實測）；拿掉即 T-2.1-M1 轉紅
  #   （pipefail 已於檔頭 set；此處 rc 反映 jq 或 sort 之失敗）
  LC_ALL=C jq -r --arg k "$1" '.[$k].rows[] | @tsv' "${REG}" | LC_ALL=C sort || return 1
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
_fk_reject_unregistered_blocks() {
  _fkr_root="$(_fk_root)"; _fkr_rc=0
  _fkr_keys="$(_fk_keys)" || return 1
  while IFS= read -r _fkr_k; do
    [ -n "${_fkr_k}" ] || continue
    _fkr_tgt="$(_fk_target "${_fkr_k}")" || { _fkr_rc=1; continue; }
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
${_fkr_keys}
EOF
  return "${_fkr_rc}"
}

_fk_emit_all() {
  _fk_validate_keys || return 1
  _fke_rc=0
  while IFS= read -r _fke_k; do
    [ -n "${_fke_k}" ] || continue
    _fk_validate_rows "${_fke_k}" || { _fke_rc=1; continue; }
    _fk_gen_block "${_fke_k}" || _fke_rc=1
  done < <(_fk_keys)
  return "${_fke_rc}"
}

_fk_check() {
  _fk_validate_keys || return 1
  _fkc_root="$(_fk_root)"; _fkc_rc=0
  while IFS= read -r _fkc_k; do
    [ -n "${_fkc_k}" ] || continue
    _fk_validate_rows "${_fkc_k}" || { _fkc_rc=1; continue; }
    _fkc_tgt="$(_fk_target "${_fkc_k}")" || { _fkc_rc=1; continue; }
    _fkc_path="${_fkc_root}/${_fkc_tgt}"
    [ -f "${_fkc_path}" ] || {
      echo "FACTKEY MISSING TARGET: ${_fkc_k} → ${_fkc_path} → fail-closed" >&2
      _fkc_rc=1; continue; }
    _fk_markers_ok "${_fkc_k}" "${_fkc_path}" "${_fkc_tgt}" || { _fkc_rc=1; continue; }
    # 🔴 生成結果先落變數並**驗 rc**，不得直接塞進 `[ = "$(...)" ]`〔CODEX-R1-P1-03〕：
    #   命令替換內的 rc 會被丟掉 ⇒ 生成失敗卻只比字串＝靜默通過。
    _fkc_want="$(_fk_gen_block "${_fkc_k}")" || {
      echo "FACTKEY GEN FAILED: ${_fkc_k}（生成器自身失敗，未與宿主檔比對）→ fail-closed" >&2
      _fkc_rc=1; continue; }
    _fkc_cur="$(sed -n "/^<!-- BEGIN GENERATED: ${_fkc_k} -->$/,/^<!-- END GENERATED: ${_fkc_k} -->$/p" \
                  "${_fkc_path}")"
    [ "${_fkc_cur}" = "${_fkc_want}" ] || {
      echo "FACTKEY DRIFT: ${_fkc_k} in ${_fkc_tgt}（宿主檔與 ${REG} 不一致；跑 --write 重生成）" >&2
      _fkc_rc=1; }
  done < <(_fk_keys)
  # 未登記之 generated block 一律拒〔CODEX-R1-P1-02〕
  _fk_reject_unregistered_blocks || _fkc_rc=1
  return "${_fkc_rc}"
}

_fk_write() {
  _fk_validate_keys || return 1
  _fkw_root="$(_fk_root)"; _fkw_rc=0
  while IFS= read -r _fkw_k; do
    [ -n "${_fkw_k}" ] || continue
    _fk_validate_rows "${_fkw_k}" || { _fkw_rc=1; continue; }
    _fkw_tgt="$(_fk_target "${_fkw_k}")" || { _fkw_rc=1; continue; }
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
