#!/usr/bin/env bash
# spec_ruling_task_sync.sh — SPEC「裁定(§D)→施工(§P Task)」同步閘（SPEC-RULING-SYNC，2026-08-22）
#
# 病根：2026-08-22 GAP-3 UX SPEC，主委於 R2→R3 修訂 §D 裁定後**未同步 §P 之 Task**，
#   造成同一份 SPEC 內互斥條文並存：
#     · §D-7／Task 7.3 明訂「禁寫死 scenario 專屬文案」，而 Task 4.1b 仍**強制** vitest
#       斷言固定文案「正反例由 t0 條件決定，不看未來」⇒ 照 4.1b 實作，A/B 預測型 UI 會說謊
#       （CODEX-R3-P0-02／GROK-R3-P0-02 兩家獨立命中）
#     · §D-7 L1 已改「讀欄位級 lookahead_bars 標註」，而 Task 2.1b 仍只掃
#       `future_{N}bar_return` ⇒ R2 之 P0 在實作層原樣重現
#       （CODEX-R3-P0-01／GROK-R3-P0-01／COMPOSER-R3-P1-01/02）
#
#   主委記憶檔 `feedback_cross_reference_sync` 載明此類錯「同類錯犯 6 次；
#   **用 grep 機械掃殘留勿靠眼睛**」——2026-08-22 為**第 7 次**，且主委又是目視。
#   三家 consult 一致判定：「§D 裁定與 §P Task 分離且無派審前機械同步閘，
#   是**可重複的系統性方法缺陷**」（CODEX-R1-P0-02／GROK-R1-P1-02／COMPOSER-R1-P1-01）。
#   ⇒ 本腳本即該缺陷之機械化。紀律已證明無效（第 7 次），閘門才有效。
#
# 檢查兩件事：
#   A. **裁定必須落成 Task**：每條 `**D-<n>` 裁定須在 §P 被至少一個 Task 引用（`D-<n>` 字樣），
#      否則該裁定只停在敘述層 ⇒ Agent 無機械入口實作（R3 群集 B 之形態）。
#   B. **禁用語不得殘留**：§D 若宣告「禁 X」，全檔（含 §P）不得再有強制 X 之條文。
#      禁用語由 SPEC 自身以 `<!-- SYNC-FORBID: <regex> -->` 宣告，**不寫死於本腳本**
#      ——寫死清單就是下一個過期副本。
#
# 🔴 誠實邊界：
#   1. A 只驗「裁定編號有被 Task 引用」，**不驗語意是否真的落實**。
#      引用了但寫錯內容，本閘抓不到 ⇒ 由委員 review 承接。
#   2. B 之禁用語需 SPEC 作者主動以 `SYNC-FORBID` 標註；忘了標就擋不到。
#      **這是已知缺口，不宣稱已封**；但標註成本一行，且 R3 兩條 P0 皆屬可標註形態。
#   3. 本閘只掃單一 SPEC 檔內部一致性，不跨 SPEC/TODO 對證。
#
# 用法：
#   bash scripts/spec_ruling_task_sync.sh docs/XXX_SPEC.md
# rc: 0=同步；2=不同步（訊息在 stderr）
set -u

f="${1:-}"
if [ -z "${f}" ] || [ ! -f "${f}" ]; then
  echo "用法: bash scripts/spec_ruling_task_sync.sh <SPEC.md>" >&2
  exit 0
fi

_fail=0
_report=""

# ── A. 裁定 → Task 引用 ────────────────────────────────────────────────
# 裁定 heading 形態：行首 `**D-<n>` （本 repo SPEC 之既有慣例）
_rulings="$(grep -oE '^\*\*D-[0-9]+' "${f}" 2>/dev/null | sed 's/^\*\*//' | sort -u)"
# §P 起點（含之後全部內容）——裁定須被施工段引用才算落地
_p_start="$(grep -n '^## §P' "${f}" | head -1 | cut -d: -f1)"
if [ -n "${_p_start}" ] && [ -n "${_rulings}" ]; then
  _p_body="$(tail -n "+${_p_start}" "${f}")"
  while IFS= read -r r; do
    [ -n "${r}" ] || continue
    if ! printf '%s' "${_p_body}" | grep -q "${r}"; then
      _fail=1
      _report="${_report}  · 裁定 ${r} 未被 §P 任何 Task 引用 ⇒ 只停在敘述層，Agent 無機械入口
"
    fi
  done <<EOF
${_rulings}
EOF
fi

# ── B. SYNC-FORBID 禁用語殘留 ─────────────────────────────────────────
# SPEC 以 `<!-- SYNC-FORBID: <regex> -->` 宣告禁用語；宣告行本身與 §D 說明段豁免。
while IFS= read -r decl; do
  [ -n "${decl}" ] || continue
  pat="$(printf '%s' "${decl}" | sed -E 's/.*SYNC-FORBID:[[:space:]]*//; s/[[:space:]]*-->.*//')"
  [ -n "${pat}" ] || continue
  # 命中行：排除宣告行自身、markdown 引用行、含否定詞之行（那是在禁止而非主張）
  hits="$(grep -nE "${pat}" "${f}" 2>/dev/null \
          | grep -v 'SYNC-FORBID' \
          | grep -vE '^[0-9]+:[[:space:]]*>' \
          | grep -vE '不得|禁(止|用)|不適用|一律不|撤回|原寫|已改' || true)"
  if [ -n "${hits}" ]; then
    _fail=1
    _report="${_report}  · 禁用語殘留（SYNC-FORBID: ${pat}）：
"
    while IFS= read -r h; do
      [ -n "${h}" ] && _report="${_report}      ${f}:${h}
"
    done <<EOF
$(printf '%s' "${hits}" | head -5)
EOF
  fi
done < <(grep -o '<!--[[:space:]]*SYNC-FORBID:[^>]*-->' "${f}" 2>/dev/null || true)

if [ "${_fail}" -eq 0 ]; then
  exit 0
fi

{
  echo "[spec_ruling_task_sync] 🔴 ${f} 之裁定與施工段不同步"
  printf '%s' "${_report}"
  echo
  echo "  病根：改了 §D 裁定卻未同步 §P Task（feedback_cross_reference_sync 已載此類錯犯 7 次）。"
  echo "  修：①每條裁定至少被一個 Task 明文引用 ②禁用語不得在 §P 殘留。"
  echo "  禁用語以 SPEC 內 '<!-- SYNC-FORBID: <regex> -->' 宣告，本腳本不寫死清單。"
} >&2
exit 2
