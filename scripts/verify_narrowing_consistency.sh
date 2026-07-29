#!/usr/bin/env bash
# 「收窄後語意一致性」檢查——實跑行為對帳文件斷言。
#
# ═══════════════════════════════════════════════════════════════════
# 2026-07-29 重寫：**改用固定文法，不再 parse 散文**（使用者裁決）
#
# 沿革（為何要重寫）：
#   v2.9 把 audit 反查從「建立 session 時」收窄為「產生 review lock 時」，
#   但 SPEC/TODO 的【驗證段】仍寫「不存在 session → rc≠0」(無條件) ⇒ 條文與行為相反。
#   起草者寫字串比對想機械對帳，**被 codex 連六輪用不同散文形式打穿**：
#     R6 整行掩護 → R7 半形 ;/,、跨行、後綴否定 → R8 全形逗號 → R9 全形冒號
#     → R10 前綴否定 → R11「不帶/不加/不使用/不需要」
#   期間起草者還自撞一次：改成「整類標點全切」導致斷言碎裂，攻法④ 退回假綠。
#   **根因＝拿字串比對去 parse 無界的散文形式空間。補丁永遠追不完。**
#
# 使用者裁決：條件式驗收斷言一律用固定文法（SPEC §C「驗收斷言文法」）：
#     ASSERT <命令> WHEN <key>=<value> ... THEN rc=<n>|rc!=<n>
#   機檢規則簡化成一句話：
#     **驗證段裡每一次提到受管命令，都必須在 ASSERT 行內；散文中出現即 FAIL。**
#   ⇒ 不需切段、不需判否定、不需處理標點 ⇒ **逃脫點從「無限」降為「零」**。
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail
fail=0
MANAGED='reconcile_build'          # 受管命令（條件式行為者）
PROBE="handoffs/_narrowprobe_$$"   # repo-local（外部 /tmp 會被 sandbox 拒）
trap 'rm -rf "$PROBE"' EXIT
mkdir -p "$PROBE"
SRC="$PROBE/x-codex.md"
printf '## CODEX-R1-P2-01\n\n**斷言**: probe\n\n**來源摘要**: probe#0000\n\n[MINOR] probe\n' > "$SRC"

# ── 1. 實跑行為（真 oracle）─────────────────────────────────────
echo "=== 實跑：audit 中不存在的 session 名 ==="
# 判定依據＝【是否被 audit 反查拒絕】，不是 rc：
#   合成探針的 finding 過不了 completeness，reconcile_build 照樣回 rc=1。
#   用 rc 當訊號會把「completeness 失敗」誤判成「audit 拒絕」（本腳本首版即如此誤報）。
_REJECT='session_name 命中'
NAME="_narrow_unknown_$$"

bash scripts/reconcile_build.sh "$NAME" "$SRC" > "$PROBE/disc.log" 2>&1
disc_rej=0; grep -q "$_REJECT" "$PROBE/disc.log" && disc_rej=1
disc_built=0; [ -d "handoffs/reconcile/$NAME" ] && disc_built=1
rm -rf "handoffs/reconcile/$NAME"

bash scripts/reconcile_build.sh "${NAME}b" --mode review "$SRC" > "$PROBE/rev.log" 2>&1
rev_rej=0; grep -q "$_REJECT" "$PROBE/rev.log" && rev_rej=1
rm -rf "handoffs/reconcile/${NAME}b"

printf '  mode=discovery：被 audit 反查拒絕=%s，session 建成=%s（應 0/1）\n' "$disc_rej" "$disc_built"
printf '  mode=review   ：被 audit 反查拒絕=%s（應 1）\n' "$rev_rej"
if [ "$disc_rej" -eq 0 ] && [ "$disc_built" -eq 1 ]; then
  echo "  ✅ discovery 不做 audit 反查且能建 session（bootstrap P0 未復活）"
else echo "  ❌ discovery 被 audit 反查擋住 → bootstrap P0 復活"; fail=1; fi
if [ "$rev_rej" -eq 1 ]; then
  echo "  ✅ review 無對應開債 → 被 audit 反查拒絕（identity binding 生效）"
else echo "  ❌ review 未被 audit 反查拒絕 → identity binding 失效"; fail=1; fi

# ── 2. 文件斷言：固定文法（取代所有散文 parsing）───────────────
echo "=== 文件斷言：受管命令是否都在 ASSERT 行內 ==="
for f in docs/P16_COMMITTEE_DEBT_SPEC.md docs/P16_COMMITTEE_DEBT_TODO.md; do
  # 抽驗證段整塊（`- **驗證` 起，到下一個 bullet 或空行止）
  block=$(awk '
    /^[[:space:]]*[-*][[:space:]]*\*\*驗證/ { inb=1; print; next }
    inb && /^[[:space:]]*[-*][[:space:]]*\*\*/ { inb=0; next }
    inb { print; next }
  ' "$f")
  # 規則：只要求【條件式】斷言用 ASSERT——即同時出現「受管命令」與「模式關鍵字」者。
  #   非條件式驗收（如 `reconcile_build --help` 印出旗標）維持散文，不受此限（SPEC §C 已界定範圍）。
  #   注意：此處只判「有沒有模式關鍵字」這一個布林，**不解析散文形式**，
  #        故不受標點／否定／跨行等繞法影響（那正是前六輪被打穿的原因）。
  #   規則＝**嚴格**：驗收段每次提到受管命令都必須在 ASSERT 行內，
  #   只有【明確白名單】可例外。**不得**改用「含某些關鍵字才要求」的啟發式——
  #   CODEX-R12-P1-01 實證：那樣用 session=/round=/audit=/harness= 寫的條件式散文會溜過去。
  #   白名單（非條件式，不涉行為分支）：`--help`（只驗輸出含哪些旗標字串）。
  #   （起草者一度想把文件裡的命令字串拆開來躲過本檢查——那是騙自己且會讓文件裡的
  #     指令複製貼上即錯。**檢查誤報就修檢查或加白名單，不准改壞文件。**）
  #   白名單收窄（CODEX-R13-P1-01）：`--help` 只在【該行不含任何條件鍵】時才放行，
  #   否則 `reconcile_build --help WHEN ...` 可整行夾帶條件式語意溜過。
  #   另補：驗收段中**不提命令名**但含條件鍵的散文，同樣要抓（否則省略命令名即可完全避開）。
  bad=$(printf '%s\n' "$block" | grep -n "$MANAGED" \
        | grep -vE '\-\-help([^=]*$|[^=]*[^a-z_]=)' \
        | grep -v 'ASSERT' || true)
  # 「省略命令名」的條件式散文（CODEX-R13-P1-01 後半）：
  #   只在【本身已含受管命令 ASSERT 的驗收區塊】內掃，且需同時有 rc 宣稱才算斷言。
  #   限縮理由：其他命令（如 debt_clear）目前仍用散文寫條件式驗收，
  #   那是**已登記的待轉換項**（SPEC §A 誠實邊界），不在本次受管範圍，不應在此誤報。
  if printf '%s\n' "$block" | grep -q "ASSERT[[:space:]]*$MANAGED"; then
    bad2=$(printf '%s\n' "$block" \
          | grep -nE '(^|[^a-z_.])(session|mode|from|to|round|audit|rebuild|harness)=' \
          | grep -E 'rc≠0|rc!=0|rc=0' | grep -v 'ASSERT' || true)
    [ -n "$bad2" ] && bad="${bad}
${bad2}"
  fi
  if [ -n "$bad" ]; then
    printf '  ❌ %s 驗證段有【不在 ASSERT 行內】的 %s：\n' "$f" "$MANAGED"
    printf '%s\n' "$bad" | head -3 | sed 's/^/       /' | cut -c1-120
    fail=1
  else
    n=$(printf '%s\n' "$block" | grep -c "^[[:space:]]*ASSERT[[:space:]]*$MANAGED" || true)
    printf '  ✅ %s 驗證段：%s 個 ASSERT 行，散文中 0 處 %s\n' "$f" "$n" "$MANAGED"
  fi
done

# ── 3. ASSERT 行文法合規 + 必須涵蓋 discovery 正向 ───────────────
echo "=== ASSERT 行文法與覆蓋 ==="
# 排除 §C 的文法【範本】行（含 <> 佔位符），它不是斷言
al=$(grep -h "^[[:space:]]*ASSERT[[:space:]]" docs/P16_COMMITTEE_DEBT_SPEC.md | grep -v '<' || true)
if [ -z "$al" ]; then echo "  ❌ SPEC 無任何 ASSERT 行"; fail=1; fi
# 條件鍵詞彙表（新增鍵須同步此表，避免打錯字靜默通過）
VOCAB='session mode from to round audit rebuild harness lock.mode'
POST_VOCAB='lock.mode lock.round_id lock.sources lock.hashes lock.roster'
while IFS= read -r a; do
  [ -z "$a" ] && continue
  a=$(printf '%s' "$a" | tr '\t' ' ')   # tab 正規化（CODEX-R13-P1-03：tab 分隔可繞重複鍵檢查）
  # 1) 語法
  printf '%s' "$a" | grep -qE '^[[:space:]]*ASSERT[[:space:]]+[A-Za-z_][A-Za-z0-9_]*([[:space:]]+WHEN([[:space:]]+[a-z_]+=[a-z0-9_!]+)+)?[[:space:]]+THEN[[:space:]]+rc(=|!=)[0-9]+([[:space:]]+AND[[:space:]]+[a-z_.]+=[a-z0-9_!]+)*[[:space:]]*$' \
    || { printf '  ❌ 文法不合：%s\n' "$(printf '%s' "$a" | cut -c1-100)"; fail=1; continue; }
  # 2) 條件鍵須在詞彙表內（CODEX-R12-P1-02：防打錯字/自創鍵靜默通過）
  keys=$(printf '%s' "$a" | sed 's/.*WHEN//; s/THEN.*//' | tr ' ' '\n' | grep '=' | cut -d= -f1 | grep -v '^$' || true)
  for k in $keys; do
    printf '%s' " $VOCAB " | grep -q " $k " \
      || { printf '  ❌ 未知條件鍵 `%s`：%s\n' "$k" "$(printf '%s' "$a" | cut -c1-90)"; fail=1; }
  done
  # 3) 同一 ASSERT 不得重複鍵（CODEX-R12-P1-02：`mode=review mode=discovery` 自相矛盾）
  dup=$(printf '%s\n' $keys | sort | uniq -d || true)
  [ -n "$dup" ] && { printf '  ❌ 重複條件鍵 `%s`（自相矛盾）：%s\n' "$dup" "$(printf '%s' "$a" | cut -c1-80)"; fail=1; }
  # 4) AND 後置條件鍵：詞彙表 + 不得重複（CODEX-R13-P1-03）
  pkeys=$(printf '%s' "$a" | grep -oE 'AND[[:space:]]+[a-z_.]+=' | sed 's/AND[[:space:]]*//; s/=$//' || true)
  for k in $pkeys; do
    printf '%s' " $POST_VOCAB " | grep -q " $k " \
      || { printf '  ❌ 未知後置條件鍵 `%s`：%s\n' "$k" "$(printf '%s' "$a" | cut -c1-80)"; fail=1; }
  done
  pdup=$(printf '%s\n' $pkeys | sort | uniq -d || true)
  [ -n "$pdup" ] && { printf '  ❌ 重複後置條件鍵 `%s`：%s\n' "$pdup" "$(printf '%s' "$a" | cut -c1-70)"; fail=1; }
done < <(printf '%s\n' "$al")
# ── 4) ★ 交叉對照：ASSERT 宣稱 vs 本腳本實測（CODEX-R13-P1-02）──────
#    原本兩段各跑各的、從不比對 ⇒ 文件把 review/discovery 寫反照樣 PASS。
#    此處把上面量到的真實行為，拿去驗對應 ASSERT 的 rc 宣稱。
echo "=== 交叉對照：ASSERT 宣稱 vs 實測行為 ==="
_claim() {  # _claim <mode> → 印出該情境 ASSERT 宣稱的 rc 記號(rc=0 / rc!=0)
  printf '%s\n' "$al" | grep "session=absent" | grep "mode=$1" \
    | grep -oE 'THEN[[:space:]]+rc(=|!=)[0-9]+' | head -1 | sed 's/THEN[[:space:]]*//'
}
c_disc=$(_claim discovery); c_rev=$(_claim review)
# 實測：disc_rej=0 且 disc_built=1 ⇒ 行為等同 rc=0（建得成）；rev_rej=1 ⇒ 行為等同 rc!=0
m_disc="rc!=0"; [ "$disc_rej" -eq 0 ] && [ "$disc_built" -eq 1 ] && m_disc="rc=0"
m_rev="rc=0";   [ "$rev_rej" -eq 1 ] && m_rev="rc!=0"
printf '  mode=discovery：文件宣稱 %-6s ／ 實測 %-6s\n' "${c_disc:-<缺>}" "$m_disc"
printf '  mode=review   ：文件宣稱 %-6s ／ 實測 %-6s\n' "${c_rev:-<缺>}"  "$m_rev"
[ -n "$c_disc" ] || { echo "  ❌ 缺 session=absent mode=discovery 的 ASSERT"; fail=1; }
[ -n "$c_rev" ]  || { echo "  ❌ 缺 session=absent mode=review 的 ASSERT"; fail=1; }
[ "$c_disc" = "$m_disc" ] || { echo "  ❌ discovery：文件宣稱與實測【不一致】"; fail=1; }
[ "$c_rev" = "$m_rev" ]   || { echo "  ❌ review：文件宣稱與實測【不一致】"; fail=1; }
[ "$c_disc" = "$m_disc" ] && [ "$c_rev" = "$m_rev" ] && echo "  ✅ 兩條情境的文件宣稱與實測一致"

printf '%s\n' "$al" | grep -q 'mode=discovery' \
  && echo "  ✅ 含 mode=discovery 的正向斷言（收窄的正向驗收）" \
  || { echo "  ❌ 缺 mode=discovery 正向斷言（不驗就等於沒驗收窄）"; fail=1; }
printf '%s\n' "$al" | grep -q 'mode=review' \
  && echo "  ✅ 含 mode=review 的 fail-closed 斷言" \
  || { echo "  ❌ 缺 mode=review 斷言"; fail=1; }

echo
if [ "$fail" = 0 ]; then
  echo "NARROWING CONSISTENCY PASS"
  echo "  文件斷言採固定文法（SPEC §C），不再 parse 散文 ⇒ 標點／否定／跨行等散文繞法皆不適用。"
else
  echo "NARROWING CONSISTENCY FAIL"
fi
exit "$fail"
