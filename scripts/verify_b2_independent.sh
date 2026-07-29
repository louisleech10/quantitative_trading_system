#!/usr/bin/env bash
# B2 獨立驗收（主委端，不採信實作端自報）
#
# 專攻 B2 的四個坑（SPEC/TODO 明列、且此前在 SPEC 層與 TODO 層各犯過一次）：
#   ①缺 shift → session 名被當事件參數
#   ②內部函式自行取鎖 → 自鎖
#   ③rc 不傳播 → 失敗被 _release_lock 的 rc=0 吞掉
#   ④三態誤判 → 掃描出錯時照樣 append
# 判定一律【比對專屬錯誤訊息或落地事實】，不只看 rc
# （本專案反覆犯的病：用比待驗行為更寬的訊號當通過條件）。
set -uo pipefail
S=scripts/audit_append.sh
fail=0
ok(){ printf '  ✅ %s\n' "$1"; }
bad(){ printf '  ❌ %s\n' "$1"; fail=1; }

echo "=== 0. 檔案與語法 ==="
[ -f "$S" ] && ok "audit_append.sh 存在" || { bad "缺檔"; exit 1; }
bash -n "$S" && ok "語法 OK" || bad "語法錯"

# ⚠️ 一律對【剝除註解後】的碼做判定。
#    首版直接 grep 全檔，把「# 禁 flock」的註解判成「使用了 flock」、
#    把契約說明註解判成「*_locked() 內取鎖」——兩者皆誤報，實作其實正確。
#    這是本專案反覆犯的同型病：用比待驗行為更寬的訊號當通過條件（第 4 次）。
CODE="$(mktemp)"; trap 'rm -f "$CODE"' EXIT
sed 's/[[:space:]]*#.*$//' "$S" | grep -v '^[[:space:]]*$' > "$CODE"

echo "=== 1. 坑①：shift（session 名不得被當事件參數）==="
grep -qE 'shift' "$S" && ok "有 shift" || bad "缺 shift"

echo "=== 2. 坑②：內部函式不得自行取鎖（自鎖）==="
# lock-held 內部函式（*_locked）內不得出現取鎖呼叫
if awk '/_locked\(\)/{inf=1} inf && /_acquire_lock/{found=1} /^}/{inf=0} END{exit(found?0:1)}' "$CODE" >/dev/null; then
  bad "*_locked() 內出現 _acquire_lock（自鎖風險）"
else
  ok "*_locked() 內無取鎖呼叫"
fi
grep -qE 'reentrant|鎖交接' "$S" && printf '  ⚠️  檔內提及 reentrant/鎖交接，請人工確認非實作而是禁令說明\n' || true

echo "=== 3. 坑③：rc 傳播（_release_lock 不得吞掉失敗）==="
grep -qE 'rc=\$\?' "$S" && ok "有捕捉 rc" || bad "未捕捉 rc"
grep -qE 'return[[:space:]]+"?\$\{?rc' "$S" && ok "有回傳捕捉到的 rc" || bad "未回傳 rc（失敗會被吞）"

echo "=== 4. 坑④：三態（掃描錯誤須 fail-closed，不得當成沒找到）==="
grep -qE 'case[[:space:]]+\$\?[[:space:]]+in' "$S" && ok "掃描結果用 case 三態判定" || bad "未見三態 case（可能把非零全當沒找到）"

echo "=== 5. 憲法：禁 flock／禁 declare -A ==="
grep -qE "(^|[^a-z_])flock" "$CODE" && bad "使用了 flock（macOS 無此指令）" || ok "未用 flock"
grep -q "declare -A" "$CODE" && bad "使用了 declare -A（bash 3.2 不支援）" || ok "未用 declare -A"

echo "=== 6. 反 bypass：新增 env override 須綁 harness ==="
# ⚠️ 不得只掃 `*_OVERRIDE` 命名（CODEX-R1-P2-05 實證漏抓）：
#    憲法管的是「**任何**新增 env override」，不是特定命名。
#    實例：AUDIT_APPEND_MAX_RETRY / AUDIT_APPEND_RETRY_INTERVAL 未綁 harness，
#    首版檢查因只認 *_OVERRIDE 而完全漏掉（本 session 第 5 次「訊號比待驗行為更寬」）。
#    改為：掃所有【被讀取的大寫 env】，扣掉既有白名單，逐一要求 harness 綁定。
_ENV_WHITELIST='GOVERNANCE_TEST_HARNESS|HOME|PATH|PWD|USER|SHELL|TMPDIR|LANG|LC_[A-Z]+'
#    判準＝【被賦值給區域變數、且用 `${X:-default}` 形式讀取的大寫名】才算 env override；
#    腳本自己的區域變數（LOCKDIR/EVENT_NAME…）只是被展開，不是外部可注入面，不算。
#    (首版把所有大寫展開都算，誤報一堆內部變數——過寬與過窄都要修)
envs=$(grep -oE '=["'"'"']?\$\{[A-Z][A-Z0-9_]+:-[^}]*\}' "$CODE" \
       | sed 's/^=["'"'"']*\${//; s/:-.*//' | sort -u \
       | grep -vE "^(${_ENV_WHITELIST})$" || true)
if [ -n "$envs" ]; then
  # 逐一要求：該 env 名出現的同一段（±6 行）內須有 GOVERNANCE_TEST_HARNESS 檢查
  for e in $envs; do
    ln=$(grep -n "\${${e}[:-}]" "$CODE" | head -1 | cut -d: -f1)
    [ -z "$ln" ] && continue
    lo=$((ln>6?ln-6:1)); hi=$((ln+6))
    if sed -n "${lo},${hi}p" "$CODE" | grep -q 'GOVERNANCE_TEST_HARNESS'; then
      ok "env ${e} 有 harness 綁定（±6 行內）"
    else
      bad "env ${e} 未綁 GOVERNANCE_TEST_HARNESS（違反反 bypass 紅線）"
    fi
  done
else
  ok "未新增任何 env override"
fi

echo "=== 6b. 空值不得跳過守衛（CODEX-R2-P1-01）==="
# 事故：REQUIRE_ABSENT_SESSION 預設空字串，判定用 `[ -n ... ]`
#   ⇒ 傳 `--require-absent-session ""` 等同沒傳，唯一性守衛整個被跳過（probe rows=2）。
#   通則：**「有沒有傳這個旗標」不可用「值是否非空」代替**——旗標出現即須生效。
if grep -qE '^[[:space:]]*if[[:space:]]+\[[[:space:]]+-n[[:space:]]+"\$\{REQUIRE_ABSENT_SESSION\}"' "$CODE"; then
  bad "唯一性守衛用 [ -n ] 判定 → 空值可跳過（須改為「旗標出現即生效」並拒空值）"
else
  ok "唯一性守衛未用「值非空」代替「旗標出現」"
fi

echo "=== 7. 範圍：不得越界做 B3–B5 ==="
for f in scripts/debt_ledger.sh scripts/debt_clear.sh; do
  [ -f "$f" ] && bad "越界新增 $f（屬 B4）" || ok "未新增 $(basename "$f")"
done
git diff --name-only -- scripts/gate.sh | grep -q . && bad "動了 gate.sh（屬 B5）" || ok "未動 gate.sh"

echo "=== 8. 防假綠：既有測試斷言未被刪 ==="
# grep -c 未命中時 stdout 已是 0 但 rc=1；`|| echo 0` 會再補一個 0 → "0\n0" 使 [ 炸。
# 用 `|| true` 吞 rc，勿再補印（CLAUDE.md 已載此坑，起草者又犯一次）。
n=$(git diff -- tests/ | grep -cE "^-.*assert" || true)
# ⚠️ 全形括號緊接 $n 會被 bash 併進變數名（本 session 第 2 次），一律用 ${n}
[ "${n}" -eq 0 ] && ok "既有測試無 assert 被刪（${n}）" || bad "有 ${n} 行 assert 被刪"

echo
[ "$fail" = 0 ] && echo "B2 INDEPENDENT VERIFY PASS" || echo "B2 INDEPENDENT VERIFY FAIL"
exit "$fail"
