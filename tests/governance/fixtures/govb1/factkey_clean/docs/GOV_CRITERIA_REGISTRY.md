# fixture 宿主檔（非真實文件）

本檔只為 governance-criteria 的 --check 正反對照存在。
🔴 本節刻意不寫任何期望結束狀態的字面形式——本檔即判準宿主，
區塊外出現該形式會被 fail-closed（WL-02）。要陳述請用判準 ID 指標。

<!-- BEGIN GENERATED: governance-criteria -->
| 判準ID | 適用範圍 | 條件 | 期望rc | 狀態 | 對應測試 |
|---|---|---|---|---|---|
| C-001 | gen_fact_key_blocks --check | 宿主生成區塊與註冊表一致 | 0 | 現行 | test_t21_assert_clean_fixture_rc_zero |
| C-002 | gen_fact_key_blocks --check | 宿主生成區塊與註冊表不一致 | 1 | 現行 | test_t21_assert_drifted_fixture_rc_nonzero_with_key_and_file |
| C-003 | gen_fact_key_blocks --check | 註冊表無任何 fact-key | 0 | 現行 | test_empty_registry_is_rc_zero_not_failure |
| C-004 | gen_fact_key_blocks emit | columns 含禁用字元（封閉集合判定） | 1 | 現行 | test_wl01_illegal_columns_is_fail_closed |
| C-005 | gen_fact_key_blocks emit | render 為 table 但未宣告 columns | 1 | 現行 | test_wl01_table_render_without_columns_is_fail_closed |
| C-006 | gen_fact_key_blocks emit | 資料列欄數與 columns 宣告不符 | 1 | 現行 | test_wl01_row_length_mismatch_is_fail_closed |
| C-007 | gen_fact_key_blocks emit | 儲存格含控制字元 | 1 | 現行 | test_wl01_control_char_in_cell_is_fail_closed |
| C-008 | gen_fact_key_blocks --check | 生成區塊外手寫狀態字面值 | 1 | 現行 | test_t21_handwritten_status_in_tracked_file_is_rejected |
| C-009 | gen_fact_key_blocks --check | 判準表同適用範圍同條件有相異期望 | 1 | 現行 | test_wl02_conflicting_criteria_is_fail_closed |
| C-010 | gen_fact_key_blocks --check | 判準宿主生成區塊外陳述期望結束狀態 | 1 | 現行 | test_wl02_rc_claim_outside_block_is_fail_closed |
| C-011 | gen_fact_key_blocks --check | 判準狀態值不在封閉列舉內 | 1 | 現行 | test_wl02_unknown_criteria_status_is_fail_closed |
| C-012 | gen_fact_key_blocks emit | columns 禁用字元以逐項列舉判定 | 1 | 已廢 | 見 C-004；本列為 CODEX-R1-P1-01 之前身判準，保留沿革 |
| C-013 | gen_fact_key_blocks emit | 機制登記列之證據欄不符封閉格式 | 1 | 現行 | test_wl03_illegal_evidence_form_is_fail_closed |
| C-014 | gen_fact_key_blocks emit | 機制登記列宣稱 receipt 但該檔不存在 | 1 | 現行 | test_wl03_receipt_pointing_at_missing_file_is_fail_closed |
| C-015 | gen_fact_key_blocks --check | opt-in 宿主之改法子樹含未登記平台機制 | 1 | 現行 | test_wl03_unregistered_mechanism_in_gaifa_subtree_is_fail_closed |
| C-016 | gen_fact_key_blocks --check | 非 opt-in 宿主含同樣未登記平台機制 | 0 | 現行 | test_wl03_non_optin_host_is_not_scanned_named_residual |
<!-- END GENERATED: governance-criteria -->
