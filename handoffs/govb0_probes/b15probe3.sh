#!/usr/bin/env bash
# b15probe3.sh — 驗證 COMPOSER-R1-P0-01：引號感知會不會打開 bash -c 這個洞。
# 兩個原型：①單純剝除引號內容 ②引號感知 tokenize + 對 -c 引數遞迴。唯讀。
set -u
RE='(^|[;&|][[:space:]]*)((\S*/)?(codex|cursor-agent|grok|agy))[[:space:]]'

# 原型①：剝除單/雙引號 span 內容後比對（SPEC Task 2.1 目前的寫法）
strip_quotes() {
  printf '%s' "$1" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g"
}
proto1() { printf '%s' "$(strip_quotes "$1")" | grep -Eq "$RE"; }

# 原型②：剝除後比對；另外把 (bash|sh|zsh) -c 的引號引數取出來遞迴比對
extract_dashc() {
  printf '%s' "$1" | sed -nE "s/.*(bash|sh|zsh)[[:space:]]+-c[[:space:]]+['\"]([^'\"]*)['\"].*/\2/p"
}
proto2() {
  local c="$1" inner
  if printf '%s' "$(strip_quotes "$c")" | grep -Eq "$RE"; then return 0; fi
  inner="$(extract_dashc "$c")"
  if [ -n "$inner" ] && printf '%s' "$inner" | grep -Eq "$RE"; then return 0; fi
  return 1
}

t() {
  local label="$1" cmd="$2" want="$3"
  local r1 r2
  if proto1 "$cmd"; then r1=BLOCK; else r1=ALLOW; fi
  if proto2 "$cmd"; then r2=BLOCK; else r2=ALLOW; fi
  local m1 m2
  if [ "$r1" = "$want" ]; then m1=ok; else m1=XX; fi
  if [ "$r2" = "$want" ]; then m2=ok; else m2=XX; fi
  printf '  proto1=%s %-5s | proto2=%s %-5s | want=%-5s | %s\n' "$m1" "$r1" "$m2" "$r2" "$want" "$label"
}

echo "===== TP：真派工，必須 BLOCK ====="
t "裸 codex exec"          'codex exec -s workspace-write "p"'                      BLOCK
t "絕對路徑 codex"          '/opt/homebrew/bin/codex exec hi'                        BLOCK
t "COMPOSER-P0-01: bash -c 包住派工" 'bash -c "codex exec x"'                        BLOCK
t "sh -c 包住派工"          "sh -c 'grok -m grok-4.5 -p x'"                          BLOCK
t "分號後派工"              'echo go; grok -m grok-4.5 -p "x"'                       BLOCK

echo
echo "===== TN：唯讀，必須 ALLOW ====="
t "pgrep 引號內含分隔符"    "pgrep -fl 'codex exec|cursor-agent|grok '"              ALLOW
t "commit 訊息含分號家族名"  'git commit -m "fix: no review file; codex closure done"' ALLOW
t "cat 檔名子字串"          'cat sp_codex.txt'                                       ALLOW
t "grep 委員名於文件"        "grep -rn 'grok' docs/MULTI_AGENT_ORCHESTRATION.md"      ALLOW
