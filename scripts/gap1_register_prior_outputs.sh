#!/usr/bin/env bash
# gap1_register_prior_outputs.sh — 一次性：把 GAP-1 前幾輪（R1–R7 與其戳記輪）之委員產出
# 補註冊進 .claude/gate/audit.log，使 claim checker 之委員豁免生效。
#
# 為何存在：前一個 session 產生了這些委員檔卻**未 commit**（本 session 收尾時才一併入版控），
# 而 `register-output` 是委員產出通過 claim checker 的必要步驟（見記憶 reference_dispatch_cli_invocation）。
# 逐檔對應之 task-id 依 `.claude/gate/audit.log` 之 committee_round_open 事件（session→task 對照）。
# 純一次性補登；不進任何流程。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2

register() {  # <task-id> <file-prefix>
  _task="$1"; _prefix="$2"
  for _fam in codex composer grok; do
    _f="handoffs/${_prefix}-${_fam}.md"
    [ -f "${_f}" ] || continue
    bash scripts/gate.sh register-output "${_task}" "${_f}" > /dev/null 2>&1 \
      && echo "  ok  ${_f}" || echo "  SKIP ${_f}"
  done
}

echo "[gap1-register] consult / review 輪"
register 20260817-GAP1-X-CONSULT-R1 20260817-gap1-recon
register 20260817-GAP1-X-REVIEW-R1  20260817-gap1-specadv
for n in 2 3 4 5 6 7; do
  register "20260817-GAP1-X-REVIEW-R${n}" "20260817-gap1-specadv-r${n}"
done

echo "[gap1-register] stamp 輪"
register 20260817-GAP1-X-STAMP-R1 20260817-gap1-stamp-c1
register 20260817-GAP1-X-STAMP-R2 20260817-gap1-stamp-v1
register 20260817-GAP1-X-STAMP-R3 20260817-gap1-stamp-r2
register 20260817-GAP1-X-STAMP-R4 20260817-gap1-stamp-v4
register 20260817-GAP1-X-STAMP-R5 20260817-gap1-stamp-v4b
register 20260817-GAP1-X-STAMP-R6 20260817-gap1-stamp-v5
register 20260817-GAP1-X-STAMP-R7 20260817-gap1-stamp-v6
echo "[gap1-register] 完成"
