# factkey_clean fixture root
# Task 2.1 以 GOVB1_FACTKEY_ROOT 指向此目錄；內容由 2.1 生成器契約定義。
# 本目錄於 Task 0.1 建立為存在性錨點（T-0.1-F1）。
#
# 內容（Task 2.1／B6 填入）：
#   docs/GOVERNANCE_EXECUTION_ORDER.md — 與 scripts/fact_keys.json 一致之 generated block
#   契約：`--check` rc=0
#
# 🔴 改了 scripts/fact_keys.json 之後，本 fixture 會轉紅（那正是它的用途）。
#    再生指令（不要手改 block）：
#      GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_clean \
#        bash scripts/gen_fact_key_blocks.sh --write
#    再生後須同步重做 factkey_drifted（見該目錄 README）。
