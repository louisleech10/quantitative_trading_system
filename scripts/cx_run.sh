#!/usr/bin/env bash
# cx_run.sh — 委員派工安全模板(治本;取代手搓 inline prompt)。
# 根除三反覆錯:①反引號被 shell 當命令替換 ②`&` detach 掉 harness 通知 ③PATH 127。
#
# 用法(Claude 一律經此派委員,勿再手搓 codex/grok/cursor-agent 命令列):
#   bash scripts/cx_run.sh <family> <brief_path> <output_path> [effort]
#   family ∈ {codex, grok, composer}
#   brief_path : repo 內指示檔(prompt 全文放這;可自由用反引號,它被讀非 shell 插值)
#   output_path: 委員產出寫到這(handoffs/*.md)
#   effort     : codex only, 預設 xhigh
#
# 設計:命令列給委員的 prompt 是**固定極簡模板**「讀 <brief> 照做, 家族名=X, 產出寫 <out>」——
#   無反引號/無 $/無特殊字元 → 引號陷阱不可能發生。絕對路徑寫死。腳本本身不加 `&`;
#   Claude 用 Bash run_in_background:true 背景執行本腳本即可(勿在呼叫本腳本時加 `&`)。
set -u

fam="${1:-}"; brief="${2:-}"; out="${3:-}"; effort="${4:-xhigh}"
[ -n "${fam}" ] && [ -n "${brief}" ] && [ -n "${out}" ] || {
  echo "用法: bash scripts/cx_run.sh <codex|grok|composer> <brief_path> <output_path> [effort]"; exit 2; }
[ -f "${brief}" ] || { echo "ERROR: brief 檔不存在: ${brief}"; exit 2; }

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
_bk_all="$(grep -oE '^brief-kind:[[:space:]]*[a-z]+' "${brief}" 2>/dev/null | sed 's/.*:[[:space:]]*//' | sort -u)"
_bk_n="$(printf '%s\n' "${_bk_all}" | grep -c '[a-z]' || true)"
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
# ---------------------------------------------------------------------------
# 角色閘(2026-07-29 使用者定;防「Claude 憑腦中模型選家族」)
# 事故:2026-07-24 與 2026-07-29 連續兩次,把實作派給 reviewer、把 implementer 排進
#   code review(違反實作者不自審)。**兩次 ORCH §1 與記憶檔都寫對了**——散文規則擋不住,
#   故做成閘門。角色 SoT = scripts/governance_roles.json,**只有使用者可改**。
# 規則:impl → 家族須 == implementer。**implementer_backup 不自動放行**(僅供錯誤訊息提示);
#      切換實作端一律由使用者改 SoT(bash scripts/set_roles.sh <family>),不是 Claude 選備援。
#      (CODEX-R5-P1-02:本註解原寫「或 implementer_backup」,與下方程式碼及 SoT 相反)
#      review → 家族【不得】是 implementer(實作者不自審);closure/stamp/consult 不限(三家全員)
# fail-closed:SoT 缺檔/壞 JSON/缺鍵 → 拒派。
# ---------------------------------------------------------------------------
_ROLES="$(dirname "$0")/governance_roles.json"
# ⚠️ 家族不在 SoT 時【跳過角色閘】,交給檔尾 dispatch case 的 `*)` 分支去報錯。
#    理由(2026-07-29 實測):角色閘若搶先判非法家族,會把 `notafamily` 報成「角色不符」——
#    既誤導,又弄壞 test_impl_kind_not_required_to_have_finding_clauses。
#    另:**不得**在此另寫一份家族清單(憲法禁寫死;且會搶走 test_consumer_family_list_matches_sot
#    釘選的那一行,導致抽出空集合誤判漂移)。故用 SoT 函式庫判定,不列清單。
#    ⚠️ 連【註解】都不可出現該測試釘選的字樣——起草者已因此踩坑兩次(訊息一次、註解一次)。
. "$(dirname "$0")/governance_families.sh" 2>/dev/null || true
_KNOWN_FAM="$(families_get review_families '|' 2>/dev/null || echo '')"
_fam_known=0
[ -n "${_KNOWN_FAM}" ] && printf '%s' "${fam}" | grep -qE "^(${_KNOWN_FAM})$" && _fam_known=1

if [ "${_fam_known}" = "1" ] && { [ "${_bk}" = "impl" ] || [ "${_bk}" = "review" ]; }; then
  [ -f "${_ROLES}" ] || { echo "ERROR: 角色 SoT 缺檔: ${_ROLES}(fail-closed)"; exit 2; }
  _impl="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(d['implementer'])" 2>/dev/null)"
  _bkup="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(d.get('implementer_backup',''))" 2>/dev/null)"
  _revs="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(' '.join(d['reviewers']))" 2>/dev/null)"
  [ -n "${_impl}" ] && [ -n "${_revs}" ] || { echo "ERROR: 角色 SoT 解析失敗或缺鍵(fail-closed): ${_ROLES}"; exit 2; }

  # ⚠️ implementer_backup 【不】自動放行(僅供錯誤訊息提示)。
  #    使用者原話:「Grok 或 Codex 實作是我指定,你只能遵守,不能變更,我會根據額度調配」
  #    ⇒ 切換實作端 = 使用者改 SoT 的 implementer 欄,不是由 Claude 選備援。
  #    (本 oracle 首跑即抓到:若允許 backup,等同放行 2026-07-29 我犯的那個錯)
  if [ "${_bk}" = "impl" ] && [ "${fam}" != "${_impl}" ]; then
    echo "ERROR: 角色不符 — brief-kind=impl 的實作端須為 '${_impl}',但收到 '${fam}'。"
    echo "  角色 SoT: ${_ROLES}(**只有使用者可改**;Claude 不得自行變更,備援 '${_bkup}' 亦不自動放行)"
    echo "  若使用者本次指定改由 '${fam}' 實作,請【請使用者先更新該檔的 implementer 欄】再派工。"
    exit 2
  fi
  if [ "${_bk}" = "review" ] && [ "${fam}" = "${_impl}" ]; then
    echo "ERROR: 角色不符 — '${fam}' 是現行 implementer,不得擔任 code review(實作者不自審)。"
    echo "  現行 reviewers: ${_revs}　角色 SoT: ${_ROLES}"
    exit 2
  fi
fi

case "${out}" in handoffs/*) : ;; *) echo "ERROR: output 須在 handoffs/: ${out}"; exit 2 ;; esac

CODEX="/opt/homebrew/bin/codex"
GROK="/Users/louis/.grok/bin/grok"

# 固定極簡 prompt(無反引號/特殊字元)
prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。收尾清 /tmp workdir(保留 claude-501)。"

case "${fam}" in
  codex)
    [ -x "${CODEX}" ] || { echo "ERROR: codex 不存在: ${CODEX}"; exit 2; }
    "${CODEX}" exec -s workspace-write -m gpt-5.6-luna -c model_reasoning_effort="${effort}" "${prompt}" </dev/null
    ;;
  grok)
    [ -x "${GROK}" ] || { echo "ERROR: grok 不存在: ${GROK}"; exit 2; }
    "${GROK}" -m grok-4.5 --sandbox workspace --always-approve --output-format plain -p "${prompt}"
    ;;
  composer)
    cursor-agent -p --force --output-format text --model composer-2.5 "${prompt}"
    ;;
  *) echo "ERROR: family 須為 codex|grok|composer, 得到: ${fam}"; exit 2 ;;
esac
echo "[cx_run] ${fam} done rc=$? out=${out}"
