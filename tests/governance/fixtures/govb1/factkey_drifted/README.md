# factkey_drifted fixture root
# Task 2.1 以 GOVB1_FACTKEY_ROOT 指向此目錄；內容由 2.1 生成器契約定義。
# 本目錄於 Task 0.1 建立為存在性錨點（T-0.1-F1）。
#
# 內容（Task 2.1／B6 填入）：
#   docs/GOVERNANCE_EXECUTION_ORDER.md — generated block 內恰一列被竄改（序數 140 之票號）
#   契約：`--check` rc≠0，且訊息含 key 與檔名
#
# 🔴 漂移只改「block 內一列的值」，不改標記、不改列數——
#    若改成刪標記，測到的就變成「缺標記」那條路徑，正反對照會失去鑑別力。
#
# 再生（scripts/fact_keys.json 改動後）：
#   1) GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_drifted \
#        bash scripts/gen_fact_key_blocks.sh --write
#   2) 再把序數 140 那一列的票號改成不存在的值（如 B-99（竄改））
