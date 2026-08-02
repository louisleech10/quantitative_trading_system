#!/usr/bin/env bash
# verdict_filled_check.sh — 「Verdict 是否已填實」的**唯一實作**。
#
# 出生理由（2026-08-03）：同一判準有兩個消費點——
#   ① `gate.sh` 的 D-1（派工前驗 `--adversarial` 檔）
#   ② `doc_format_precheck.sh`（收斂檔 `synth.md` 寫檔當下）
# 複製一份到第二個呼叫點＝第二真相源，必然漂移（本 repo 已因此吃過多次虧）。
#
# 判準（三條同時成立才算「已填實」；出處＝P16-GATE-D1-STRUCTURED-VERDICT 兩次事故）：
#   (a) 行首錨定，允許 markdown 結構前綴：空白／`#`／單一 `[-+*]`／`N.`／`N)`（**皆須後接空白**）
#       ＋ emphasis `*+`（不要求空白）。**不含 `>`（blockquote）**——全語料中 `>` 開頭含 Verdict
#       的行全為散文提及，放行等於重開散文誤判洞。
#   (b) 容許 `Verdict` 與冒號之間有括號補充（修「Verdict（綜合）：」被誤拒的事故），但不得跨越冒號。
#   (c) 冒號後須有**非佔位**實質內容：不得為 `{{…}}`／待填／TBD／xxx／`…`／`（待填）`／`← 未填`。
#
# 刻意不設「結論最短長度」：兩次事故皆與長度無關，無事故支撐即不立規則；
#   且會誤拒 `Verdict: OK`／`Verdict: 過`，另 BSD awk length() 按位元組計，該規則在 CJK 上本就不成立。
# 誠實邊界：不驗結論真偽、不驗枚舉、不做 markdown fence 解析
#   （fenced code block 內的 `Verdict: X` 仍被接受＝`CODEX-R1-P2-02`，已知且明示）。
#
# 用法：bash scripts/verdict_filled_check.sh <file>
# rc: 0=有已填實的 Verdict；1=沒有；2=用法錯／檔不存在
set -u

f="${1:-}"
[ -n "${f}" ] || { echo "用法: bash scripts/verdict_filled_check.sh <file>" >&2; exit 2; }
[ -f "${f}" ] || { echo "ERROR: 檔不存在: ${f}" >&2; exit 2; }

awk '
    {
      line = $0
      # 逐層剝除行首結構前綴（含巢狀，如「  - **Verdict**: X」）。
      # 終止性：每輪至少刪一個行首字元、字串嚴格變短，否則 line==before 離開。
      do {
        before = line
        sub(/^[[:space:]]+/, "", line)
        sub(/^[#]+[[:space:]]+/, "", line)        # heading：# 後須空白
        sub(/^[-+*][[:space:]]+/, "", line)       # 無序清單：單一 marker + 空白
        sub(/^[0-9]+[.)][[:space:]]+/, "", line)  # 有序清單：N. / N) + 空白
        sub(/^\*+/, "", line)                     # emphasis：**Verdict** 之類
      } while (line != before)
      if (line !~ /^Verdict/) next
      if (match(line, /[:：]/) == 0) next
      prefix = substr(line, 1, RSTART - 1)
      gsub(/[[:space:]]|\*/, "", prefix)
      if (prefix !~ /^Verdict(\(.*\)|（.*）)?$/) next
      rest = substr(line, RSTART + RLENGTH)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", rest)
      gsub(/\*/, "", rest)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", rest)
      if (rest == "") next
      if (rest ~ /\{\{/) next
      if (rest ~ /^[(（][[:space:]]*(待填|TBD|xxx|XXX|填此)/) next
      if (rest ~ /^(待填|TBD|tbd|xxx|XXX|填此|未填)/) next
      if (rest ~ /←[[:space:]]*未填/) next
      if (rest ~ /^\.\.\.$/ || rest ~ /^…$/) next
      found = 1
      exit
    }
    END { exit(found ? 0 : 1) }' "${f}"
