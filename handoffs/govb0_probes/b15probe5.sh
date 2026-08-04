#!/usr/bin/env bash
# b15probe5.sh — 原型③：把「命令位置」擴大到所有 shell 命令起始語境。
# 起始語境集合：行首 / ; / & / | / ( / ` / $( / && / || / eval 之後 / xargs 之後。
# 對照 proto2（僅 ^ ; & |）。唯讀。
set -u

# 命令起始前綴：行首，或 ; & | ( ` 之後（含 $( 與 && || 自然涵蓋），或 eval/xargs 之後
START='(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?'
FAM3="${START}((\\S*/)?(codex|cursor-agent|grok|agy))[[:space:]]"
CLA3="${START}(\\S*/)?claude[[:space:]]+([^[:space:]]+[[:space:]]+)*(-p|--print)([[:space:]]|$)"

FAM2='(^|[;&|][[:space:]]*)((\S*/)?(codex|cursor-agent|grok|agy))[[:space:]]'

strip_quotes() { printf '%s' "$1" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g"; }
extract_dashc() { printf '%s' "$1" | sed -nE "s/.*(bash|sh|zsh)[[:space:]]+-c[[:space:]]+['\"]([^'\"]*)['\"].*/\2/p"; }
# eval 的引號引數同樣是「一整條命令」，須比照 -c 遞迴
extract_eval()  { printf '%s' "$1" | sed -nE "s/.*(^|[;&|(\`[:space:]])eval[[:space:]]+['\"]([^'\"]*)['\"].*/\2/p"; }

proto2(){
  local c="$1" inner
  printf '%s' "$(strip_quotes "$c")" | grep -Eq "$FAM2" && return 0
  inner="$(extract_dashc "$c")"
  [ -n "$inner" ] && printf '%s' "$inner" | grep -Eq "$FAM2" && return 0
  return 1
}
proto3(){
  local c="$1" s inner
  s="$(strip_quotes "$c")"
  printf '%s' "$s" | grep -Eq "$FAM3" && return 0
  printf '%s' "$s" | grep -Eq "$CLA3" && return 0
  for inner in "$(extract_dashc "$c")" "$(extract_eval "$c")"; do
    [ -n "$inner" ] || continue
    printf '%s' "$inner" | grep -Eq "$FAM3" && return 0
    printf '%s' "$inner" | grep -Eq "$CLA3" && return 0
  done
  return 1
}

t() {
  local label="$1" cmd="$2" want="$3" a b ma mb
  if proto2 "$cmd"; then a=BLOCK; else a=ALLOW; fi
  if proto3 "$cmd"; then b=BLOCK; else b=ALLOW; fi
  if [ "$a" = "$want" ]; then ma=ok; else ma=XX; fi
  if [ "$b" = "$want" ]; then mb=ok; else mb=XX; fi
  printf '  proto2=%s %-5s | proto3=%s %-5s | want=%-5s | %s\n' "$ma" "$a" "$mb" "$b" "$want" "$label"
}

echo "===== TP：真派工，必須 BLOCK ====="
t "裸 codex exec"      'codex exec -s workspace-write "p"'      BLOCK
t "絕對路徑"           '/opt/homebrew/bin/codex exec hi'        BLOCK
t "bash -c 包住"        'bash -c "codex exec x"'                 BLOCK
t "sh -c 包住"          "sh -c 'grok -m grok-4.5 -p x'"          BLOCK
t "分號後"             'echo go; grok -m grok-4.5 -p "x"'        BLOCK
t "管線後"             'cat b.md | codex exec "p"'              BLOCK
t "eval 包住"          'eval "codex exec x"'                    BLOCK
t "命令替換 \$()"       'out=$(codex exec x)'                    BLOCK
t "反引號"             'out=`codex exec x`'                     BLOCK
t "子 shell 括號"       '(codex exec x)'                         BLOCK
t "&& 之後"            'true && codex exec x'                   BLOCK
t "|| 之後"            'false || grok -m x -p y'                BLOCK
t "claude -p"          'claude -p "do it"'                      BLOCK
t "claude 命令替換"     'v=$(claude -p "hi")'                    BLOCK
t "claude 絕對路徑"     '/usr/local/bin/claude --print "x"'      BLOCK
t "xargs 後"           'echo x | xargs codex exec'              BLOCK

echo
echo "===== TN：唯讀，必須 ALLOW ====="
t "pgrep 引號內分隔符"  "pgrep -fl 'codex exec|cursor-agent|grok '"  ALLOW
t "commit 訊息含分號"   'git commit -m "fix: x; codex closure done"'  ALLOW
t "檔名子字串"         'cat sp_codex.txt'                       ALLOW
t "scratchpad + rev-parse" 'head -3 /private/tmp/claude-501/x.out; git rev-parse HEAD' ALLOW
t ".claude + porcelain" 'ls .claude/tmp; git status --porcelain'  ALLOW
t "find -print"        'find .claude/tmp -name "*.md" -print'    ALLOW
t "grep 委員名"        "grep -rn 'grok' docs/ORCH.md"           ALLOW
t "claude 在檔名中段"   'cat my-claude-notes.md'                 ALLOW
t "目錄名為 grok"       'ls /tmp/grok/notes.md'                  ALLOW
t "唯讀查 cx_run"       'sed -n "1,40p" scripts/cx_run.sh'       ALLOW
