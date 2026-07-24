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
# brief 合規閘(2026-07-24 使用者定;防「手搓 brief 漏掉範本必填條款」)
# 兩次實證事故(同一病):
#   ①漏 canonical finding ID 格式 → 委員產出機器讀不到(codex F-01/grok T1-01/composer 無ID)
#     → completeness 抽不到 → Claude 只能手做 reconcile → 掉項(漏記 grok 立場)
#   ②漏 §0 反幻覺/挑戰前提 → Claude 的錯誤前提被當 finding 帶回
#     (實例:brief 自己把「送草稿去審」寫成合法情境,codex 順著產出偽 finding C2)
#   ——範本 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 兩條都寫得好好的,是手搓時漏掉。
# 故:凡「收集委員 findings」類派工,brief 缺必填條款 → **拒派**(fail-closed,不讓 Claude 繞)。
# ---------------------------------------------------------------------------
_bk="$(grep -oE 'brief-kind:[[:space:]]*[a-z]+' "${brief}" 2>/dev/null | head -1 | sed 's/.*:[[:space:]]*//')"
[ -n "${_bk}" ] || {
  echo "ERROR: brief 缺 'brief-kind:' 宣告。請於 brief 加一行,值 ∈ review|consult|closure|impl|stamp"
  echo "  (收集 findings 類=review/consult/closure,會另檢範本必填條款)"
  exit 2
}
case "${_bk}" in
  review|consult|closure)
    grep -qE '\-R<?n?[0-9]*>?-P\[?0?-?3?\]?-|FAMILY>-R|COMMITTEE_FINDING_TEMPLATE|SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT' "${brief}" \
      || { echo "ERROR: brief-kind=${_bk} 須指明 canonical finding ID 格式(## <FAMILY>-R<n>-P[0-3]-<NN>);"
           echo "  否則委員產出機器讀不到,completeness 無法驗 0 掉項。見 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md"; exit 2; }
    grep -qE '挑戰前提|反幻覺|質疑.*前提' "${brief}" \
      || { echo "ERROR: brief-kind=${_bk} 須含「挑戰前提/反幻覺」條款(範本 §0);"
           echo "  否則 Claude 的錯誤前提會被當 finding 帶回(相關性錯誤,ORCH L94 傷疤)。"; exit 2; }
    ;;
  impl|stamp) : ;;
  *) echo "ERROR: 未知 brief-kind: ${_bk}(允許 review|consult|closure|impl|stamp)"; exit 2 ;;
esac
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
