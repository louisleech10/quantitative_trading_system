#!/usr/bin/env bash
# b15probe.sh — 主委自產版：對 gate_check.sh:86 的**現行正則**逐例重現 B-15 的三個 FP。
# 唯讀；不碰 repo 內任何腳本。正則字面複製自 scripts/gate_check.sh:86。
set -u

RE='(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'

# 與 gate_check.sh:81-84 等價的 env 前綴剝除
strip_env() {
  local c="$1"
  while printf '%s' "$c" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*='; do
    c="$(printf '%s' "$c" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+//')"
  done
  printf '%s' "$c"
}

# 回傳 0=會被判 dispatch(擋)  1=放行
verdict() {
  local cmd; cmd="$(strip_env "$1")"
  if printf '%s' "$cmd" | grep -Eq "$RE"; then
    # gate_check.sh:88 的排除
    if printf '%s' "$cmd" | grep -Eq 'scripts/gate(_check)?\.sh'; then return 1; fi
    return 0
  fi
  return 1
}

show() {
  local label="$1" cmd="$2" expect="$3"
  local v; verdict "$cmd"; v=$?
  local got; if [ "$v" -eq 0 ]; then got="BLOCK"; else got="ALLOW"; fi
  local mark; if [ "$got" = "$expect" ]; then mark="ok "; else mark="XX "; fi
  printf '%s %-6s want=%-5s | %s\n' "$mark" "$got" "$expect" "$label"
  if [ "$got" = "BLOCK" ]; then
    printf '      命中片段: %s\n' "$(printf '%s' "$cmd" | grep -Eo "$RE" | head -3 | tr '\n' '~')"
  fi
}

echo "===== TN：唯讀，應 ALLOW（B-15 的三個 FP）====="
show "FP-1 pgrep 查背景派工進程" \
     "pgrep -fl 'codex exec|cursor-agent|grok '" ALLOW
show "FP-2a for 迴圈讀三家產出（分號後接 do）" \
     'for f in codex composer grok; do cat handoffs/20260804-x-$f.md; done' ALLOW
show "FP-2b for 迴圈（家族名在 in 之後、分號前）" \
     'for f in codex composer grok ; do echo $f ; done' ALLOW
show "FP-3 completeness --lock" \
     "bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-govb0-recon" ALLOW
show "FP-3b completeness --lock（路徑含家族名）" \
     "bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-x/sources/grok.md" ALLOW
show "TN-4 cat 單一委員產出" \
     "cat handoffs/20260804-govflow-b4-review-codex.md" ALLOW
show "TN-5 ls 產出目錄" \
     "ls -l handoffs/reconcile/20260804-govb0-recon/sources/" ALLOW
show "TN-6 git commit 訊息含分號後家族名（今日實際踩到）" \
     'git commit -m "fix: no review file; codex closure review done"' ALLOW
show "TN-7 grep 委員名於檔案" \
     "grep -rn 'grok' docs/MULTI_AGENT_ORCHESTRATION.md" ALLOW

echo
echo "===== TP：真派工，必須 BLOCK ====="
show "TP-1 手搓 codex exec" \
     'codex exec -s workspace-write -o out.md "prompt"' BLOCK
show "TP-2 手搓 cursor-agent" \
     'cursor-agent -p --force --output-format text --model composer-2.5 "prompt"' BLOCK
show "TP-3 手搓 grok" \
     'grok -m grok-4.5 --sandbox read-only --always-approve -p "prompt"' BLOCK
show "TP-4 env 前綴繞過" \
     'GATE_DIR_OVERRIDE=/tmp codex exec -s workspace-write "prompt"' BLOCK
show "TP-5 管線後派工" \
     'cat brief.md | codex exec -s workspace-write "prompt"' BLOCK
show "TP-6 分號後派工" \
     'echo start; grok -m grok-4.5 -p "prompt"' BLOCK
show "TP-7 claude -p 子代理" \
     'claude -p "do something"' BLOCK
