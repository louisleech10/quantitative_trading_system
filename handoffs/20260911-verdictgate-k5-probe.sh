#!/usr/bin/env bash
# K5 probe（VERDICTGATE B3 R1 主委自查 CLAUDE-R1-P1-01）：SPEC 字面 `--push-range 0000000..<sha>` 修前 fail-open、修後 fail-closed。
# 用法：bash handoffs/20260911-verdictgate-k5-probe.sh  （只建暫存 repo，不動本 repo；不含任何委員名稱以免觸發 gate_check）
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d "${TMPDIR:-/tmp}/k5probe.XXXXXX")"
trap 'rm -rf "$W"' EXIT
mkdir -p "$W/repo/scripts" "$W/repo/.claude/gate"
git -C "$REPO" show d6c52c27:scripts/ticket_batch_check.sh > "$W/repo/scripts/tbc_old.sh"
cp "$REPO/scripts/ticket_batch_check.sh" "$W/repo/scripts/tbc_new.sh"
cp "$REPO/scripts/audit_append.sh" "$REPO/scripts/audit_events.json" "$W/repo/scripts/" 2>/dev/null || true
: > "$W/repo/.claude/gate/audit.log"
cd "$W/repo" || exit 2
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q -b main . ; printf '.claude/\n' > .gitignore; git add -A; git commit -q -m base
mkdir -p momentum; echo a > momentum/a.py; git add -A; git commit -q -m "feat: a (no trailer)"   # 無 hook ⇒ 等同 --no-verify
echo b > momentum/b.py; git add -A; git commit -q -m "feat: b" -m "Ticket-Batch: small"
sha="$(git rev-parse HEAD)"; ZERO='0000000000000000000000000000000000000000'
export GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="$W/repo/.claude/gate/audit.log" GATE_DIR_OVERRIDE="$W/repo/.claude/gate"
bash scripts/tbc_old.sh --push-range "${ZERO}..${sha}" --local-sha "$sha"; old_rc=$?
bash scripts/tbc_new.sh --push-range "${ZERO}..${sha}" --local-sha "$sha"; new_rc=$?
bash scripts/tbc_new.sh --push-range "deadbeef..${sha}" --local-sha "$sha"; bad_rc=$?
echo "K5 修前(d6c52c27) 全零 range rc=${old_rc}  （期望 0 ＝ fail-open：無 trailer 生產 commit 被放行）"
echo "K5 修後 全零 range rc=${new_rc}           （期望 ≠0：無 trailer 生產 commit 被擋）"
echo "K5 修後 不可解析 range rc=${bad_rc}       （期望 ≠0：fail-closed）"
[ "$old_rc" -eq 0 ] && [ "$new_rc" -ne 0 ] && [ "$bad_rc" -ne 0 ] && { echo "K5 PROBE: REPRODUCED-AND-FIXED"; exit 0; }
echo "K5 PROBE: UNEXPECTED"; exit 1
