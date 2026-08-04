#!/usr/bin/env bash
# b15probe4.sh — 驗證 COMPOSER-R2-P0-01：eval / 命令替換 / 反引號 / 子 shell 是否 fail-open。
# 三欄對照：CURRENT（現行 gate_check.sh:86）／proto2（剝引號＋-c 遞迴）／期望。唯讀。
set -u

CUR='(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'
FAM='(^|[;&|][[:space:]]*)((\S*/)?(codex|cursor-agent|grok|agy))[[:space:]]'

strip_quotes() { printf '%s' "$1" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g"; }
extract_dashc() { printf '%s' "$1" | sed -nE "s/.*(bash|sh|zsh)[[:space:]]+-c[[:space:]]+['\"]([^'\"]*)['\"].*/\2/p"; }

cur()   { printf '%s' "$1" | grep -Eq "$CUR"; }
proto2(){
  local c="$1" inner
  printf '%s' "$(strip_quotes "$c")" | grep -Eq "$FAM" && return 0
  inner="$(extract_dashc "$c")"
  [ -n "$inner" ] && printf '%s' "$inner" | grep -Eq "$FAM" && return 0
  return 1
}

t() {
  local label="$1" cmd="$2" want="$3" a b
  if cur "$cmd";    then a=BLOCK; else a=ALLOW; fi
  if proto2 "$cmd"; then b=BLOCK; else b=ALLOW; fi
  local ma mb
  if [ "$a" = "$want" ]; then ma=ok; else ma=XX; fi
  if [ "$b" = "$want" ]; then mb=ok; else mb=XX; fi
  printf '  CURRENT=%s %-5s | proto2=%s %-5s | want=%-5s | %s\n' "$ma" "$a" "$mb" "$b" "$want" "$label"
}

echo "===== composer R2-P0-01 指出的四個向量（皆為真派工，want=BLOCK）====="
t "eval 包住"          'eval "codex exec x"'                  BLOCK
t "命令替換 \$()"       'out=$(codex exec x)'                  BLOCK
t "反引號"             'out=`codex exec x`'                   BLOCK
t "子 shell 括號"       '(codex exec x)'                       BLOCK
t "eval 單引號"        "eval 'grok -m grok-4.5 -p x'"          BLOCK
t "命令替換嵌 claude"   'v=$(claude -p "hi")'                  BLOCK

echo
echo "===== 對照：已知會擋的（回歸護欄）====="
t "裸 codex exec"      'codex exec -s workspace-write "p"'    BLOCK
t "bash -c 包住"        'bash -c "codex exec x"'               BLOCK
t "分號後"             'echo go; grok -m grok-4.5 -p "x"'      BLOCK

echo
echo "===== 對照：唯讀應放行 ====="
t "pgrep 引號內分隔符"  "pgrep -fl 'codex exec|cursor-agent|grok '" ALLOW
t "commit 訊息"        'git commit -m "fix: x; codex done"'    ALLOW
