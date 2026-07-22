#!/usr/bin/env bash
# completeness_check.sh — 綜合(reconcile/UNION)完整性機械檢查
#
# 病灶(2026-07-22 IC reconcile 手抄事故):Claude 手抄合併多方委員產物 → 靜默掉項。
# 方法:委員產物用 canonical finding ID(見下);本腳本機械抽每個來源檔的 ID,
#   檢查是否**全部**出現在綜合檔。缺任一 → FAIL。把「靜默掉項」變「機器擋下」。
#
# 用法:
#   bash scripts/completeness_check.sh <綜合檔> <來源檔1> [來源檔2 ...]
#   STRICT=1          → 來源無 ID 時 FAIL(預設 1; STRICT=0 才 WARN+續跑)。
#   ALLOW_BARE_IDS=1  → 允許裸 F/L/C/N/NE 短 ID(預設關;易與章節/行號撞)。
#   ALLOW_ID_PATTERN_OVERRIDE=1 + ID_PATTERN=... → 除錯覆寫(gate/CI 禁止)。
#
# 誠實邊界(三家對抗審查 + grok 紅隊 2026-07-22):
#   ✅ 擋:來源【有 ## heading canonical ID 的 finding】未進綜合(dropped-ID class)。
#   ❌ 不擋:語意降級(ID 在但描述/severity 被改弱)——需委員全項忠實度覆議。
#   ❌ 不擋:錯併(ID 進了但併錯底層問題)——需委員複驗。
#   ❌ 不擋:來源本身沒 heading ID 的 prose/list finding——須來源端遵守慣例。
#   ❌ 不擋:呼叫端縮減來源清單(argv 信任邊界)——須 gate 從 dispatch manifest 注入來源。
#   ❌ 不擋:跨來源共用同一 bare/短 ID 致「ID 在但不同義 finding 被吞」。
#   ∴ 本腳本是「聚合完整性(B)」一層,非「語意忠實(C)」;分層防禦,非封印。
#
# canonical finding ID 慣例(委員派工 prompt 應要求):
#   以 markdown heading 呈現: `## <ID>` 或 `### <ID>`(ID 為標題首 token;至少 ##)。
#   推薦獨立命名空間: <FAM>-<n> 或 <FAM>-<ROUND>-<n>(如 CODEX-01 / GROK-R1-01)。
#   亦支援: FACTS-<n> / MISSING-NODES-<n> / ESCAPE-... / HARDEN-... / EP-<X>。
set -u

SYNTH="${1:-}"
shift || true
[ -n "${SYNTH}" ] || { echo "用法: bash scripts/completeness_check.sh <綜合檔> <來源檔...>"; exit 2; }
[ -f "${SYNTH}" ] || { echo "COMPLETENESS FAIL: 綜合檔不存在: ${SYNTH}"; exit 2; }
[ "$#" -ge 1 ] || { echo "用法: 至少一個來源檔"; exit 2; }

# 預設 STRICT=1:無 ID 來源不得假 PASS(紅隊 A5/A12 vacuous PASS)。
STRICT="${STRICT:-1}"
ALLOW_BARE_IDS="${ALLOW_BARE_IDS:-0}"

# 至少 ## (h2+)。單一 # 會把 markdown 註解「# CODEX-02 deferred」誤當 heading(紅隊 A2)。
HEADING_LINE_RE='^[[:space:]]*#{2,6}[[:space:]][[:space:]]*'

# 預設只收命名空間 ID;裸 F1/L47 需 ALLOW_BARE_IDS=1(紅隊 A4/A8)。
# 注意:ERE 不用 (?:) — macOS BSD sed/grep 不穩。
NS_ID_RE='^(FACTS-[0-9]+|MISSING-NODES-[0-9]+|ESCAPE-[A-Z0-9-]+|HARDEN-[A-Za-z0-9_-]+|EP-[A-Z]+|[A-Z]{2,10}(-[A-Z0-9]+)*-[0-9]+)$'
BARE_ID_RE='^(FACTS-[0-9]+|MISSING-NODES-[0-9]+|ESCAPE-[A-Z0-9-]+|HARDEN-[A-Za-z0-9_-]+|EP-[A-Z]+|[A-Z]{2,10}(-[A-Z0-9]+)*-[0-9]+|F[0-9]+|NE[0-9]+|L[0-9]+|[CN][0-9]+)$'
if [ "${ALLOW_BARE_IDS}" = "1" ]; then
  CANONICAL_ID_RE="${BARE_ID_RE}"
else
  CANONICAL_ID_RE="${NS_ID_RE}"
fi

if [ -n "${ID_PATTERN:-}" ]; then
  if [ "${ALLOW_ID_PATTERN_OVERRIDE:-}" != "1" ]; then
    echo "COMPLETENESS FAIL: ID_PATTERN 覆寫已禁用(紅隊 F-c/A6)。除錯請設 ALLOW_ID_PATTERN_OVERRIDE=1, gate/CI 禁止。"
    exit 1
  fi
  # 覆寫時改走全文 grep -oE(除錯用);正式路徑仍是 heading extract。
  USE_PATTERN_OVERRIDE=1
else
  USE_PATTERN_OVERRIDE=0
fi

extract_heading_ids() {
  local file="$1"
  if [ "${USE_PATTERN_OVERRIDE}" = "1" ]; then
    grep -oE "${ID_PATTERN}" "${file}" 2>/dev/null | sort -u
    return 0
  fi
  # 抽 h2+ 行首 token,剝尾部標點,再套 canonical filter。
  grep -E "${HEADING_LINE_RE}" "${file}" 2>/dev/null \
    | sed -E "s/${HEADING_LINE_RE}//" \
    | awk '{print $1}' \
    | sed -E 's/[^A-Za-z0-9_-].*$//' \
    | grep -E "${CANONICAL_ID_RE}" \
    | sort -u
}

synth_ids="$(extract_heading_ids "${SYNTH}")"

overall=0
sources_with_ids=0
for src in "$@"; do
  if [ ! -f "${src}" ]; then
    echo "COMPLETENESS FAIL: 來源檔不存在: ${src}"; overall=1; continue
  fi
  src_ids="$(extract_heading_ids "${src}")"
  if [ -z "${src_ids}" ]; then
    echo "COMPLETENESS WARN: ${src} 抽不到任何 heading ID(來源未用 ## <ID>?) → 本腳本無法保護,須人工/覆議"
    if [ "${STRICT}" = "1" ]; then
      overall=1
    fi
    continue
  fi
  sources_with_ids=$((sources_with_ids + 1))
  # comm 需 sorted;printf 保一行一 ID。
  missing="$(comm -23 <(printf '%s\n' "${src_ids}") <(printf '%s\n' "${synth_ids}"))"
  n_src="$(printf '%s\n' "${src_ids}" | grep -c .)"
  if [ -n "${missing}" ]; then
    n_miss="$(printf '%s\n' "${missing}" | grep -c .)"
    echo "COMPLETENESS FAIL: ${src} — ${n_miss}/${n_src} 個 ID 未出現在綜合檔:"
    # 引號保護,避免 HARDEN-a*b 等 metachar 被 shell glob 展開(紅隊 A13/CLEAN-M)。
    while IFS= read -r mid; do
      [ -n "${mid}" ] && printf '  · %s\n' "${mid}"
    done <<< "${missing}"
    overall=1
  else
    echo "COMPLETENESS PASS: ${src} — ${n_src}/${n_src} 個 ID 全在綜合檔。"
  fi
done

# 全滅 vacuous PASS:所有來源都無 ID 時不得 exit 0(紅隊 A5/A12/CLEAN-K)。
if [ "${sources_with_ids}" -eq 0 ]; then
  echo "COMPLETENESS FAIL: 無任何來源抽出 heading ID(vacuous;可能 prose-only 或未遵守 ## <ID> 慣例)。"
  exit 1
fi

if [ "${overall}" -ne 0 ]; then
  echo "COMPLETENESS FAIL: 有來源 finding ID 未進綜合(手抄掉項?)。補齊後重跑。"
  exit 1
fi
echo "COMPLETENESS PASS(dropped-ID 層): 全來源 heading ID 皆在綜合。注意:仍不保證語意忠實/無錯併/來源清單完整(須委員覆議+dispatch 注入來源)。"
exit 0
