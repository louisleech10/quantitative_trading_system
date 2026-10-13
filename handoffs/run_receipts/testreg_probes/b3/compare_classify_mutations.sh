#!/usr/bin/env bash
# compare_classify.py 之 fail-closed 反例實跑（諮詢 r3 CODEX-R3-P1-04 處置之證據）。
# 以 G3 主委表為基底（須 PASS），逐案造一個缺陷副本，斷言比對器 rc=1；任一案 rc≠預期 ⇒ 本腳本 exit 1。
# 用法：bash compare_classify_mutations.sh
set -u
D="$(cd "$(dirname "$0")" && pwd)"
CMP="venv/bin/python $D/compare_classify.py"
SCOPE="$D/G3.txt"
BASE="$D/claude_G3.md"
TMP="$(mktemp -d)"
fail=0
run_case() {  # $1 名稱 $2 預期 rc $3 檔
  $CMP "$SCOPE" "$TMP/out.tsv" "x=$3" > "$TMP/$1.log" 2>&1
  rc=$?
  if [ "$rc" = "$2" ]; then echo "ok   $1 rc=$rc"; else echo "FAIL $1 rc=$rc（預期 $2）"; fail=1; fi
}
first_row() { awk -F'\t' 'f && NF==9 && $1 ~ /^tests\// {print NR; exit} /^```testreg-classify/ {f=1}' "$BASE"; }
R=$(first_row)
run_case baseline 0 "$BASE"
awk -v r="$R" 'NR!=r' "$BASE" > "$TMP/missing.md";                                 run_case missing_row 1 "$TMP/missing.md"
awk -v r="$R" '{print} NR==r {print}' "$BASE" > "$TMP/dup.md";                     run_case duplicate_row 1 "$TMP/dup.md"
awk -v r="$R" 'BEGIN{OFS="\t"} {if (NR==r) {print; $1="tests/test_not_in_scope.py"} print}' FS='\t' "$BASE" > "$TMP/extra.md"; run_case extra_row 1 "$TMP/extra.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$2="A99"} {print}' "$BASE" > "$TMP/enum.md"; run_case bad_guarantee_enum 1 "$TMP/enum.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$3="unclassified"} {print}' "$BASE" > "$TMP/uncl.md"; run_case unclassified_oracle 1 "$TMP/uncl.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$5="rewrite"; $6=$1"::test_function_that_does_not_exist"} {print}' "$BASE" > "$TMP/nofunc.md"; run_case missing_function 1 "$TMP/nofunc.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$5="keep"; $6=$1"::x"} {print}' "$BASE" > "$TMP/keeptgt.md"; run_case keep_with_targets 1 "$TMP/keeptgt.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$8=$1":999999"} {print}' "$BASE" > "$TMP/ev.md";  run_case evidence_out_of_range 1 "$TMP/ev.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$8="tests/no_such_file.py:1"} {print}' "$BASE" > "$TMP/evf.md"; run_case evidence_missing_file 1 "$TMP/evf.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$9=$9"\textra"} {print}' "$BASE" > "$TMP/tab.md"; run_case note_with_tab 1 "$TMP/tab.md"
awk -v r="$R" 'BEGIN{FS=OFS="\t"} NR==r {$7=$1"::nope:E9:-"} {print}' "$BASE" > "$TMP/tomb.md"; run_case bad_tombstone 1 "$TMP/tomb.md"
sed 's/^```testreg-classify$/```text/' "$BASE" > "$TMP/notable.md";                 run_case no_table 1 "$TMP/notable.md"
echo "tmp=$TMP"
exit $fail
