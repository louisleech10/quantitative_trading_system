# 判準登記表（唯一來源）

FACT-KEY: governance-criteria
LAST-RULED: 2026-08-13
RULED-BY: 三家委員 consult（`handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md`）

---

## 本檔的地位

**本檔是「判準」這件事的唯一來源。** 判準＝「在某個適用範圍下，某個條件成立時，期望的結束狀態」。

| 對象 | 允許的寫法 |
|---|---|
| 本檔生成區塊 | 唯一可陳述期望結束狀態之處 |
| 本檔其他段落 | **只得寫判準 ID 指標**；寫期望結束狀態的字面形式即 fail-closed |
| 其他文件 | 不受本機制管制（**面向未來不溯及既往**，見下方殘留） |

改法＝改 `scripts/fact_keys.json` 的 `governance-criteria`，再跑
`bash scripts/gen_fact_key_blocks.sh --write`。

## 三道機械檢查（皆在 `gen_fact_key_blocks.sh --check` 內）

1. **狀態列舉封閉**：`狀態` 欄只收 `_schema.criteria_status_enum` 所列值，未知值 fail-closed。
   〔`CODEX-R1-P1-03`：未宣告封閉列舉時，未知值會被當普通字串接受〕
2. **同範圍同條件不得有相異期望**：`狀態` 為現行者，同一 `(適用範圍, 條件)` 出現相異
   `期望rc` ⇒ fail-closed。這就是待辦清單第二項的字面要求，只是作用在**資料**而非散文。
3. **本檔生成區塊外不得寫期望結束狀態**：以**封閉白名單**比對（非黑名單列舉），
   範圍**只有**本檔（＝判準 key 之 target），且豁免本檔全部合法生成區塊。
   〔`COMPOSER-R1-P1-01`／`GROK-R1-P1-02`：只釘三個字母會被同義寫法繞過，
   `docs/GOV_GATECHAIN_SPEC.md` 內已存在該同義用法〕

## 🔴 具名殘留（**不得宣稱本機制已封死互斥判準**）

1. 🔴 **語意互斥不被攔截**：兩段話若用**不同的條件字串**描述同一物理事件
   （出生事故那型：「依賴腳本缺檔」vs「已在具名略過清單」），鍵不相等 ⇒ 衝突偵測靜默放行。
   **該型仍只能靠人／review 抓。** 三家一致（`GROK-R1-P1-01`／`CODEX-R1-P1-01`／`COMPOSER-R1-P2-01`）。
   ⇒ 寫判準時的紀律：**同一物理事件必須共用同一條件字串**。此為紀律，非機械強制。
2. 🔴 **membership 靠登記，不靠有沒有區塊**：未登記的檔案即使貼一組看起來像本表的生成標記，
   **也不會被掃描**（`CODEX-R1-P1-02`）。要進入管制只有一條路——在註冊表登記為 target。
3. 🔴 **本表是目錄／投影，不是實作行為的 oracle**：改表不改碼、改碼不改表，
   本檔的檢查都仍會綠（`GROK-R1-P2-01`／`CODEX-R1-P1-03`）。
   行為承重在 `對應測試` 欄所指的那條測試，**不在本表**。
4. **既有文件不溯及**：`docs/` 既有以散文陳述期望結束狀態的行（量級 700–800 行，
   確切數字隨比對式寬嚴而異——**引用時必須同時給比對式**）一律不動、不掃。
   使用者 2026-08-05 定死「修正只考慮以後」。
6. 🔴 **白名單只涵蓋具名形態，不涵蓋關係型／轉換型陳述**：
   涵蓋集合是**實測導出**（三家於 r2 各自掃描本庫得出，非想像列舉），
   具名清單見 `scripts/gen_fact_key_blocks.sh` 之 `_FK_RC_CLAIM_FORMS`（測試以集合相等鎖死）。
   **刻意不納入**「最終狀態與第一份一致」「由通過變為不通過」這類**關係型**陳述——
   那需要理解語意，一納入就退化成無限黑名單。該類仍靠 review。
   〔`CODEX-R2-P1-01`／`COMPOSER-R2-P1-01`／`GROK-R2-P1-01`：
   主委原宣稱「六種足以涵蓋實務」已被三家各自實測證偽並更正〕
7. `對應測試` 的存在性只在 pytest 檢查，不在 `--check` 內；且只驗函式存在，
   不驗它有沒有被 skip 或是不是空心（`COMPOSER-R2-P2-01`，兩家判為可接受邊界）。

5. 備案軸向已否決：「同區段內數字期望與『不變』並存」雖有訊號，但人工複核顯示
   命中者**全部**是同一 Task 內多個不同條件各有其期望的合法寫法 ⇒ 當 FAIL 會大量誤擋
   （`COMPOSER-R1-P1-02`）。不做。

## 判準表

> 欄名見表頭（機械產物）。`對應測試` 欄指向真正承重的那條測試；
> 有一條檢查會驗證該測試確實存在，防止本表變成無人對照的散文目錄。

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
