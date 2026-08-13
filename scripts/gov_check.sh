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
# 🔴 段序＝**便宜先、貴的後**(2026-08-12 使用者指示;實測依據見下)。
#   出生事故:原段序是 語法 → **pytest(約 700s)** → 探針 → 白話(1s) → fact-key(0s)。
#   那三條秒級閘任何一條紅,約 700 秒就白跑,而且得整輪重來。本 session 實測全套跑 9 次
#   ＝100.7 分鐘,其中約 44 分鐘屬這類「貴的先跑完才發現便宜的紅了」。
#   修法:秒級段全部前移,且**便宜段一紅就早退**(不進 pytest)。
#   ⚠️ 段號＝穩定識別碼,**執行序即宣告序**(本檔由上而下),兩者現已一致。
#   ⚠️ `--fast` 的契約**刻意不動**(仍＝語法+格式,見第 1b 段後之出口):
#      它跑在無 govb1 資料檔的隔離副本上(tests/governance/test_gov_check_dep_failclosed.py),
#      把 fact-key/白話/G-7 併進去會讓那些副本因缺資料檔而紅 ⇒ 假紅。
#
# 🔴 誠實邊界(2026-08-13 使用者定,CI 全數刪除後):本機 macOS 是**唯一** oracle。
#   跨平台盲區(如 BSD/GNU realpath、stat -f %m vs -c %Y)**不再有任何東西兜底**。
#   刪 CI 之理由:governance.yml 連續五次全紅(42 failed)、verify_claim 亦紅,無人查看
#   ⇒ 零保護純噪音,判準同 l65_benchmark.yml(2026-07-26 刪)。
#   ⇒ 42 條紅經查證**無一為真實跨平台 bug**,全為 CI 環境配置(效能斷言在共用 runner
#      不可靠、shallow clone 讀不到 git 歷史物件、G-7 需 commit 範圍)。
#   ⇒ 推論:本段全套 pytest 已是唯一防線,**不得再以「CI 會兜底」為由移出 pre-push**。
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
# 段號（唯一宣告處）— 票 B-25／Task 2.2 §2
#
# 出生理由：本檔原有 10 處段號，分母**全是寫死的字串**，結果自己就不一致
#   （同時存在 `1/3`、`4/4`，另有帶字母後綴的 `1b/3`）。寫死的數字必然漂。
# 規則：**分母＝本檔實際段數（現算）**；帶字母後綴者（如 `1b`）併入前一段、不另計；
#   🔴 **禁在任何字串中寫死分母**（tests/governance/test_govb1_factkey_hook.py 機械釘住）。
# 未登記的段號 ⇒ fail-closed：新增一段而忘了登記，會當場炸而不是靜默印出錯的分母。
# ---------------------------------------------------------------------------
_GC_SEG_IDS='1 1b 2 3 4 5 6'
_gc_total() {
  # shellcheck disable=SC2086
  printf '%s\n' ${_GC_SEG_IDS} \
    | sed 's/[^0-9].*$//' | grep -v '^$' | sort -u | wc -l | tr -d ' '
}
_GC_TOTAL="$(_gc_total)"
_gc_seg() {   # $1=段號（須已登記） $2=標題
  case " ${_GC_SEG_IDS} " in
    *" $1 "*) : ;;
    *) echo "[gov_check] ✗ 未登記的段號 '$1'（須先加入 _GC_SEG_IDS）→ fail-closed" >&2
       exit 2 ;;
  esac
  echo "[gov_check] $1/${_GC_TOTAL} $2"
}

# ---------------------------------------------------------------------------
# 失敗摘要（2026-08-12）— 失敗原因一律累積,收尾一次印在**最末**
#
# 出生事故:本檔輸出動輒 1600+ 行(pytest 佔絕大多數)。失敗原因散在中間,
#   `tail -3` 只看得到收尾那句「有項目未過」,看不到是哪一段為什麼紅。
#   本 session 兩次因此直接重跑整套(白花 22 分鐘)——那不是紀律問題,是輸出設計問題。
# 規則:🔴 任何段落判紅一律走 `_gc_fail <段號> "<一行原因>"`,**禁直接寫 `rc_all=1`**
#   (直接寫＝該原因不會進摘要,又退回「tail 看不到」的狀態)。
# 摘要行帶固定前綴 `GOV-CHECK-FAILED:` ⇒ 可 grep,不必人眼掃。
# ---------------------------------------------------------------------------
_gc_fails=''
_gc_fail() {   # $1=段號 $2=一行原因（會進最末摘要）
  rc_all=1
  _gc_fails="${_gc_fails}GOV-CHECK-FAILED: [段 $1] $2
"
}
_gc_summary() {   # $1=收尾語；印摘要並回傳 rc_all
  if [ "${rc_all}" -eq 0 ]; then
    echo "[gov_check] ✅ ${1}(注意:本機綠≠CI綠,push 後仍看 CI)"
  else
    {
      echo ""
      echo "════════ 失敗摘要（以下即全部原因；勿只看 tail 就重跑整套）════════"
      printf '%s' "${_gc_fails}"
      echo "══════════════════════════════════════════════════════"
      echo "[gov_check] ❌ ${1}"
    } >&2
  fi
  return "${rc_all}"
}

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
    # 段 0 未登記於 _GC_SEG_IDS（它不印段號、也不算一段）；此處只借 _gc_fail 進摘要。
    _gc_fail 0 "active_stampers 含不在 review_families 之家族: ${_extra}（新增正式委員須先進 review_families）"
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
    # 🔴 與 govb1_final_gate.sh `_g7_ooe_commits` **同法**（原生 trailer 解析 + 同一
    #   grandfather 封閉集）。此處刻意不沿用舊的 `--grep`：稽核清單若比閘的實際豁免集**寬**，
    #   使用者會看到「已豁免」但閘其實沒放行的 commit，反而誤導。
    #   兩處漂移由 tests/governance/test_govb1_contract_matrix.py 之
    #   test_ooe_audit_list_matches_gate 釘住。
    # 🔴 欄位順序＝sha, trailer, subject〔CODEX-R2-P2-03〕：
    #   前版把自由文字的 `%s` 放中間再取 `$3`，**subject 含 tab 的 commit 會整筆漏列**
    #   （codex 實測：gate 選入、稽核清單沒有）⇒ 已豁免路徑變成看不見的旁路。
    #   把 subject 移到最後，並以「前兩個 tab」定界，subject 內含 tab 也不影響判定。
    # 🔴 重複 key 以 0x1F 分隔偵測並拒（與閘同法，見 _G7_OOE_MULTI_SEP）。
    _ooe_raw="$(git log --format='%h%x09%(trailers:key=Governance-Scope,valueonly,separator=%x1F)%x09%s' \
      "${_ooe_base}..HEAD" 2>/dev/null)"
    _ooe_list="$(printf '%s\n' "${_ooe_raw}" \
      | awk '
          { i = index($0, "\t"); if (i == 0) next
            sha = substr($0, 1, i - 1); rest = substr($0, i + 1)
            j = index(rest, "\t"); if (j == 0) next
            val = substr(rest, 1, j - 1); subj = substr(rest, j + 1)
            if (val ~ /^out-of-epic([[:space:]]|$)/ && index(val, "\037") == 0)
              print sha " " subj }')"
    # grandfather（慣例訂立前之兩筆；須仍落在 base..HEAD 內才列）
    _ooe_gf=""
    for _s in d0dc68245e967380965e6b2ee18349e74a34ca5d \
              28b586a8224f1338b6a445f66e6e782e06c3d013; do
      git merge-base --is-ancestor "${_s}" HEAD 2>/dev/null || continue
      git merge-base --is-ancestor "${_s}" "${_ooe_base}" 2>/dev/null && continue
      _ooe_gf="${_ooe_gf}$(git log -1 --format='%h %s (grandfather)' "${_s}" 2>/dev/null)
"
    done
    _ooe_all="$(printf '%s\n%s\n' "${_ooe_list}" "${_ooe_gf}" | grep -v '^[[:space:]]*$')"
    if [ -n "${_ooe_all}" ]; then
      echo "[gov_check] ℹ out-of-epic commit（G-7 manifest 白名單已豁免，供稽核）:"
      printf '%s\n' "${_ooe_all}" | sed 's/^/            /'
    fi
  fi
fi

# --- 1) shell 語法 ---
_gc_seg 1 "shell 語法 (bash -n)…"
_bad=0
for f in scripts/*.sh scripts/git_hooks/*; do
  [ -f "${f}" ] || continue
  case "${f}" in *.py|*.json|*.txt|*.md) continue ;; esac
  head -1 "${f}" | grep -q 'bash\|sh' || continue
  bash -n "${f}" 2>/dev/null || { echo "  ✗ 語法錯: ${f}" >&2; _bad=1; }
done
if [ "${_bad}" -ne 0 ]; then
  echo "[gov_check] ✗ shell 語法未過" >&2
  _gc_fail 1 "shell 語法錯（具名檔案見上方 ✗ 行；跑 bash -n <檔> 重現）"
else echo "[gov_check] ✓ shell 語法 OK"; fi

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
_gc_seg 1b "治理文件格式 (doc_format_precheck，範圍=本次改動)…"
_docbad=0
_docn=0
_base="$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD 2>/dev/null || echo "")"
# ⚠️ 依賴缺檔一律 **fail-closed**（CODEX-R2-P1-01）：第一版寫成 `[ -f ] && ...`，
#   檔案不在就**靜默跳過整段且 rc=0** ⇒ 刪掉 doc_format_precheck.sh 就能讓格式檢查假綠。
#   pre-push 只呼叫 gov_check，所以那是真的 fail-open。缺工具＝檢查沒跑＝不得回報通過。
for _dep in scripts/doc_format_precheck.sh scripts/template_check.sh scripts/brief_conformance_check.sh; do
  [ -f "${_dep}" ] || {
    echo "[gov_check] ✗ 缺依賴 ${_dep} → fail-closed（不得靜默跳過格式檢查）" >&2
    _gc_fail 1b "缺依賴 ${_dep} → fail-closed（格式防線不得因缺檔靜默關掉）"
  }
done
if [ -z "${_base}" ]; then
  echo "[gov_check] ✗ 無法解析 git base（merge-base/rev-parse 皆失敗）→ fail-closed" >&2
  _gc_fail 1b "無法解析 git base（merge-base/rev-parse 皆失敗）→ 掃描範圍不明,fail-closed"
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
  _gc_fail 1b "治理文件格式 ${_docbad} 個未過（檔名見上方 ✗ 行；跑 bash scripts/doc_format_precheck.sh <檔> 看詳情）"
else
  echo "[gov_check] ✓ 治理文件格式 OK（本次改動 ${_docn} 個）"
fi
# 🔴 legacy backlog 計數**已移到本檔最末**（2026-08-12）。
#   出生事故：它掃全庫 216 個 docs/*.md，實測讓 `--fast` 從約 5 秒變成 **80 秒**，
#   而它**只印一個數字、永不進 rc_all、從不擋任何東西**。
#   擺在便宜段中間 ⇒ 每次都得先付這 75 秒，才知道 0 秒的 fact-key 閘紅了沒。
#   規則：不擋門的東西不得排在擋門的東西前面。搬移處見檔案最末「legacy backlog」節。

if [ "${fast}" -eq 1 ]; then
  _gc_summary "--fast 完成(契約＝語法+格式;刻意不含第 2–4 段,理由見檔頭)"
  exit "${rc_all}"
fi

# ── 2) 白話說明過期偵測（原第 4 段，2026-08-12 前移）────────────────
# 為何在此(2026-08-05 使用者指出):白話說明的更新原本只靠主委記得,
#   且 plain_docs_sync_check.sh 本身也要「記得跑」才有用 ⇒ 仍是紀律不是機制。
#   接進 gov_check(pre-push 唯一委派點)後,忘記更新 = 推不上去。
# 為何前移到 pytest 之前(2026-08-12):本段實測 1 秒,原本排在約 700 秒的 pytest 之後,
#   忘記更新白話 ⇒ 白等約 700 秒才知道,且修完要整輪重跑。
if [ -f scripts/plain_docs_sync_check.sh ]; then
  _gc_seg 2 "白話說明過期偵測…"
  if bash scripts/plain_docs_sync_check.sh; then
    echo "[gov_check] ✓ 白話說明 同步 OK"
  else
    echo "[gov_check] ✗ 白話說明已過期(見上;更新後推進各檔 SYNCED-AT)" >&2
    _gc_fail 2 "白話說明已過期（更新內容後推進各檔 SYNCED-AT；跑 bash scripts/plain_docs_sync_check.sh 看是哪幾份）"
  fi
else
  _gc_seg 2 "略過(無 plain_docs_sync_check.sh)"
fi

# ── 3) 事實單一來源 fact-key（票 B-25／Task 2.2；原第 5 段，2026-08-12 前移）──
# 為何掛在 pre-push 這一點，而**不是**派工當下（與 票 B-29 不矛盾的理由）：
#   · `B-29` 管的是**派工當下的宣告**（brief 說清楚什麼會變）——那是單一動作的輸入品質。
#   · `B-25` 管的是**文件副本一致性**——它是 repo 全域狀態，
#     只有 push 前才有完整快照（改了 A 檔忘了跑生成器，唯有比對整棵樹才看得出來）。
#   兩者掛點不同是因為**檢查對象的粒度不同**，不是重複強制。
# 為何前移到 pytest 之前（2026-08-12）：本段實測 0 秒。本 session 因它排在約 700 秒之後，
#   踩了四次「手寫狀態字面值 → 約 700 秒後才被擋 → 整輪重跑」。
# 🔴 生成器不存在／不可執行 ⇒ fail-closed（不得靜默略過；刪掉腳本就能假綠＝沒有檢查）。
# 🔴 不得宣稱「single-source 已完成」。具名殘留：
#   ① 生成器不知道的新文件裡憑空手寫第三份副本 ⇒ 擋不到
#   ② `git push --no-verify` 可繞（與本檔其餘機制同一邊界）
# 誠實邊界：`--fast` 不跑本段（--fast 之契約＝語法+格式）；push 路徑走 `--no-probe`，會跑。
_gov_check_factkey() {   # -> rc
  _gc_seg 3 "事實單一來源 (fact-key)…"
  # 🔴 TODO 偽碼寫的是 `${ROOT}/scripts/...`，但本檔無 ROOT 變數且 set -u
  #   ⇒ 逐字照抄會在執行期炸。本檔開頭已 cd 到 repo 根，故用相對路徑。
  [ -x scripts/gen_fact_key_blocks.sh ] || {
    echo "[gov_check] ✗ gen_fact_key_blocks.sh 缺失或不可執行 → fail-closed" >&2
    return 1
  }
  # 🔴 `env -u GOVB1_FACTKEY_ROOT`〔CODEX-R1-P1-01〕：
  #   該變數是**測試用**的 fixture 指向鉤子。強制層若照收，任何人（或殘留在 shell
  #   環境裡的一行 export）就能把 push 前的檢查導去乾淨 fixture ⇒ 真實宿主檔漂移照樣過。
  #   強制點必須自己決定檢查對象，不接受呼叫端指定 ⇒ 此處一律清掉。
  env -u GOVB1_FACTKEY_ROOT bash scripts/gen_fact_key_blocks.sh --check || return 1
}
if _gov_check_factkey; then
  echo "[gov_check] ✓ 事實單一來源 OK"
else
  echo "[gov_check] ✗ 事實單一來源漂移(見上;改 scripts/fact_keys.json 後跑 --write)" >&2
  _gc_fail 3 "fact-key 漂移（改 scripts/fact_keys.json 後跑 bash scripts/gen_fact_key_blocks.sh --write；禁在文件內手寫狀態字面值）"
fi

# ── 4) scope 淨差預檢（G-7）────────────────────────────────
# 為何新增（2026-08-12 使用者指示）：G-7 用 **endpoint 淨差**（只比 <a>..<b> 兩端點），
#   所以 **commit 前恆綠、一 commit 才現形**。本 session 頭尾各踩一次。
#   在此之前 G-7 **完全不在 push 鏈上**，只靠主委「記得手動跑 8 秒快閘」——
#   而紀律不是機制（使用者原話：「寫進紀律有什麼用，下一次就不做了」）⇒ 接進強制點。
# 🔴 **必須帶 `--only g7`**：govb1_final_gate.sh 預設跑整張 `_CHECKS` 表，
#   而該表第一列即 `_g0_tests`＝**全套 pytest** ⇒ 漏掉旗標會在此多跑一次約 700 秒
#   （本 session 實際踩過；這是本段唯一的高代價陷阱）。實測 `--only g7` 為 8 秒。
# 🔴 缺檔處置＝**fail-closed**〔CODEX-R1-P1-01〕：
#   第一版寫成「腳本不在就印略過」，理由是「本段是新增覆蓋，略過不比現況差」。
#   codex 指出那是 fail-open 的標準形態——刪掉／漏裝／錯誤 checkout 該腳本，
#   新增的 G-7 push-chain 覆蓋就**靜默消失**，而 push 照樣綠。此判斷成立，已改。
# 適用性判定用**資料檔**而非腳本：`scripts/govb1_scope.manifest` 是 G-7 的輸入，
#   它在＝本 repo 屬 govb1 epic ⇒ 閘必須能跑，腳本缺席即為壞掉，判紅。
#   兩者皆不在＝非 govb1 repo（乾淨 clone／tmp 測試副本）⇒ 本段不適用，略過。
#   ⇒ 「刪腳本讓檢查消失」這條路被堵死；要繞得連 manifest 一起刪，而那會讓
#      `_g7_policy` 自己 fail-closed（見 govb1_final_gate.sh 之 `_nonempty G-7`）。
# 反面由 test_gov_check_cheap_first.py::test_mutation_removing_g7_script_turns_red 釘住。
if [ -f scripts/govb1_scope.manifest ]; then
  _gc_seg 4 "scope 淨差預檢 (G-7；約 8 秒)…"
  if [ ! -f scripts/govb1_final_gate.sh ]; then
    echo "[gov_check] ✗ 有 govb1_scope.manifest 卻缺 govb1_final_gate.sh → fail-closed" >&2
    _gc_fail 4 "缺 scripts/govb1_final_gate.sh 但 scope manifest 在 ⇒ G-7 覆蓋消失（不得靜默略過）"
  elif bash scripts/govb1_final_gate.sh --only g7 >/dev/null; then
    echo "[gov_check] ✓ G-7 scope 淨差 OK"
  else
    echo "[gov_check] ✗ G-7 scope 淨差未過(見上)" >&2
    _gc_fail 4 "G-7 scope 淨差未過（跑 bash scripts/govb1_final_gate.sh --only g7 看詳情；out-of-epic 之 commit 須帶 Governance-Scope trailer 且置於訊息最末段）"
  fi
else
  _gc_seg 4 "略過(無 govb1_scope.manifest ⇒ 非 govb1 epic repo，G-7 不適用)"
fi

# ── 便宜段早退閘（2026-08-12）────────────────────────────────
# 第 1–4 段實測合計約 10 秒；第 5 段 pytest 實測 **710.68s／1530 passed**（2026-08-12）。
# 便宜段已經紅了還去跑那 700 秒，**必定白跑**（修完得整輪重來）。
# 🔴 誠實邊界：本修法**不會讓全綠的 push 變快**（實測全綠 13 分 20 秒，比改動前略久，
#   因為多了 G-7 預檢 8 秒）。修掉的是「付滿 11 分鐘才被告知一個 0 秒的閘紅了」那個迴圈。
# 🔴 誠實邊界：早退＝這一輪只會看到便宜段的失敗，pytest 的問題要下一輪才知道。
#   這是刻意取捨——實測本 session 便宜段紅的次數遠多於 pytest 紅的次數。
if [ "${rc_all}" -ne 0 ]; then
  _gc_summary "便宜段(第 1–4 段,合計約 10 秒)已失敗 → 早退,不跑 pytest(省約 700 秒)。修好後重跑。"
  exit "${rc_all}"
fi

py="venv/bin/python"; [ -x "${py}" ] || py="$(command -v python3 || command -v python)"
# 🔴〔CODEX-R1-P2-01〕原為裸 `exit 1`，失敗原因不進摘要 ⇒ 與「任何判紅走 _gc_fail」矛盾。
[ -n "${py}" ] || {
  echo "[gov_check] ✗ 找不到 python → fail-closed" >&2
  _gc_fail 5 "找不到 python（venv/bin/python 與 PATH 皆無）⇒ 守衛測試無法執行，fail-closed"
  _gc_summary "找不到 python → 無法執行守衛測試"
  exit "${rc_all}"
}

# --- 5) governance 守衛測試 ---
if [ -d tests/governance ]; then
  _gc_seg 5 "governance 守衛測試 (pytest tests/governance)…"
  if "${py}" -m pytest tests/governance -q --tb=short; then
    echo "[gov_check] ✓ governance 測試通過"
  else
    echo "[gov_check] ✗ governance 測試未過" >&2
    _gc_fail 5 "governance 守衛測試未過（失敗案例見上方 pytest 輸出；單獨重現跑 venv/bin/python -m pytest tests/governance -q）"
  fi
else
  _gc_seg 5 "略過(無 tests/governance)"
fi

# --- 6) mutation 探針健檢(守衛測試是否為真 oracle) ---
if [ "${no_probe}" -eq 1 ]; then
  _gc_seg 6 "略過探針健檢(--no-probe;慢變項,改由手動/守衛測試改動時跑)"
elif [ -x scripts/mutation_probe_check.sh ]; then
  _gc_seg 6 "mutation 探針健檢…"
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
      echo "[gov_check] ✗ 探針健檢未過(非既有債檔的探針失效,須修)" >&2
      _gc_fail 6 "mutation 探針健檢未過（非既有債檔的探針失效；跑 bash scripts/mutation_probe_check.sh <檔> 看是哪支）"
    fi
  else
    _gc_seg 6 "無(非既有債的)探針檔,略過"
  fi
else
  _gc_seg 6 "略過(無 mutation_probe_check.sh)"
fi

# ── legacy backlog（純資訊，不擋門；2026-08-12 由段 1b 尾巴搬來本處）──────
# 全庫尚有多少既有檔不合規。**只報數不擋**，避免「看起來全庫乾淨」的假象。
# 這條刻意不進 rc_all——擋既有債會讓所有人 --no-verify，等於關掉整條防線。
# 🔴 為何搬到最末：實測掃 216 檔約 75 秒，而它不擋門。放前面等於每次都先付 75 秒
#   才知道秒級閘紅了沒。放最末 ⇒ 失敗時根本不會跑到（下面 rc_all 判斷）。
# 🔴 具名殘留：**綠燈路徑仍要付這 75 秒**（約佔一次成功 push 的 11%）。
#   要根治得做「內容雜湊快取」或改成 opt-in，本輪刻意不做——不擋門的成本優先序低於
#   擋門的成本，且再加機制正是 scope accretion。要清時另記。
if [ "${rc_all}" -eq 0 ] && [ -f scripts/doc_format_precheck.sh ]; then
  _blog=0
  while IFS= read -r f; do
    [ -f "${f}" ] || continue
    bash scripts/doc_format_precheck.sh "${f}" >/dev/null 2>&1 || _blog=$((_blog + 1))
  done <<EOF
$(git ls-files 'docs/*.md' 2>/dev/null)
EOF
  [ "${_blog}" -gt 0 ] && echo "[gov_check] ℹ 既有未合規 backlog：${_blog} 個 docs/*.md（不擋 push；多為 Archived 與白話版誤報，待 T7 清）"
fi

_gc_summary "全數通過"
exit "${rc_all}"
