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
CODE="$(mktemp)"
_V7_TMP=""
trap 'rm -f "$CODE"; [ -n "${_V7_TMP}" ] && rm -rf "${_V7_TMP}"' EXIT
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

echo "=== 7. gate.sh 債務閘語意 scope（B5 合法 hunk；拒其他漂移）==="
# B2–B4 期間 §7 禁改 gate.sh。B5 Task 3.1 合法加債務閘後，兩層缺一不可：
#   層 A 靜態錨點（定義／呼叫點／位置／非 early-return stub／既有護欄字樣）
#   層 B 行為 oracle：隔離副本塞真 OPEN 債 → gate.sh dispatch 必須 rc≠0
#        （反轉 OPEN 分支 return 1→0 時此 oracle 必須轉紅——靜態錨點抓不到）
#   層 C 範圍：剝除 B5 授權區後 residual 必須 == HEAD gate.sh（授權區外漂移 → 報錯）
# 不得只保留靜態錨點（CODEX-R2-P1-03）。
GATE_SH=scripts/gate.sh
if ! grep -qE '^_check_open_debt\(\)' "${GATE_SH}"; then
  bad "gate.sh 缺 _check_open_debt() 定義（B5 Task 3.1）"
else
  ok "gate.sh 定義 _check_open_debt()"
fi
# 非註解呼叫次數（定義行不含；註解行略過）
n_call=$(awk '
  /^[[:space:]]*#/ { next }
  /^_check_open_debt\(\)/ { next }
  /_check_open_debt/ { c++ }
  END { print c+0 }
' "${GATE_SH}")
if [ "${n_call}" -eq 1 ]; then
  ok "gate.sh 非註解 _check_open_debt 呼叫恰 1 次"
else
  bad "gate.sh 非註解 _check_open_debt 呼叫數=${n_call}（須恰 1）"
fi
if grep -qE '^[[:space:]]+_check_open_debt \|\| exit 1[[:space:]]*$' "${GATE_SH}"; then
  ok "gate.sh 呼叫形狀為 _check_open_debt || exit 1"
else
  bad "gate.sh 呼叫形狀不符（須 _check_open_debt || exit 1）"
fi
# 行序：dispatch 分支「template 必填 miss」< 債務呼叫 < 「第一次實際呼叫 _run_completeness_gate」
line_miss=$(grep -nE 'miss template[[:space:]]' "${GATE_SH}" | head -1 | cut -d: -f1)
line_debt=$(grep -nE '^[[:space:]]+_check_open_debt \|\| exit 1[[:space:]]*$' "${GATE_SH}" | head -1 | cut -d: -f1)
line_comp=$(grep -nE '^[[:space:]]*_run_completeness_gate ' "${GATE_SH}" | head -1 | cut -d: -f1)
if [ -n "${line_miss}" ] && [ -n "${line_debt}" ] && [ -n "${line_comp}" ] \
  && [ "${line_miss}" -lt "${line_debt}" ] && [ "${line_debt}" -lt "${line_comp}" ]; then
  ok "gate.sh 債務閘位置：必填之後、completeness 之前（${line_miss}<${line_debt}<${line_comp}）"
else
  bad "gate.sh 債務閘位置不正確 miss=${line_miss} debt=${line_debt} comp=${line_comp}"
fi
# 函式體必須真的呼叫 debt_ledger --has-open；拒 early-return stub
body_snip=$(awk '
  /^_check_open_debt\(\)/ { in_fn=1; next }
  in_fn && /^if \[/ { exit }
  in_fn && /^[a-zA-Z_][a-zA-Z0-9_]*\(\)/ { exit }
  in_fn { print }
' "${GATE_SH}")
if printf '%s' "${body_snip}" | grep -qF 'debt_ledger.sh' \
  && printf '%s' "${body_snip}" | grep -qF -- '--has-open'; then
  if printf '%s\n' "${body_snip}" | awk '
    /^[[:space:]]*return[[:space:]]+0/ { if (!seen) bad=1 }
    /debt_ledger\.sh/ { seen=1 }
    END { exit bad+0 }
  '; then
    ok "gate.sh _check_open_debt 體呼叫 debt_ledger --has-open（非 early-return stub）"
  else
    bad "gate.sh _check_open_debt 在 debt_ledger 前 return 0（stub 假綠）"
  fi
else
  bad "gate.sh _check_open_debt 體未呼叫 debt_ledger --has-open（疑 stub）"
fi
# 既有護欄殘留（B5 不得順手拆除）
for needle in '_run_completeness_gate' 'reconcile_stamps_check' 'realpath'; do
  if grep -qF "${needle}" "${GATE_SH}"; then
    ok "gate.sh 保留護欄字樣 ${needle}"
  else
    bad "gate.sh 缺既有護欄字樣 ${needle}（B5 外漂移）"
  fi
done

# ── 層 C：範圍（授權區外漂移）────────────────────────────────
# 剝除 B5 授權區（_check_open_debt 註解塊+函式體；Task 3.1 呼叫點+其註解）後，
# residual 必須與 HEAD:scripts/gate.sh 位元組相等。足夠：任意非授權 hunk 改動會 diff 非空。
_strip_b5_debt_regions() {
  # $1=path → stdout residual
  awk '
    BEGIN { skip_fn=0; depth=0 }
    # 呼叫點（唯一合法形狀）
    /^[[:space:]]+_check_open_debt \|\| exit 1[[:space:]]*$/ { next }
    # 呼叫點上一行 Task 3.1 註解
    /^[[:space:]]*# Task 3\.1：債務閘/ { next }
    # 進入 _check_open_debt 函式：連同其前導 # 註解塊一併略過
    /^_check_open_debt\(\)/ {
      # 回吐已緩衝的非註解？此處改為：函式前連續 #/空行在緩衝中不輸出
      skip_fn=1
      depth=0
      # count braces on this line too
      n=split($0, a, "")
      for (i=1;i<=n;i++) {
        if (a[i]=="{") depth++
        else if (a[i]=="}") depth--
      }
      delete buf
      buf_n=0
      next
    }
    skip_fn {
      n=split($0, a, "")
      for (i=1;i<=n;i++) {
        if (a[i]=="{") depth++
        else if (a[i]=="}") depth--
      }
      if (depth<=0) { skip_fn=0 }
      next
    }
    # 緩衝連續註解／空行；遇到非註解時若下一邏輯是函式會被上面吃掉。
    # 簡化：直接輸出；函式前註解塊用第二次 pass 清。
    { print }
  ' "$1" | awk '
    # 第二 pass：刪除緊貼在已刪函式位置留下的孤立 _check_open_debt 註解塊
    # （以 "# _check_open_debt" 開頭的連續 # 行 + 其前後 --- 分隔行）
    BEGIN { pending=0 }
    {
      if ($0 ~ /^# -+$/ || $0 ~ /^# _check_open_debt/ || ($0 ~ /^# / && pending)) {
        # 可能是 B5 註解塊：暫存
        if ($0 ~ /^# _check_open_debt/ || $0 ~ /^# -+$/ || pending) {
          p[++pn]=$0
          if ($0 ~ /^# _check_open_debt/) pending=1
          if ($0 ~ /^# -+$/ && pending && pn>1) {
            # 可能是塊尾 ---：若塊內含 _check_open_debt 則丟棄整塊
            drop=0
            for (i=1;i<=pn;i++) if (p[i] ~ /_check_open_debt/) drop=1
            if (drop) { pn=0; pending=0; next }
            for (i=1;i<=pn;i++) print p[i]
            pn=0; pending=0; next
          }
          next
        }
      }
      if (pn>0) {
        for (i=1;i<=pn;i++) print p[i]
        pn=0; pending=0
      }
      print
    }
    END {
      if (pn>0) for (i=1;i<=pn;i++) print p[i]
    }
  '
}
_V7_TMP=$(mktemp -d)
if git show HEAD:scripts/gate.sh >"${_V7_TMP}/gate_head.sh" 2>/dev/null; then
  _strip_b5_debt_regions "${GATE_SH}" >"${_V7_TMP}/gate_residual.sh"
  # 正規化尾端換行後比對
  if diff -q "${_V7_TMP}/gate_head.sh" "${_V7_TMP}/gate_residual.sh" >/dev/null 2>&1; then
    ok "gate.sh 範圍層：B5 授權區外 residual == HEAD（無域外漂移）"
  else
    # 寬鬆一點：允許 residual 與 HEAD 只差空白行壓縮（函式移除後多餘空行）
    # 仍拒實質內容漂移：以去連續空行後的內容比對
    awk 'NF{print} !NF{if(!b)print; b=1; next} {b=0}' "${_V7_TMP}/gate_head.sh" >"${_V7_TMP}/h.norm"
    awk 'NF{print} !NF{if(!b)print; b=1; next} {b=0}' "${_V7_TMP}/gate_residual.sh" >"${_V7_TMP}/r.norm"
    if diff -q "${_V7_TMP}/h.norm" "${_V7_TMP}/r.norm" >/dev/null 2>&1; then
      ok "gate.sh 範圍層：B5 授權區外 residual ≈ HEAD（僅空白差）"
    else
      bad "gate.sh 範圍層：B5 授權區外有漂移（residual ≠ HEAD）"
      diff -u "${_V7_TMP}/h.norm" "${_V7_TMP}/r.norm" | head -40 || true
    fi
  fi
else
  bad "gate.sh 範圍層：無法讀 HEAD:scripts/gate.sh"
fi

# ── 層 B：行為 oracle（OPEN 債 → dispatch 必須 rc≠0）────────────────
# 隔離副本：禁直接變異 repo 內 scripts/。塞一筆真 OPEN 債後跑 gate dispatch。
_V7_ORACLE="${_V7_TMP}/oracle_repo"
mkdir -p "${_V7_ORACLE}/scripts" "${_V7_ORACLE}/.claude/gate" "${_V7_TMP}/gate_dir"
for _f in gate.sh debt_ledger.sh _debt_ledger_core.py audit_events.json \
          governance_families.sh governance_families.json; do
  if [ -f "scripts/${_f}" ]; then
    cp "scripts/${_f}" "${_V7_ORACLE}/scripts/${_f}"
    case "${_f}" in *.sh) chmod 755 "${_V7_ORACLE}/scripts/${_f}" ;; esac
  fi
done
# 真 OPEN 債（ts 在 registry cutoff 之後；sequence=1）
cat >"${_V7_ORACLE}/.claude/gate/audit.log" <<'OPENJSON'
{"actor":"verify-b2","brief_path":"handoffs/b.md","brief_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","brief_sha256_norm":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","event":"committee_round_open","event_id":"00000000-0000-4000-8000-000000000001","expected_outputs":{"codex":"handoffs/x.md"},"lock_mode":"discovery","origin_script":"committee_run.sh","participants":["codex"],"producer":"audit_append.sh","round_id":"verify-b2-open-oracle","schema_version":1,"sequence":1,"session_name":"verify-b2-oracle-s","task_id":"t-oracle","ts":"2026-08-01T12:00:00Z"}
OPENJSON
# 確認 ledger 視其為 OPEN（rc=1）
_oracle_ledger_rc=0
GOVERNANCE_TEST_HARNESS=1 \
DEBT_AUDIT_OVERRIDE="${_V7_ORACLE}/.claude/gate/audit.log" \
bash "${_V7_ORACLE}/scripts/debt_ledger.sh" --has-open >/dev/null 2>&1 \
  || _oracle_ledger_rc=$?
# 直接取 rc，禁 pipe
if [ "${_oracle_ledger_rc}" -ne 1 ]; then
  # 重跑取 stderr 供診斷
  _oracle_err=$(GOVERNANCE_TEST_HARNESS=1 \
    DEBT_AUDIT_OVERRIDE="${_V7_ORACLE}/.claude/gate/audit.log" \
    bash "${_V7_ORACLE}/scripts/debt_ledger.sh" --has-open 2>&1 >/dev/null) || true
  bad "行為 oracle 前置：debt_ledger --has-open 對 OPEN fixture 須 rc=1（got ${_oracle_ledger_rc}）err=${_oracle_err}"
else
  ok "行為 oracle 前置：OPEN fixture → debt_ledger rc=1"
  _oracle_gate_rc=0
  GOVERNANCE_TEST_HARNESS=1 \
  DEBT_AUDIT_OVERRIDE="${_V7_ORACLE}/.claude/gate/audit.log" \
  GATE_DIR_OVERRIDE="${_V7_TMP}/gate_dir" \
  bash "${_V7_ORACLE}/scripts/gate.sh" dispatch \
    --intent "verify-b2 open-oracle" \
    --risk low \
    --facts-asked "none-needed:verify-b2-oracle" \
    --review-role "single-executor:n/a" \
    --template "n/a:verify-b2-oracle" \
    --task-id "verify-b2-open-oracle" \
    --output "handoffs/verify-b2-open-oracle.md" \
    >/dev/null 2>&1 \
    || _oracle_gate_rc=$?
  if [ "${_oracle_gate_rc}" -ne 0 ]; then
    ok "行為 oracle：OPEN 債 → gate.sh dispatch rc=${_oracle_gate_rc}（拒發）"
  else
    bad "行為 oracle：OPEN 債時 gate.sh dispatch 放行 rc=0（fail-open；語意 mutation 可繞）"
  fi
  # token 不得因 OPEN 而新建（目錄可空）
  if [ -f "${_V7_TMP}/gate_dir/dispatch.token" ]; then
    bad "行為 oracle：OPEN 債時不應寫出 dispatch.token"
  else
    ok "行為 oracle：OPEN 債時無 dispatch.token"
  fi
fi

echo "=== 8. 防假綠：既有測試斷言未被刪 ==="
# grep -c 未命中時 stdout 已是 0 但 rc=1；`|| echo 0` 會再補一個 0 → "0\n0" 使 [ 炸。
# 用 `|| true` 吞 rc，勿再補印（CLAUDE.md 已載此坑，起草者又犯一次）。
n=$(git diff -- tests/ | grep -cE "^-.*assert" || true)
# ⚠️ 全形括號緊接 $n 會被 bash 併進變數名（本 session 第 2 次），一律用 ${n}
[ "${n}" -eq 0 ] && ok "既有測試無 assert 被刪（${n}）" || bad "有 ${n} 行 assert 被刪"

echo
[ "$fail" = 0 ] && echo "B2 INDEPENDENT VERIFY PASS" || echo "B2 INDEPENDENT VERIFY FAIL"
exit "$fail"
