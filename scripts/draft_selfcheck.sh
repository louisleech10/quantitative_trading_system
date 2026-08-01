#!/usr/bin/env bash
# draft_selfcheck.sh — 治理草案「起草缺陷」機械自檢（起草端前移檢查）
#
# ── 為何存在 ──────────────────────────────────────────────────────────
# 線 B（凍結文件修訂程序）R1→R2→R3 三輪對抗審，委員反覆抓到的是**同四種結構缺陷**，
# 不是不同的新問題。每抓一次的成本 = 3 家派工 + 3 家戳記 = 6 次委員呼叫。
# 三輪下來，起草缺陷的偵測成本遠高於缺陷本身。
#
# 本腳本把「委員每輪都抓的同一件事」前移到起草端，機械擋在派工之前。
# 它**不取代**對抗審——它只負責讓委員不必再花一整輪講同一句話。
#
# ── 四條檢查（每條都有具名事故出處）──────────────────────────────────
# ① 死欄：schema 宣告了欄位，但 §oracle 表沒有任何一行提到它
#    → 「寫下欄位」被誤當成「有機制」。
#    事故：v0.2 `BASE-COMMIT`（CODEX-R2-P0-01，主委承認是死欄）
#         → v0.3 `stamped_by`／`manifest_blob`（GROK-R3-P0-01／CODEX-R3-P0-01）
#    **同型連犯兩版，且第二次發生在主委剛承認第一次之後。**
#
# ② OR 短路：fail-closed 斷言表的列同時含「rc=」與「或/OR」
#    → 實作者可讀成「前面條件失敗仍可靠後段放行」，把硬前置變成 fail-open。
#    事故：v0.3 §3.3 第 6 條（GROK-R3-P0-02，附偽碼反例）
#
# ③ 對照表孤兒：版本變更對照表宣稱的處置，正文找不到
#    → 「已修正」只存在於變更說明，實際規則沒改。
#    事故：v0.2 補遺規則只寫在對照表（COMPOSER-R2 群集 C）
#
# ④ 否決回歸：已被委員會否決的機制錨點，換個名目又出現在新版
#    事故：v0.1 reconcile 補遺 → v0.2 errata → v0.3 §4.4 又是 reconcile 補遺
#         （COMPOSER-R3-P0-01：「換標籤保留通道」）
#
# ── 用法 ──────────────────────────────────────────────────────────────
#   bash scripts/draft_selfcheck.sh <draft.md> [--rejected <tsv>] [--only 1|2|3|4|5]
#
# ── exit ──────────────────────────────────────────────────────────────
#   0 = 五條全過   1 = 有違反   2 = 用法／檔案錯（fail-closed）
#
# ── ⚠️ 本工具是 ADVISORY，不得作為安全邊界 ────────────────────────────
# R4 收斂裁定（`handoffs/reconcile/20260801-gov-amend-r4/synth.md` 群集 ε，三家 APPROVED，
# body sha 7074eb2c…）：
#   「`draft_selfcheck.sh` 只能是 advisory，不得作為安全邊界。
#     把可繞過的字面檢查掛成 gate 是製造程序假綠。
#     selfcheck PASS 不得單獨解除對抗審，也不得作為『可進實作』的依據。」
#
# 三家各自實跑的繞過（v0.4 當時全部 rc=0 假綠）：
#   ①「或」改寫成「／」 ②schema 移出 fenced block
#   ③新增空 `## §99` 並讓對照表指向它 ④`--rejected` 指向空 TSV
# 本版已針對四者收口，但**收口不等於不可繞過**——字面檢查永遠可被改寫繞過。
# 故：**禁止把本腳本 rc=0 當成派工／實作的放行條件。**
#
# ── 誠實邊界 ──────────────────────────────────────────────────────────
# * 本腳本是**字面匹配**，不理解語意。它擋的是「作者忘了」，不是「作者要騙」。
# * 覆蓋面小於病灶面：v0.4 §4.4「宣稱有機檢、實測不轉紅」是**散文**不是 schema 欄位，
#   檢查①抓不到。這是 R4 群集 α，由委員實跑 probe 才發現。
# * 檢查①寧可誤報：欄位在 oracle 表找不到字面對應即報。修法可以是補 oracle 行，
#   也可以是刪欄位——但**不接受「它其實有被讀到」這種口頭答覆**，因為 v0.2/v0.3
#   兩次死欄，主委當下都認為它有被讀到。
# * 檢查④依賴 `handoffs/gov_rejected_mechanisms.tsv` 是否被誠實維護；
#   該檔漏記 = 本檢查漏抓。它是 append-only 資產，不是自動生成。
# ---------------------------------------------------------------------------
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

usage() {
  echo "用法: bash scripts/draft_selfcheck.sh <draft.md> [--rejected <tsv>] [--only 1|2|3|4|5]" >&2
  exit 2
}

draft=""
rejected="handoffs/gov_rejected_mechanisms.tsv"
only=""

while [ $# -gt 0 ]; do
  case "$1" in
    # `--rejected` 覆寫僅測試 harness 可用。
    # 病灶（CODEX-R4-P1-02 實跑）：`--rejected` 指向空 TSV → 檢查④ rc=0 假綠。
    # 同 completeness_check.sh 的 COMPLETENESS_ALLOW_ARGV_SOURCES 設計：正式路徑 fail-closed。
    --rejected)
      shift; [ $# -gt 0 ] || usage
      if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
        echo "SELFCHECK FAIL: --rejected 覆寫僅 GOVERNANCE_TEST_HARNESS=1 可用（正式路徑拒受控清單替換）" >&2
        exit 2
      fi
      rejected="$1" ;;
    --only)     shift; [ $# -gt 0 ] || usage; only="$1" ;;
    -h|--help)  usage ;;
    -*)         echo "ERROR: 未知旗標: $1" >&2; usage ;;
    *)          [ -z "${draft}" ] || { echo "ERROR: 只接受一個草案檔" >&2; usage; }; draft="$1" ;;
  esac
  shift
done

[ -n "${draft}" ] || usage
[ -f "${draft}" ] || { echo "SELFCHECK FAIL: 草案檔不存在: ${draft}" >&2; exit 2; }

case "${only}" in ""|1|2|3|4|5) : ;; *) echo "ERROR: --only 只接受 1|2|3|4|5" >&2; exit 2 ;; esac

_want() { [ -z "${only}" ] || [ "${only}" = "$1" ]; }

VIOLATIONS=0
_fail() { VIOLATIONS=$((VIOLATIONS + 1)); echo "$*"; }

# 可預測暫存檔名（CODEX-R4-P1-02）→ 改 mktemp -d
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/selfcheck.XXXXXXXX")" || { echo "SELFCHECK FAIL: mktemp 失敗" >&2; exit 2; }
trap 'rm -rf "${TMPD}"' EXIT

echo "SELFCHECK 標的: ${draft}"
echo "SELFCHECK sha256: $(shasum -a 256 "${draft}" | awk '{print $1}')"
# 否決清單的 sha 一併印出供稽核：清單被削弱時使用者看得到（唯一寫入者仍是主委，見檔頭 ADVISORY 說明）
if [ -f "${rejected}" ]; then
  echo "SELFCHECK 否決清單: ${rejected} sha256:$(shasum -a 256 "${rejected}" | awk '{print $1}')"
fi
echo "---------------------------------------------------------------"

# ===========================================================================
# 檢查① 死欄：schema 欄位須在 oracle 表有字面對應
# ===========================================================================
if _want 1; then
  echo "【檢查① 死欄】schema 欄位 vs oracle 表"

  # oracle 區塊 = 標題含 "oracle"（不分大小寫）的 section，至下一個同級或更高級標題止
  awk '
    /^#{2,3}[[:space:]]/ {
      if (in_oracle) { if (match($0, /[Oo][Rr][Aa][Cc][Ll][Ee]/) == 0) in_oracle = 0 }
      if (match($0, /[Oo][Rr][Aa][Cc][Ll][Ee]/)) in_oracle = 1
    }
    in_oracle { print }
  ' "${draft}" > ${TMPD}/oracle 2>/dev/null

  if [ ! -s ${TMPD}/oracle ]; then
    _fail "SELFCHECK-1 FAIL: 找不到 oracle 區塊（標題須含 'oracle'）——無 oracle 表時所有欄位皆為死欄。"
  else
    # 抽 fenced block 內的 schema 欄位：
    #   (a) yaml 風格 `key:` / `- key:` / `{ key: ... }`
    #   (b) 大寫常數欄位 `BASE-BLOB:`
    awk '
      /^[[:space:]]*```/ { in_fence = !in_fence; next }
      !in_fence { next }
      {
        line = $0
        if (match(line, /^[[:space:]]*-?[[:space:]]*[A-Za-z_][A-Za-z0-9_]*:/)) {
          k = substr(line, RSTART, RLENGTH); gsub(/[[:space:]-]/, "", k); sub(/:$/, "", k); print k
        }
        if (match(line, /^[A-Z][A-Z0-9-]+:/)) {
          k = substr(line, RSTART, RLENGTH); sub(/:$/, "", k); print k
        }
        rest = line
        while (match(rest, /[{,][[:space:]]*[A-Za-z_][A-Za-z0-9_]*:/)) {
          k = substr(rest, RSTART, RLENGTH); gsub(/[{,[:space:]]/, "", k); sub(/:$/, "", k); print k
          rest = substr(rest, RSTART + RLENGTH)
        }
      }
    ' "${draft}" | sort -u > ${TMPD}/fields 2>/dev/null

    # 停用詞：過泛，字面比對無鑑別力
    STOPWORDS="id path bash sh git rg http https echo cat"

    n_dead=0
    while IFS= read -r field; do
      [ -n "${field}" ] || continue
      skip=0
      for sw in ${STOPWORDS}; do [ "${field}" = "${sw}" ] && skip=1; done
      [ "${skip}" = "1" ] && continue
      if ! grep -qF -- "${field}" ${TMPD}/oracle; then
        n_dead=$((n_dead + 1))
        lineno="$(grep -nF -- "${field}:" "${draft}" | head -1 | cut -d: -f1)"
        _fail "SELFCHECK-1 FAIL: 死欄 \`${field}\`（${draft}:${lineno:-?}）——宣告於 schema，但 oracle 表無任何一行提及。修法：補一條指名該欄位的三態 oracle，或刪除該欄位。"
      fi
    done < ${TMPD}/fields

    # 反繞過：schema 必須放在 fenced block 內，否則上面的抽取看不到它。
    # 病灶（GROK-R4-P1-04／CODEX-R4-P1-02 實跑）：把 `stamped_by:` 寫在 fence 外 → 檢查①假 PASS。
    # 判準：fence 外、行首形如 `key: <佔位符>`（值以 `<` 起始）＝ schema 定義的字面特徵。
    n_unfenced=0
    while IFS= read -r hit; do
      [ -n "${hit}" ] || continue
      n_unfenced=$((n_unfenced + 1))
      _fail "SELFCHECK-1 FAIL: schema 欄位定義在 fenced block 之外 → ${hit}"
      echo "    修法：把該 schema 移進 \`\`\` 區塊。fence 外的欄位定義**不會被死欄檢查掃到**，等於自動免檢。"
    done <<EOF
$(awk '
  /^[[:space:]]*```/ { in_fence = !in_fence; next }
  in_fence { next }
  /^[[:space:]]*[|>]/ { next }
  /^[[:space:]]*-?[[:space:]]*[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*</ { print NR ":" $0; next }
  /^[A-Z][A-Z0-9-]+:[[:space:]]*</ { print NR ":" $0 }
' "${draft}")
EOF

    [ "${n_dead}" = "0" ] && [ "${n_unfenced}" = "0" ] && echo "  PASS：所有 schema 欄位在 oracle 表皆有字面對應，且皆位於 fenced block 內。"
  fi
  rm -f ${TMPD}/oracle ${TMPD}/fields
  echo "---------------------------------------------------------------"
fi

# ===========================================================================
# 檢查② OR 短路：fail-closed 斷言表列同時含 rc= 與 或/OR
# ===========================================================================
if _want 2; then
  echo "【檢查② OR 短路】fail-closed 斷言表的分歧語意"
  # 只掃「規範性斷言表」所在 section（標題含 斷言／檢查器契約／硬前置）。
  # 不掃 oracle 表與說明表：那裡的「或」是在描述 fixture 或在講本檢查自己，
  # 不是判定條件的分歧語意（實測 v0.4：不收窄 → 3 條全誤報）。
  awk '
    /^#{2,6}[[:space:]]/ { in_sec = (match($0, /斷言/) || match($0, /檢查器契約/) || match($0, /硬前置/)) ? 1 : 0; next }
    in_sec { print NR ":" $0 }
  ' "${draft}" > ${TMPD}/assert 2>/dev/null
  n_or=0
  while IFS= read -r hit; do
    [ -n "${hit}" ] || continue
    n_or=$((n_or + 1))
    _fail "SELFCHECK-2 FAIL: 斷言表列含分歧語意（rc= 與 或/OR 同列）→ ${hit}"
  done <<EOF
$(grep -E '^[0-9]+:[[:space:]]*\|' ${TMPD}/assert | grep -E 'rc[=≠]' | awk '
  # 一定報：明確的選擇連接詞
  /或|否則|亦可|也可|[ ]OR[ ]|either/ { print; next }
  # 條件報：**全形**斜線當連接詞（GROK-R4-P1-04 實測「或 → ／」可繞過本檢查）。
  # 只認全形 `／`：半形 `/` 在斷言表大量出現於**檔案路徑**（`scripts/x.sh`），
  # 納入會 100% 誤報（實測 v0.5 的 A9 列即因 `scripts/reconcile_stamps_check.sh` 被誤報）。
  # 全形斜線在路徑中不會出現，故可安全視為連接詞。
  # 進一步折衷：該列已有「且」或「與」時視為連言，不報。
  # 誠實邊界：作者只要改用半形斜線或補一個「且」就能繞過本條——
  # 這是本工具只能 advisory 的又一個實例（R4 群集 ε）。
  /／/ { if ($0 !~ /且|與/) print }
')
EOF
  rm -f ${TMPD}/assert
  if [ "${n_or}" = "0" ]; then
    echo "  PASS：無 rc= 斷言列夾帶未定序的『或』。"
  else
    echo "  修法：把硬前置與內容支路拆成兩段明寫（哪幾條無例外 rc=2、哪一條才允許 OR），"
    echo "        並在 oracle 表加一條「短路實作 → 轉紅」的 mutant。"
  fi
  echo "---------------------------------------------------------------"
fi

# ===========================================================================
# 檢查③ 對照表孤兒：變更對照表宣稱的處置，正文須存在
# ===========================================================================
if _want 3; then
  echo "【檢查③ 對照表孤兒】變更對照表 vs 正文"

  # 對照表區塊 = 標題含「變更」或「相對」的 section，至下一個 ^## 止
  awk '
    /^#{2,3}[[:space:]]/ {
      if (in_tbl) { in_tbl = 0 }
      if (match($0, /變更/) || match($0, /相對/)) { in_tbl = 1; next }
    }
    in_tbl { print NR ":" $0 }
  ' "${draft}" > ${TMPD}/tbl 2>/dev/null

  if [ ! -s ${TMPD}/tbl ]; then
    echo "  SKIP：找不到變更對照表 section（標題含『變更』或『相對』）。"
  else
    # 判準（v0.2 事故的直接機械化）：
    #   對照表每一資料列的「處置」欄，必須指出至少一個 § 錨點，且該 § 標題須存在於正文。
    #   v0.2 的病正是「補遺規則寫在對照表、正文沒有對應 §」——處置無處可落地。
    #   不比對粗體文字全等：對照表用摘要措辭、正文用規範措辭，逐字比對 100% 誤報（實測）。
    n_orphan=0
    n_rows=0
    while IFS= read -r row; do
      [ -n "${row}" ] || continue
      ln="${row%%:*}"
      body="${row#*:}"
      # 只處理表格列（section 內的散文／空行／水平線一律不是對照表資料）
      printf '%s' "${body}" | grep -qE '^[[:space:]]*\|' || continue
      # 跳過表頭與分隔列
      printf '%s' "${body}" | grep -qE '^[[:space:]]*\|[[:space:]]*:?-{2,}' && continue
      printf '%s' "${body}" | grep -qE '^[[:space:]]*\|[[:space:]]*(v0\.[0-9]|群集|項|#|類別|機制)[[:space:]]*\|' && continue
      n_rows=$((n_rows + 1))
      # 最後一欄 = 處置欄
      action="$(printf '%s' "${body}" | awk -F'|' '{print $(NF-1)}')"
      anchors="$(printf '%s' "${action}" | grep -oE '§[0-9]+(\.[0-9]+)?[a-z]?' | sort -u)"
      if [ -z "${anchors}" ]; then
        n_orphan=$((n_orphan + 1))
        _fail "SELFCHECK-3 FAIL: 對照表第 ${ln} 列的處置未指向任何 § 錨點——無法追溯到正文位置。"
        echo "    處置欄: $(printf '%s' "${action}" | cut -c1-80)"
        continue
      fi
      for a in ${anchors}; do
        # 正文子節標題允許省略 §（實況：`### 4.2 ...` 與 `## §4 ...` 並存）
        a_num="${a#§}"
        hdr_ln="$(grep -nE "^#{2,4}[[:space:]]+§?${a_num}([[:space:]]|\(|（|$)" "${draft}" | head -1 | cut -d: -f1)"
        if [ -z "${hdr_ln}" ]; then
          n_orphan=$((n_orphan + 1))
          _fail "SELFCHECK-3 FAIL: 對照表孤兒——第 ${ln} 列宣稱處置落在 ${a}，但正文無該 § 標題。"
          continue
        fi
        # § 存在但內文空洞也是孤兒（GROK-R4-P1-04／brief 問項②：
        #   實測「新增空 `## §99` 並讓對照表指向它」→ 舊版 rc=0 假綠）。
        # 判準：該標題到下一個標題之間，實質內容行 ≥2（排除空行、水平線、單獨的 markdown 標記）。
        # 起始標題的層級：子節（更深的 #）算在該 § 的內文裡，遇到**同級或更高級**才停。
        # （實測 bug：v0.4 §3.3 的內容全在 `#### 3.3-A`／`3.3-B` 子節，
        #   若遇任何標題就停 → §3.3 被誤判成 1 行空殼。）
        hdr_depth="$(awk -v s="${hdr_ln}" 'NR==s { match($0, /^#+/); print RLENGTH; exit }' "${draft}")"
        body_lines="$(awk -v s="${hdr_ln}" -v d="${hdr_depth}" '
          NR <= s { next }
          /^#{1,6}[[:space:]]/ { match($0, /^#+/); if (RLENGTH <= d) exit; next }
          /^[[:space:]]*$/ { next }
          /^[[:space:]]*-{3,}[[:space:]]*$/ { next }
          { n++ }
          END { print n + 0 }
        ' "${draft}")"
        if [ "${body_lines:-0}" -lt 2 ]; then
          n_orphan=$((n_orphan + 1))
          _fail "SELFCHECK-3 FAIL: 對照表孤兒——第 ${ln} 列指向 ${a}（${draft}:${hdr_ln}），該 § 標題存在但**內文僅 ${body_lines:-0} 行實質內容**＝空殼落點。"
        fi
      done
    done < ${TMPD}/tbl

    [ "${n_orphan}" = "0" ] && echo "  PASS：對照表 ${n_rows} 列的處置皆指向正文存在的 § 錨點。"
  fi
  rm -f ${TMPD}/tbl
  echo "---------------------------------------------------------------"
fi

# ===========================================================================
# 檢查④ 否決回歸：已否決機制錨點不得以非「已刪」語境出現
# ===========================================================================
if _want 4; then
  echo "【檢查④ 否決回歸】已否決機制錨點"
  if [ ! -f "${rejected}" ]; then
    _fail "SELFCHECK-4 FAIL: 否決清單不存在: ${rejected}（fail-closed：無清單即無法證明沒有回歸）"
  else
    # 白名單語境：該行在講「已刪／禁用」
    NEGCTX='刪|禁止|不得|廢除|不再|已移除|不存在|已關閉|否決'
    n_regress=0
    while IFS="$(printf '\t')" read -r tok src reason; do
      case "${tok}" in ''|'#'*) continue ;; esac
      while IFS= read -r hit; do
        [ -n "${hit}" ] || continue
        ln="${hit%%:*}"
        body="${hit#*:}"
        if printf '%s' "${body}" | grep -qE "${NEGCTX}"; then continue; fi
        n_regress=$((n_regress + 1))
        _fail "SELFCHECK-4 FAIL: 否決機制回歸『${tok}』（${draft}:${ln}）——非『已刪／禁用』語境。"
        echo "    裁決來源: ${src}"
        echo "    否決理由: ${reason}"
        echo "    命中行  : $(printf '%s' "${body}" | cut -c1-90)"
      done <<EOF
$(grep -nF -- "${tok}" "${draft}")
EOF
    done < "${rejected}"
    [ "${n_regress}" = "0" ] && echo "  PASS：否決清單中的機制錨點皆未回歸。"
  fi
  echo "---------------------------------------------------------------"
fi

# ===========================================================================
# 檢查⑤ 無反例的機制效力宣稱
#
# 病灶（R4／R5 連續兩輪，這是主委錯誤的**真正根因**）：
#   v0.4 §4.4：「任何補遺 append 都會改變 body hash → 既有機檢**自動**轉紅」
#              → codex 與 grok 各自實跑證偽（append 在戳記後根本不進 hash）
#   v0.5 §4.4：「戳記開始之後只能是 STAMP 行，**故**『戳記後 append 覆寫裁決』**仍被擋**」
#              → 三家各自實跑證偽（`## 戳記` 與第一個 STAMP 之間可自由注入）
#
# R5 收斂的診斷：**不是不做驗證，是對驗證結果過度推論**——
#   把「測過的子集成立」寫成「整個機制成立」。
#   檢查①②③④ 全部檢查**結構**，對**推論**無能為力（R5 收斂具名記錄）。
#
# 判準：凡「機制效力宣稱」（同時含效力詞與因果詞的句子），
#   必須帶 `〔CLAIM:<oracle-id>〕` 標記，且該 id 須出現在 oracle 表。
#   ——把宣稱與反例用 ID 綁起來，與 canonical finding ID 同一套思路。
#
# 誠實邊界：本檢查抓的是「宣稱沒綁 oracle」，**抓不到「綁了但 oracle 本身不涵蓋該宣稱」**。
#   後者仍須委員實跑。本檢查只把「連綁都沒綁」這一層擋掉。
# ===========================================================================
if _want 5; then
  echo "【檢查⑤ 無反例宣稱】機制效力宣稱 vs oracle 綁定"
  # 本檢查自建 oracle 區塊（檢查①的暫存已在其結束時清掉，且 --only 5 時不會跑檢查①）
  awk '
    /^#{2,3}[[:space:]]/ {
      if (in_oracle) { if (match($0, /[Oo][Rr][Aa][Cc][Ll][Ee]/) == 0) in_oracle = 0 }
      if (match($0, /[Oo][Rr][Aa][Cc][Ll][Ee]/)) in_oracle = 1
    }
    in_oracle { print }
  ' "${draft}" > ${TMPD}/oracle5 2>/dev/null
  n_claim=0
  while IFS= read -r hit; do
    [ -n "${hit}" ] || continue
    ln="${hit%%:*}"
    body="${hit#*:}"
    # 已帶標記者，驗證該 oracle-id 存在於 oracle 表
    if printf '%s' "${body}" | grep -q '〔CLAIM:'; then
      cid="$(printf '%s' "${body}" | sed -n 's/.*〔CLAIM:\([^〕]*\)〕.*/\1/p')"
      if [ -z "${cid}" ]; then
        n_claim=$((n_claim + 1))
        _fail "SELFCHECK-5 FAIL: ${draft}:${ln} 的 〔CLAIM:〕 標記為空。"
      elif ! grep -qF -- "${cid}" ${TMPD}/oracle5 2>/dev/null; then
        n_claim=$((n_claim + 1))
        _fail "SELFCHECK-5 FAIL: ${draft}:${ln} 宣稱綁定 oracle \`${cid}\`，但 oracle 表無該 id。"
      fi
      continue
    fi
    n_claim=$((n_claim + 1))
    _fail "SELFCHECK-5 FAIL: 無反例的機制效力宣稱（${draft}:${ln}）"
    echo "    句子: $(printf '%s' "${body}" | cut -c1-100)"
    echo "    修法：①加 〔CLAIM:<oracle-id>〕 並在 oracle 表補一列可執行反例；或②刪除該因果宣稱。"
    echo "    〔R5 診斷：v0.4 與 v0.5 的 BLOCKING 都是這一型——測了子集，寫成整個機制成立。〕"
  done <<EOF
$(awk '
  /^#{2,6}[[:space:]]/ {
    # 敘述性小節不掃：那裡談的是歷史事故與邊界，本來就沒有 oracle
    skip = (match($0, /誠實邊界/) || match($0, /為何存在/) || match($0, /背景/) || \
            match($0, /具名記錄/) || match($0, /成本/) || match($0, /要解的問題/) || \
            match($0, /病灶/) || match($0, /覆蓋面/) || match($0, /已知繞過/) || \
            match($0, /定位/)) ? 1 : 0
    next
  }
  skip { next }
  /^[[:space:]]*[|>]/ { next }
  # 效力詞 且 因果詞 同句 → 機制效力宣稱
  /被擋|擋下|涵蓋|轉紅|fail-closed|拒發|失效/ {
    if ($0 ~ /故|所以|因此|即可|自動|仍|保證|必然/) print NR ":" $0
  }
' "${draft}")
EOF
  if [ "${n_claim}" = "0" ]; then
    echo "  PASS：所有機制效力宣稱皆已綁定 oracle（或無此類宣稱）。"
  fi
  echo "---------------------------------------------------------------"
fi

if [ "${VIOLATIONS}" -gt 0 ]; then
  echo "SELFCHECK FAIL: ${VIOLATIONS} 條違反。**修完再派委員**——這些是委員每輪都會抓到的同一批缺陷。"
  exit 1
fi

echo "SELFCHECK PASS: 五條起草缺陷檢查全過（不代表設計正確，只代表不再犯同四種結構錯）。"
exit 0
