#!/usr/bin/env bash
# b15probe6.sh — 多行指令的行首錨點：引號內多行 vs 真正的多行指令。
# 驗證「剝引號」是否已足以解決，或真的需要單行正規化。唯讀。
set -u

START='(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?'
FAM3="${START}((\\S*/)?(codex|cursor-agent|grok|agy))[[:space:]]"
CUR='(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]'

strip_quotes() { printf '%s' "$1" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g"; }

# 注意：sed 的 s/// 預設不跨行，故引號內含換行時「剝引號」會失效 —— 這正是要測的點
strip_quotes_multiline() {
  # 用 awk 做跨行的引號 span 剝除（單引號與雙引號各自成對）
  printf '%s' "$1" | awk '
    BEGIN{ inq=0; q="" }
    {
      line=""; n=length($0)
      for(i=1;i<=n;i++){
        c=substr($0,i,1)
        if(inq){ if(c==q){ inq=0; q="" } }
        else { if(c=="\"" || c=="'\''"){ inq=1; q=c } else line=line c }
      }
      print line
    }'
}

t() {
  local label="$1" cmd="$2" want="$3"
  local a b c
  if printf '%s' "$cmd" | grep -Eq "$CUR"; then a=BLOCK; else a=ALLOW; fi
  if printf '%s' "$(strip_quotes "$cmd")" | grep -Eq "$FAM3"; then b=BLOCK; else b=ALLOW; fi
  if printf '%s' "$(strip_quotes_multiline "$cmd")" | grep -Eq "$FAM3"; then c=BLOCK; else c=ALLOW; fi
  local ma mb mc
  if [ "$a" = "$want" ]; then ma=ok; else ma=XX; fi
  if [ "$b" = "$want" ]; then mb=ok; else mb=XX; fi
  if [ "$c" = "$want" ]; then mc=ok; else mc=XX; fi
  printf '  CURRENT=%s %-5s | sed剝引號=%s %-5s | awk跨行剝=%s %-5s | want=%-5s | %s\n' \
    "$ma" "$a" "$mb" "$b" "$mc" "$c" "$want" "$label"
}

MSG='git commit -m "fix: something
codex 並獨立重跑探針確認
done"'

REAL='echo start
codex exec -s workspace-write "p"'

REAL2='set -e
grok -m grok-4.5 -p "x"'

TN2='git commit -m "line1
grok 那邊已複核
line3"'

echo "===== 引號內的多行字串（TN，應 ALLOW）====="
t "commit 訊息第 2 行以 codex 開頭" "$MSG" ALLOW
t "commit 訊息第 2 行以 grok 開頭"  "$TN2" ALLOW

echo
echo "===== 真正的多行指令（TP，應 BLOCK）====="
t "第 2 行是真的 codex exec" "$REAL" BLOCK
t "第 2 行是真的 grok -m"    "$REAL2" BLOCK
