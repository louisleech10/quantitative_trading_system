#!/usr/bin/env bash
# gov_check.sh — 本機一鍵治理檢查(單一真相源;pre-push hook 也呼叫本腳本)。
#
# 為何存在(2026-07-25):bash -n / governance pytest / mutation-probe 原本散著各跑,
#   而且 pre-push 自己複製了一份檢查邏輯 → 兩處會漂。收斂成一支,pre-push 只呼叫它。
#
# 用法:
#   bash scripts/gov_check.sh            # 全套(語法 + governance 測試 + 探針健檢)
#   bash scripts/gov_check.sh --fast     # 只跑語法(秒級;適合改完 shell 立即自檢)
#   bash scripts/gov_check.sh --no-probe # 語法+測試,略過探針(pre-push 用;探針慢變不必每 push 跑)
#
# 誠實邊界:本機 oracle 有共同盲區(如 BSD/GNU realpath 分歧,本機全綠 CI 才紅)。
#   **CI(Linux)仍是唯一跨環境 oracle,push 後仍須看 CI 結果**(ci_check_after_push hook 會自動回報)。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
fast=0; no_probe=0
case "${1:-}" in
  --fast)     fast=1 ;;
  --no-probe) no_probe=1 ;;   # pre-push 用:略過探針健檢(慢變項,不必每次 push 跑)
  "")         : ;;
  *) echo "用法: bash scripts/gov_check.sh [--fast|--no-probe]" >&2; exit 2 ;;
esac

rc_all=0

# ---------------------------------------------------------------------------
# 0) 委員暫停狀態提醒（**不擋 push**，只確保不被遺忘）
#
# 出生理由（2026-08-09）：grok 額度用罄（403 spending-limit），而
# reconcile_stamps_check 預設要求 review_families **全員** ⇒ 一家掛掉全線停擺。
# 直接改 review_families 會弄紅 9 個把名冊寫死的既有斷言（3 檔，其中
# test_rolegate_predispatch.py 屬 _B45_HARNESS 禁改）⇒ 不可行。
#
# 解法：`active_stampers`（本期實際要求蓋章者），`review_families` 維持正式名冊不動。
# 🔴 **暫停／調換委員 ＝ 改 governance_families.json 的 active_stampers 一行。**
# 差集即可稽核之「暫停中」紀錄，每次 push 印出 ⇒ 不靠記憶。
# 🔴 刻意**不擋 push**：會擋就等於沒解決「不卡住流程」這個原始需求。
# ---------------------------------------------------------------------------
_fam_json="scripts/governance_families.json"
# 🔴 `active_stampers` 缺席 ⇒ 整段跳過（**不得**因此讓 push 失敗）：
#    乾淨 clone／尚未導入該 key 的環境會把每一家都算成「多出家族」而擋死 push。
_has_active=0
if [ -f "${_fam_json}" ] && command -v jq >/dev/null 2>&1; then
  jq -e 'has("active_stampers")' "${_fam_json}" >/dev/null 2>&1 && _has_active=1
fi
if [ "${_has_active}" -eq 1 ]; then
  _suspended="$(jq -r '
      (.review_families // []) - (.active_stampers // []) | .[]
    ' "${_fam_json}" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')"
  _extra="$(jq -r '
      (.active_stampers // []) - (.review_families // []) | .[]
    ' "${_fam_json}" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')"
  if [ -n "${_suspended}" ]; then
    echo "[gov_check] ⚠ 委員暫停中（未清）: ${_suspended}"
    echo "            正式名冊 review_families 仍含該家；恢復後加回 active_stampers 即可。"
    echo "            出處: ${_fam_json} 之 _active_stampers_doc"
  fi
  if [ -n "${_extra}" ]; then
    echo "[gov_check] ✗ active_stampers 含不在 review_families 之家族: ${_extra}"
    echo "            新增正式委員須先進 review_families（fail-closed，防悄悄擴編）"
    rc_all=1
  fi
fi

# ---------------------------------------------------------------------------
# 0b) out-of-epic commit 清單（**不擋 push**，只確保可稽核）
#
# 該通道讓「epic 進行期間穿插修別的問題」不被 G-7 的 manifest 白名單擋死
# （見 scripts/govb1_final_gate.sh 之 _g7_path_only_ooe）。
# 代價是 G-7 對那些路徑放行 ⇒ **必須讓每一筆都看得見**，否則就成了靜默旁路。
# ---------------------------------------------------------------------------
if [ -f scripts/govb1_frozen_hashes.txt ]; then
  _ooe_base="$(grep -m1 '^base_commit:' scripts/govb1_frozen_hashes.txt | awk '{print $2}')"
  if [ -n "${_ooe_base}" ] && git rev-parse --verify -q "${_ooe_base}^{commit}" >/dev/null 2>&1; then
    _ooe_list="$(git log --format='%h %s' --extended-regexp \
      --grep='^Governance-Scope:[[:space:]]*out-of-epic' "${_ooe_base}..HEAD" 2>/dev/null)"
    if [ -n "${_ooe_list}" ]; then
      echo "[gov_check] ℹ out-of-epic commit（G-7 manifest 白名單已豁免，供稽核）:"
      printf '%s\n' "${_ooe_list}" | sed 's/^/            /'
    fi
  fi
fi

# --- 1) shell 語法 ---
echo "[gov_check] 1/3 shell 語法 (bash -n)…"
_bad=0
for f in scripts/*.sh scripts/git_hooks/*; do
  [ -f "${f}" ] || continue
  case "${f}" in *.py|*.json|*.txt|*.md) continue ;; esac
  head -1 "${f}" | grep -q 'bash\|sh' || continue
  bash -n "${f}" 2>/dev/null || { echo "  ✗ 語法錯: ${f}" >&2; _bad=1; }
done
if [ "${_bad}" -ne 0 ]; then echo "[gov_check] ✗ shell 語法未過" >&2; rc_all=1; else echo "[gov_check] ✓ shell 語法 OK"; fi

# --- 1b) 治理文件格式全庫掃描（GOV-DOC-CHECK-AT-WRITE / CODEX-R1-P1-03）---
# 為何除了 PostToolUse hook 還要這道：hook 的 matcher 只有 `Edit|Write`，
#   **經 Bash 寫出的檔、外部編輯器改的檔、hook 上線前就存在的檔一律漏掉**。
#   codex 指出「只對 Edit|Write 成立」＝強制性有缺口，此掃描補的就是那個缺口：
#   不論誰寫的、何時寫的，跑 gov_check（pre-push hook 也呼叫）就一定會被看到。
# ⚠️ **只掃「本次改動」的檔，不掃全庫**（實測依據，非保守）：
#   全庫掃描實跑 744 檔 → **24 個既有檔未過**，且絕大多數是誤報——
#   `docs/Archived/*`（範本上路前的舊檔）與 `docs/VERIFY_GATE_SPEC_PLAIN*.md`
#   （白話版，本來就不該有 SPEC 範本錨點）。硬擋這些＝pre-push 對所有人壞掉，
#   那是噪音不是強制，且會逼人加 `--no-verify`，反而把整條防線關掉。
#   diff 範圍剛好對應本機制的目的：「**不管誰寫的**，只要這次動到就要合規」。
# **不靜默吞**：legacy 積欠數字照印（下方 backlog 行），避免看起來像「全庫都乾淨」。
echo "[gov_check] 1b/3 治理文件格式 (doc_format_precheck，範圍=本次改動)…"
_docbad=0
_docn=0
_base="$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD 2>/dev/null || echo "")"
# ⚠️ 依賴缺檔一律 **fail-closed**（CODEX-R2-P1-01）：第一版寫成 `[ -f ] && ...`，
#   檔案不在就**靜默跳過整段且 rc=0** ⇒ 刪掉 doc_format_precheck.sh 就能讓格式檢查假綠。
#   pre-push 只呼叫 gov_check，所以那是真的 fail-open。缺工具＝檢查沒跑＝不得回報通過。
for _dep in scripts/doc_format_precheck.sh scripts/template_check.sh scripts/brief_conformance_check.sh; do
  [ -f "${_dep}" ] || {
    echo "[gov_check] ✗ 缺依賴 ${_dep} → fail-closed（不得靜默跳過格式檢查）" >&2
    rc_all=1
  }
done
if [ -z "${_base}" ]; then
  echo "[gov_check] ✗ 無法解析 git base（merge-base/rev-parse 皆失敗）→ fail-closed" >&2
  rc_all=1
fi
if [ -f scripts/doc_format_precheck.sh ] && [ -n "${_base}" ]; then
  while IFS= read -r f; do
    [ -n "${f}" ] || continue
    [ -f "${f}" ] || continue          # 已刪除的檔不檢查
    # 只收 docs/*.md：`handoffs/*` 在 .git/info/exclude 被整包排除（設計如此，
    #   委員產出與 brief 不進版控），故任何 git 導向的掃描都**看不到 brief**。
    #   brief 的強制點在 committee_run.sh／cx_run.sh 的 brief_conformance_check
    #   （本輪已修為**開債前**就跑完整檢查，見 CODEX-R1-P1-01），不靠這條掃描。
    case "${f}" in docs/*.md) : ;; *) continue ;; esac
    _docn=$((_docn + 1))
    bash scripts/doc_format_precheck.sh "${f}" 2>/dev/null || {
      echo "  ✗ 格式未過: ${f}（詳情跑 bash scripts/doc_format_precheck.sh ${f}）" >&2
      _docbad=$((_docbad + 1))
    }
  done <<EOF
$( { git diff --name-only "${_base}" -- docs 2>/dev/null
     git diff --name-only --cached -- docs 2>/dev/null
     git ls-files --others --exclude-standard -- docs 2>/dev/null; } | sort -u )
EOF
fi
if [ "${_docbad}" -ne 0 ]; then
  echo "[gov_check] ✗ 治理文件格式：${_docbad} 個未過（本次改動 ${_docn} 個）" >&2
  rc_all=1
else
  echo "[gov_check] ✓ 治理文件格式 OK（本次改動 ${_docn} 個）"
fi
# legacy backlog：全庫尚有多少既有檔不合規。**只報數不擋**，避免「看起來全庫乾淨」的假象。
# 這條刻意不進 rc_all——擋既有債會讓所有人 --no-verify，等於關掉整條防線。
if [ -f scripts/doc_format_precheck.sh ]; then
  _blog=0
  while IFS= read -r f; do
    [ -f "${f}" ] || continue
    bash scripts/doc_format_precheck.sh "${f}" >/dev/null 2>&1 || _blog=$((_blog + 1))
  done <<EOF
$(git ls-files 'docs/*.md' 2>/dev/null)
EOF
  [ "${_blog}" -gt 0 ] && echo "[gov_check] ℹ 既有未合規 backlog：${_blog} 個 docs/*.md（不擋 push；多為 Archived 與白話版誤報，待 T7 清）"
fi

if [ "${fast}" -eq 1 ]; then
  [ "${rc_all}" -eq 0 ] && echo "[gov_check] --fast 完成(未跑測試)" || echo "[gov_check] --fast 未過" >&2
  exit "${rc_all}"
fi

py="venv/bin/python"; [ -x "${py}" ] || py="$(command -v python3 || command -v python)"
[ -n "${py}" ] || { echo "[gov_check] ✗ 找不到 python → fail-closed" >&2; exit 1; }

# --- 2) governance 守衛測試 ---
if [ -d tests/governance ]; then
  echo "[gov_check] 2/3 governance 守衛測試 (pytest tests/governance)…"
  if "${py}" -m pytest tests/governance -q --tb=short; then
    echo "[gov_check] ✓ governance 測試通過"
  else
    echo "[gov_check] ✗ governance 測試未過" >&2; rc_all=1
  fi
else
  echo "[gov_check] 2/3 略過(無 tests/governance)"
fi

# --- 3) mutation 探針健檢(守衛測試是否為真 oracle) ---
if [ "${no_probe}" -eq 1 ]; then
  echo "[gov_check] 3/3 略過探針健檢(--no-probe;慢變項,改由手動/守衛測試改動時跑)"
elif [ -x scripts/mutation_probe_check.sh ]; then
  echo "[gov_check] 3/3 mutation 探針健檢…"
  # 只驗「**宣稱有探針**的檔」(含 test_mutation_)其探針是否真跑得過。
  # 舊檔無探針屬既有狀態(該不該補=待辦 P1-2「驗守衛的測試必附常駐 mutation」機械強制),
  # 納入只會恆亮雜訊警告 → 刻意排除,並在此註明邊界。
  # 已知既有債(2026-07-25 實測):test_verify_gate{,_b3,_b4}.py 的探針被判「空心/偽自證」
  #   (探針沒碰待測系統)。屬既有品質債 → **具名報告但不阻斷**(阻斷會逼人養成繞過習慣);
  #   修法歸待辦 P1-2/P1-3(驗守衛的測試須附**有效**常駐 mutation)。
  # 既有債清單(2026-07-25 實測:探針「空心/偽自證」——沒真的碰待測系統)。
  #   具名排除,否則批次永遠紅、每次 push 白跑一輪逐檔重測(實測拖到 3.5 分鐘)。
  #   **修掉後請從本清單移除**(歸待辦 P1-2/P1-3:守衛測試須附**有效**常駐 mutation)。
  LEGACY_PROBE_DEBT="tests/governance/test_verify_gate.py tests/governance/test_verify_gate_b3.py tests/governance/test_verify_gate_b4.py"
  probe_files=""
  for pf in $(grep -rl 'def test_mutation_' tests/governance/test_*.py 2>/dev/null); do
    case " ${LEGACY_PROBE_DEBT} " in *" ${pf} "*) continue ;; esac
    probe_files="${probe_files} ${pf}"
  done
  if [ -n "${probe_files}" ]; then
    # shellcheck disable=SC2086
    if bash scripts/mutation_probe_check.sh ${probe_files} >/dev/null 2>&1; then
      echo "[gov_check] ✓ 探針健檢通過($(printf '%s' "${probe_files}" | wc -w | tr -d ' ') 檔;另 $(printf '%s' "${LEGACY_PROBE_DEBT}" | wc -w | tr -d ' ') 檔既有債排除中→P1-2/P1-3)"
    else
      echo "[gov_check] ✗ 探針健檢未過(非既有債檔的探針失效,須修)" >&2; rc_all=1
    fi
  else
    echo "[gov_check] 3/3 無(非既有債的)探針檔,略過"
  fi
else
  echo "[gov_check] 3/3 略過(無 mutation_probe_check.sh)"
fi

# ── 4/4 白話說明過期偵測 ────────────────────────────────
# 為何在此(2026-08-05 使用者指出):白話說明的更新原本只靠主委記得,
#   且 plain_docs_sync_check.sh 本身也要「記得跑」才有用 ⇒ 仍是紀律不是機制。
#   接進 gov_check(pre-push 唯一委派點)後,忘記更新 = 推不上去。
if [ -f scripts/plain_docs_sync_check.sh ]; then
  echo "[gov_check] 4/4 白話說明過期偵測…"
  if bash scripts/plain_docs_sync_check.sh; then
    echo "[gov_check] ✓ 白話說明 同步 OK"
  else
    echo "[gov_check] ✗ 白話說明已過期(見上;更新後推進各檔 SYNCED-AT)" >&2
    rc_all=1
  fi
else
  echo "[gov_check] 4/4 略過(無 plain_docs_sync_check.sh)"
fi

if [ "${rc_all}" -eq 0 ]; then
  echo "[gov_check] ✅ 全數通過(注意:本機綠≠CI綠,push 後仍看 CI)"
else
  echo "[gov_check] ❌ 有項目未過 — 修好再繼續" >&2
fi
exit "${rc_all}"
