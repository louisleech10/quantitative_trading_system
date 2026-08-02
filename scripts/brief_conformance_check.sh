#!/usr/bin/env bash
# brief_conformance_check.sh — brief 合規閘的**唯一實作**（GOV-DOC-CHECK-AT-WRITE）。
#
# 出生理由（2026-08-02）：本檢查原本內嵌在 cx_run.sh:29-112，只在**派工當下**才跑。
#   實證代價：本 session 4 輪、B4 批次 5 輪（該批 38%）純粹燒在「brief 格式被閘擋 → 重寫 → 重派」。
#   病根＝**檢查點在消費端不在產出端**（`GOV-FORMAT-SSOT` 症狀 B）。
#   抽成獨立腳本後有兩個呼叫點：
#     ① scripts/cx_run.sh          — 派工前硬擋（fail-closed，維持原行為）
#     ② scripts/doc_format_precheck.sh — PostToolUse hook，**寫完當下**就回灌 Claude context
#   **一份實作、兩個呼叫點**。禁把邏輯複製到呼叫端——那是第二真相源，必然漂移。
#
# 用法：
#   bash scripts/brief_conformance_check.sh <brief_path> [--emit <kv_file>]
#     --emit <kv_file>：成功時把解析結果寫入該檔，第 1 行 = brief-kind，第 2 行 = stamp-target（非 stamp 為空行）
#                       （**不用 stdout 回傳**：既有錯誤訊息就走 stdout，呼叫端若重導 stdout 會把訊息吃掉）
#   rc: 0=合規；2=不合規/用法錯。
#
# ⚠️ 訊息輸出通道與抽出前**逐字相同**（brief-kind 段走 stdout、stamp-target 段走 stderr）。
#    既有測試 tests/governance/test_stamp_taskid_inject.py 對兩者分別斷言，改通道＝弄紅既有測試。
set -u

brief="${1:-}"
emit_file=""
shift 2>/dev/null || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --emit)
      [ "$#" -ge 2 ] || { echo "ERROR: --emit 需要參數" >&2; exit 2; }
      emit_file="$2"; shift 2 ;;
    *) echo "ERROR: 未知旗標: $1" >&2; exit 2 ;;
  esac
done

[ -n "${brief}" ] || {
  echo "用法: bash scripts/brief_conformance_check.sh <brief_path> [--emit <kv_file>]" >&2; exit 2; }
[ -f "${brief}" ] || { echo "ERROR: brief 檔不存在: ${brief}" >&2; exit 2; }

# ---------------------------------------------------------------------------
# brief 合規閘 P1-1(2026-07-24 使用者定;防「手搓 brief 漏掉範本必填條款」)
# 兩次實證事故(同一病根):手搓 brief 未引用範本 →
#   ①委員不知用 canonical 格式 → 產出 F-01/GROK-T1-01/無ID → completeness 抽不到
#     → Claude 手做 reconcile → 掉項(漏 grok T1-01)
#   ②未含 §0 挑戰前提 → Claude 的錯誤前提被當 finding 帶回(偽 finding C2)
# 治本(P1-1):不在此重列範本條款(會與範本漂移/漏),改**強制 brief 引用範本**(單一真相源)
#   + 補**任務專屬前提宣告**(fact-verified/assumed;範本給不了、每次必須 Claude 攤開)。
#   格式細節(canonical ID/四欄/§0-§3/Verdict)全由範本承載;閘只驗「有沒有用範本 + 有沒有攤前提」。
# 收集 findings 類 brief 缺 → 拒派(fail-closed)。impl/stamp 不產 findings → 不強制(不誤擋)。
# 對應範本:review/adversarial→SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT;語意審→COMMITTEE_SEMANTIC_REVIEW_TEMPLATE;
#   finding 格式→COMMITTEE_FINDING_TEMPLATE(三者互引,brief 引任一即涵蓋格式契約)。
# ---------------------------------------------------------------------------
# ⚠️ 必須【錨定行首】+【拒收多筆不一致宣告】(CODEX-R5-P0-01,2026-07-29 實跑 probe 證實):
#    未錨定時,brief 內任何一行註解如 `# brief-kind: review` 會被 head -1 取到而蓋掉真宣告
#    → 角色閘被繞過(非 implementer 可跑 impl)。此解析是角色閘的判定依據,故 fail-closed。
# 完整擷取宣告值（行首 brief-kind: → 行尾，trim 尾隨空白），再整值比對白名單。
# 禁止 grep -oE '...[a-z]+' 前綴擷取：stamp-evil 會被截成 stamp（與 committee_run 同步，CR2 群 E）。
_bk_all="$(grep -E '^brief-kind:' "${brief}" 2>/dev/null | sed 's/^brief-kind:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)"
_bk_n="$(printf '%s\n' "${_bk_all}" | grep -c '[^[:space:]]' || true)"
if [ "${_bk_n}" -gt 1 ]; then
  echo "ERROR: brief 有多個【不一致】的行首 'brief-kind:' 宣告: $(printf '%s' "${_bk_all}" | tr '\n' ' ')"
  echo "  (角色閘與 brief 合規閘都依此判定,歧義一律 fail-closed)"
  exit 2
fi
_bk="$(printf '%s\n' "${_bk_all}" | head -1)"
[ -n "${_bk}" ] || {
  echo "ERROR: brief 缺 'brief-kind:' 宣告。請於 brief 加一行,值 ∈ review|consult|closure|impl|stamp"
  echo "  (收集 findings 類=review/consult/closure,會另檢範本引用+前提宣告)"
  exit 2
}
case "${_bk}" in
  review|consult|closure)
    # ① 強制引用委員範本(單一真相源承載 canonical ID/四欄/§0-§3/Verdict)
    grep -qE 'SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT|COMMITTEE_SEMANTIC_REVIEW_TEMPLATE|COMMITTEE_FINDING_TEMPLATE' "${brief}" \
      || { echo "ERROR: brief-kind=${_bk} 須**引用**委員範本(brief 內寫明 templates/<範本>.md 全文照做);"
           echo "  範本承載 canonical finding 格式+§0挑戰前提+Verdict,不引用委員不會照格式 → completeness 抽不到。"
           echo "  review/adversarial→SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT;語意審→COMMITTEE_SEMANTIC_REVIEW_TEMPLATE。"; exit 2; }
    # ② 任務專屬前提宣告(範本給不了):至少各一條 fact-verified / assumed
    #    逼 Claude 在寫 brief 當下攤開假設 → 錯誤前提死在筆下,不燒一輪委員(事故 C2)。
    # grep -c 未命中時 stdout=0 但 rc=1;用 || true 吞 rc(勿再 echo 0,否則變多行 "0\n0" 致 [ 炸)。
    _n_fact="$(grep -cE 'fact-verified:' "${brief}" 2>/dev/null || true)"
    _n_assumed="$(grep -cE 'assumed:' "${brief}" 2>/dev/null || true)"
    if [ "${_n_fact}" -lt 1 ] || [ "${_n_assumed}" -lt 1 ]; then
      echo "ERROR: brief-kind=${_bk} 須含任務專屬**前提宣告**(範本 §0):逐條標 'fact-verified: <前提> → <查證>' 或 'assumed: <前提>'。"
      echo "  現況:fact-verified=${_n_fact} assumed=${_n_assumed};**至少各 1 條**。"
      echo "  '至少一條 assumed':宣稱零假設本身可疑(沒有 brief 真的零假設);逼你攤開可疑前提,否則錯前提被當 finding 帶回(C2)。"
      exit 2
    fi
    ;;
  impl|stamp) : ;;
  *) echo "ERROR: 未知 brief-kind: ${_bk}(允許 review|consult|closure|impl|stamp)"; exit 2 ;;
esac

# ---------------------------------------------------------------------------
# GOV-STAMP-TASKID-INJECT / D-001 §D3 defense-in-depth：brief-kind=stamp 驗證 stamp-target
# 與 committee_run.sh 同判準；涵蓋直呼 cx_run 路徑（不經 committee_run）。
# 失敗 rc=2；其餘 brief-kind 不解析、不強制。
# ---------------------------------------------------------------------------
stamp_target=""
if [ "${_bk}" = "stamp" ]; then
  _st_all="$(grep -E '^stamp-target:' "${brief}" 2>/dev/null | sed 's/^stamp-target:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)"
  _st_n="$(printf '%s\n' "${_st_all}" | grep -c '.' || true)"
  if [ "${_st_n}" -eq 0 ]; then
    echo "ERROR: brief-kind=stamp 缺 stamp-target: 欄" >&2
    exit 2
  fi
  if [ "${_st_n}" -gt 1 ]; then
    echo "ERROR: stamp-target 有多個【不一致】宣告: $(printf '%s' "${_st_all}" | tr '\n' ' ')" >&2
    exit 2
  fi
  stamp_target="$(printf '%s\n' "${_st_all}" | head -1)"
  case "${stamp_target}" in
    handoffs/*) : ;;
    *) echo "ERROR: stamp-target 須 handoffs/ 前綴: ${stamp_target}" >&2; exit 2 ;;
  esac
  case "${stamp_target}" in
    *"/../"*|"../"*|*".."*)
      echo "ERROR: stamp-target 不得含 ..: ${stamp_target}" >&2
      exit 2
      ;;
  esac
  [ -f "${stamp_target}" ] || { echo "ERROR: stamp-target 檔不存在: ${stamp_target}" >&2; exit 2; }
fi

if [ -n "${emit_file}" ]; then
  # 兩行固定格式；第 2 行恆存在（非 stamp 為空行），呼叫端可用 sed -n '2p' 穩定取值
  printf '%s\n%s\n' "${_bk}" "${stamp_target}" > "${emit_file}" || {
    echo "ERROR: 無法寫入 --emit 檔: ${emit_file}" >&2; exit 2; }
fi
exit 0
