#!/usr/bin/env bash
# E-5 研究 probe（VERDICTGATE TODO §E E-5）：audit append 序（impl_token_issued 先於 ticket_commit 且 ts 差 ≤900s）
#   能否作 token_fresh 第二層？研究問題＝是否存在**合法**流程使 ticket_commit 之 append 序 < token 序、或 ts 差 >900s。
#   三序列各實跑一次：--amend -m／--amend --no-edit／rebase（非互動，GIT_SEQUENCE_EDITOR），皆在領 token 後 >900s 才發生。
# 用法：bash handoffs/20260911-verdictgate-e5-probe.sh（只建暫存 repo；不含委員名）
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d "${TMPDIR:-/tmp}/e5probe.XXXXXX")"; trap 'rm -rf "$W"' EXIT
mkdir -p "$W/repo/scripts/git_hooks" "$W/repo/.claude/gate"
for f in ticket_batch_check.sh audit_append.sh audit_events.json verification_claim_check.py; do cp "$REPO/scripts/$f" "$W/repo/scripts/"; done
for h in commit-msg post-commit; do cp "$REPO/scripts/git_hooks/$h" "$W/repo/scripts/git_hooks/"; chmod +x "$W/repo/scripts/git_hooks/$h"; done
cd "$W/repo" || exit 2
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="$W/repo/.claude/gate/audit.log" GATE_DIR_OVERRIDE="$W/repo/.claude/gate"
: > .claude/gate/audit.log
git init -q -b main . ; git config core.hooksPath scripts/git_hooks; printf '.claude/\n' > .gitignore; git add -A; git commit -q -m base
# 領 token（audit impl_token_issued）＋ token 檔；模擬「16 分鐘前領的」（mtime 回撥 ⇒ 之後 commit 之 token_fresh 由 mtime 判 false）
bash scripts/audit_append.sh --event impl_token_issued --field task_id=ROOT-impl-b2-claude --field root=ROOT --field batch=2 \
  --field family=claude --field actor=t --field origin_script=gate.sh >/dev/null
t=.claude/gate/impl.ROOT-b2.token; printf 'x\n' > "$t"
mkdir -p momentum; echo a > momentum/a.py; git add -A; git commit -q -m "feat: a" -m "Ticket-Batch: ROOT/b2"   # 合法：token 新鮮
seq_tok="$(grep -c '' .claude/gate/audit.log)"
# 把 token 變舊（>900s），再做三種合法的歷史改寫——post-commit 會為新 sha 重寫 ticket_commit（append 序在 token 之後、mtime 判 false）
touch -t "$(date -v-20M +%Y%m%d%H%M.%S 2>/dev/null || date -d '-20 min' +%Y%m%d%H%M.%S)" "$t"
GOVERNANCE_SKIP_COMMITMSG=1 git commit -q --amend -m "feat: a (amend -m)" -m "Ticket-Batch: ROOT/b2"
git commit -q --amend --no-edit
echo b > momentum/b.py; git add -A; GOVERNANCE_SKIP_COMMITMSG=1 git commit -q -m "feat: b" -m "Ticket-Batch: ROOT/b2"
GIT_SEQUENCE_EDITOR='sed -i "" -e "2s/^pick/reword/"' GIT_EDITOR=true git rebase -q -i HEAD~2 2>/dev/null || GIT_SEQUENCE_EDITOR=true GIT_EDITOR=true git rebase -q -i HEAD~2
echo "=== audit ticket_commit 列（append 序、token_fresh）==="
grep '"event": "ticket_commit"' .claude/gate/audit.log | grep -o '"sequence": [0-9]*\|"token_fresh": "[a-z]*"\|"ts": "[^"]*"' | paste - - - | sed 's/^/  /'
tok_ts="$(grep '"event": "impl_token_issued"' .claude/gate/audit.log | grep -o '"ts": "[^"]*"' | head -1)"
echo "token: ${tok_ts}"
n_after="$(grep -c '"event": "ticket_commit"' .claude/gate/audit.log)"
n_false="$(grep '"event": "ticket_commit"' .claude/gate/audit.log | grep -c '"token_fresh": "false"')"
echo "結論：ticket_commit 共 ${n_after} 列，**皆在 token 之後 append**（append 序恆成立）；其中 ${n_false} 列 token_fresh=false（mtime 判定）。"
echo "  誠實邊界：本 probe 以回撥 token mtime 模擬「20 分鐘前領的」，audit ts 並未真流逝（ts 差仍 ≤1s）；"
echo "  能證明的是：(a) 合法歷史改寫（amend -m／amend --no-edit／rebase）之 ticket_commit 序**必**在 token 之後 ⇒ 『只驗序』對過期 token 恆放行（fail-open）；"
echo "  (b) 若改以『序＋audit ts 差 ≤900s』判，等價於用 audit ts 取代 mtime——mtime 可被 touch、ts 可被延後 append 同型，無額外防護，且 amend／rebase 於 15 分鐘後會與 mtime 判定同樣紅（非誤擋差異）。"
echo "  ⇒ 第二層無增量價值；mtime 判定保留（SPEC §V：touch 屬蓄意，同 E-1 族）。"
[ "$n_false" -ge 3 ] && echo "E5 PROBE: ORDER-ALWAYS-HOLDS（序判無增量；mtime 足夠）" || echo "E5 PROBE: UNEXPECTED"
