#!/usr/bin/env bash
# spec_xref_check.sh — SPEC/TODO 改一處漏一處 之產出端閘（pre-commit）。
#
# 病根（2026-09-11 使用者當面質問「為何不每次都做全文掃描」）：VERDICTGATE SPEC 審八輪，
#   四輪的 finding 是「主委改了一段、同一概念在別處的引用沒同步」。記憶
#   feedback_cross_reference_sync 早在 2026-07 就寫了，靠紀律仍再犯六次 ⇒ 機械化。
#
# 判準（封閉、可證偽，不做語意判斷）：
#   對每個 staged 之 docs/*SPEC*.md｜docs/*TODO*.md，取 HEAD 版與 staged 版做行級 diff；
#   「被拿掉的概念」＝出現在 removed 行之反引號 token、且**不**出現在任何 added 行者。
#   該 token 若仍出現在 staged 版某行，而該行**沒有版本標記**（regex：v[0-9]+）⇒ 違規。
#   理由：合法殘留只有一種——「歷史敘述」，而歷史敘述本就該標它是哪一版的事。
#   要通過 = 真的同步改掉，或在那行標上版本（這正是正確寫法），沒有環境變數逃生口。
#
# 第二入口（使用者 2026-09-11：「不止 SPEC/TODO，每個要整理委員產出時候都會要用到」）：
#   --synth <synth.md> <target.md>：收斂檔群集表「處置」欄裡的反引號概念，必須在修訂標的
#   （SPEC/TODO）出現至少一次 ⇒ 擋「synth 說改了、標的沒改」。掛 debt_clear 前置。
#   誠實邊界：只驗「存在」，不驗語意等價（synth 寫 A、SPEC 寫 A' 抓不到）。
#
# 用法：bash scripts/spec_xref_check.sh [--staged | --files <old> <new> | --synth <synth> <target>]
#   --staged（預設）：讀 git index；無 SPEC/TODO 進 staged ⇒ rc=0 零成本。
#   --files old new  ：測試用，直接比對兩個檔案。
#   --synth s t      ：收斂檔 vs 修訂標的。
# rc：0 通過；1 違規；2 用法錯。
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 2
cd "$ROOT" || exit 2
py="venv/bin/python"; [ -x "$py" ] || py="$(command -v python3)"
[ -n "$py" ] || { echo "spec_xref_check: 無 python3" >&2; exit 2; }

MIN_TOKEN_LEN=6

_check_pair() {  # $1=old file  $2=new file  $3=label
  "$py" - "$1" "$2" "$3" "$MIN_TOKEN_LEN" <<'PY'
import difflib, re, sys
old_p, new_p, label, min_len = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
old = open(old_p, encoding="utf-8").read().splitlines()
new = open(new_p, encoding="utf-8").read().splitlines()
# 先正確配對所有反引號 span，再依長度過濾（若把長度寫進 regex，短 token 會讓後續配對錯位）
_span_re = re.compile(r"`([^`\n]+)`")
class _Tok:
    @staticmethod
    def findall(s):
        return [t for t in _span_re.findall(s) if len(t) >= min_len]
tok_re = _Tok
ver_re = re.compile(r"v[0-9]+")
removed, added = [], []
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
    if tag in ("replace", "delete"):
        removed.extend(old[i1:i2])
    if tag in ("replace", "insert"):
        added.extend(new[j1:j2])
added_text = "\n".join(added)
dropped = set()
for line in removed:
    for t in tok_re.findall(line):
        if t not in added_text:
            dropped.add(t)
violations = []
for t in sorted(dropped):
    for n, line in enumerate(new, 1):
        if t in line and not ver_re.search(line):
            violations.append((t, n, line.strip()[:110]))
if not violations:
    print(f"SPEC-XREF PASS: {label} — 被拿掉的概念 {len(dropped)} 個，殘留引用皆帶版本標記或已清")
    sys.exit(0)
print(f"SPEC-XREF FAIL: {label} — 下列概念在本次改動中被拿掉，但仍有未標版本的引用：")
for t, n, line in violations:
    print(f"  · `{t}` @L{n}: {line}")
print("  修法：同步改掉那一行，或在該行標明它是哪一版的歷史敘述（含 v<N>）。")
sys.exit(1)
PY
}

_check_synth() {  # $1=synth  $2=target
  "$py" - "$1" "$2" "$MIN_TOKEN_LEN" <<'PY'
import re, sys
synth_p, target_p, min_len = sys.argv[1], sys.argv[2], int(sys.argv[3])
synth = open(synth_p, encoding="utf-8").read()
target = open(target_p, encoding="utf-8").read()
# 只取「## 附錄」之前（群集／處置段），且只取表格列的第 4 欄（處置）
head = synth.split("## 附錄", 1)[0]
_span_re = re.compile(r"`([^`\n]+)`")
class _Tok:
    @staticmethod
    def findall(s):
        return [t for t in _span_re.findall(s) if len(t) >= min_len]
tok_re = _Tok
tokens = []
for line in head.splitlines():
    if not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 4 or cells[0] in ("群集", "---") or set(cells[0]) <= {"-"}:
        continue
    for t in tok_re.findall(cells[3]):
        if t not in tokens:
            tokens.append(t)
# 排除三種「不是概念」的反引號（封閉集合；對七份真實 synth 回放定出，勿再加）：
#   ① finding ID（FAMILY-R<n>-P<x>-<nn>）；② 實跑證據指令（git／bash／jq／sed 開頭）；
#   ③ 記憶檔名（feedback_／project_／reference_ 開頭）與行號引用（<name>.sh:<n>）
skip_re = re.compile(
    r"^([A-Z]+-R[0-9]+-P[0-3]-[0-9]{2}|(git|bash|jq|sed|grep|python3) .*|"
    r"(feedback|project|reference)_[a-z0-9_]+|[a-z_]+\.sh:[0-9]+(-[0-9]+)?)$"
)
tokens = [t for t in tokens if not skip_re.match(t)]
missing = [t for t in tokens if t not in target]
if not missing:
    print(f"SYNTH-XREF PASS: {synth_p} — 處置欄 {len(tokens)} 個概念皆見於 {target_p}")
    sys.exit(0)
print(f"SYNTH-XREF FAIL: {synth_p} — 處置欄下列概念在 {target_p} 找不到（synth 說改了、標的沒改？）：")
for t in missing:
    print(f"  · `{t}`")
sys.exit(1)
PY
}

mode="${1:---staged}"
case "$mode" in
  --synth)
    [ $# -eq 3 ] || { echo "用法: --synth <synth.md> <target.md>" >&2; exit 2; }
    [ -f "$2" ] && [ -f "$3" ] || { echo "spec_xref_check: 檔案不存在" >&2; exit 2; }
    _check_synth "$2" "$3"; exit $? ;;
  --files)
    [ $# -eq 3 ] || { echo "用法: --files <old> <new>" >&2; exit 2; }
    _check_pair "$2" "$3" "$3"; exit $? ;;
  --staged)
    rc=0
    while IFS= read -r -d '' rel; do
      [ -n "$rel" ] || continue
      case "$rel" in docs/*SPEC*.md|docs/*TODO*.md) : ;; *) continue ;; esac
      git cat-file -e "HEAD:${rel}" 2>/dev/null || continue   # 新檔無舊版可比
      tmp_old="$(mktemp)"; tmp_new="$(mktemp)"
      git show "HEAD:${rel}" > "$tmp_old"; git show ":${rel}" > "$tmp_new"
      _check_pair "$tmp_old" "$tmp_new" "$rel"; r=$?
      rm -f "$tmp_old" "$tmp_new"
      [ "$r" -ne 0 ] && rc=1
    done < <(git diff --cached --name-only --diff-filter=M -z)
    exit "$rc" ;;
  *) echo "用法: bash scripts/spec_xref_check.sh [--staged | --files <old> <new>]" >&2; exit 2 ;;
esac
