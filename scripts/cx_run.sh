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
