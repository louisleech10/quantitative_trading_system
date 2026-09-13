# SPLITUNIFY b9 — review-r20 D1／D2 閉合再驗證

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 本輪要做什麼（一句話）
**逐條重跑你自己在 review-r20 提出的反例**（章程 §B8：閉合須由**原提出方**重跑同一反例，不憑「已修」信任）。

| finding | 提出方 | 修補摘要 |
|---|---|---|
| `CODEX-R20-P1-01`／`COMPOSER-R20-P1-01`／`GROK-R20-P1-01` | 三家 | 重建 `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`——fixture 用**事件級** manifest（`Task 9.2a` 之責）、兩個 feature TF 且 cutoff 分落 train／test 段；異側 fail-closed 屬 `Task 9.2b` ⇒ 以 `xfail(strict=True)` 明示，**不得** `--deselect` |
| `CODEX-R20-P2-01`／`COMPOSER-R20-P2-01`／`GROK-R20-P2-01` | 三家 | 新增 `test_multi_symbol_branch_summary_counts_are_named`——逐值斷言三鍵並**明文擋 0 值** |
| 額外（非本輪 finding） | codex 掃出 | `handoffs/20260911-probe-splitunify-negative-injection.py` 之 `_keys()` 補 `feature_timeframe`（codex 判非阻擋，主委仍一併補） |

## 審查標的（🔴 輸入邊界）
- **本輪 diff**：`git show ef4d0664`
- **current block**：`tests/momentum/Analysis/test_splitunify_derive.py` 檔末兩條新測試；`docs/SPLITUNIFY_TODO.md` 之 `§C-9 Task 9.2a` 驗證段
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 正文（v18 三家戳記 rc=0、本輪未動）、`HISTORY-BEGIN..END`、「## 沿革與追溯索引」節。
- 🔴 **不得重開**：`Task 9.2b`–`9.5` 之設計、`Task 9.1`／B9B 已閉合者、r17 共識決、混態屬 9.2b 之裁定。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: TODO 第 6 條逐字命令通過 → `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` 輸出 `1 xfailed`（非 `1 passed`、非 `no tests ran`）。派工後預期值: 不變（唯讀審查）。
fact-verified: 兩條新測試各自實跑破壞驗鑑別力 → 多 symbol 分支刪掉三個 kwargs ⇒ `test_multi_symbol_branch_summary_counts_are_named` 轉紅；還原後綠。
fact-verified: 回歸 → 六路指定測試集實跑得 **706 passed、1 xfailed**（該 xfail 即上述設計上的過渡狀態）。VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise
fact-verified: 第三個同型漏網已補 → `handoffs/20260911-probe-splitunify-negative-injection.py` 之 `_keys()` 已含 `feature_timeframe`。

assumed: 重建之 xfail 測試**在 `Task 9.2b` 完成後會自然轉為 pass**（而非需要再改測試）。**我的否證觀測（已先跑）**：其 `pytest.raises` 之 match 為 `同一事件|異側|同側|AlignmentViolation`，與 `Task 9.2b` 條文所定之 `AlignmentViolationError` 訊息要求相容。**我沒查**：`Task 9.2b` 實際實作時錯誤訊息是否**必然**含上述任一字串——若訊息用別的措辭，`strict=True` 會在 9.2b 完成時變成 XPASS 而紅，屆時又要改測試。← **請直接攻這條**，並判是否該把 match 收緊成僅 `AlignmentViolation`。
assumed: `xfail(strict=True)` 是此處**最好**的表達方式。**我的否證觀測（已先跑）**：TODO 明文要求 `1 xfailed`、明文禁 `--deselect`。**我沒查**：是否有更好的表達（例如 `pytest.mark.skip` 加一條獨立的「9.2b 未實作」斷言），以及 `strict` 在 9.2b 完成當下的**交接摩擦**（實作者必須同時改碼與拿掉標記，否則 CI 紅）。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| xfail 錨點存在性 | TODO 第 6 條逐字命令得 `1 xfailed` | 該測試之 fixture 是否**真的**構造出異側（而非因別的錯誤而紅）——請實跑並看 raise 的是哪一個例外 |
| 多 symbol 三計數 | 逐值＋擋 0 值，實跑驗紅 | 是否涵蓋「某 symbol 子批為空」之情形 |
| 回退遺漏之同型漏網 | 已補三處（探針×2、xfail 錨點×1） | 🔴 **是否還有第四處**——請全 repo 掃「建構 `event_keys` 或引用 `build_event_keys` 而未隨 `Task 9.2` 更新」者 |
| TODO 條文 | 已補新測試名與 mutation 字面 | TODO 是否還有別處條文與現行實作不一致 |

## 必答（逐條 verdict；成對，不得只答一半）
1. **(1a)** 逐條重跑你在 review-r20 提出的反例，給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出你重跑的命令與觀測到的輸出特徵。
2. **(2a)** 重建之 xfail 測試是否**真的**因「異側」而紅？請實跑並指出 raise 的例外與訊息。
   **(2b)** 其 `match` 是否該收緊成僅 `AlignmentViolation`？給理由。
3. **(3a)** `xfail(strict=True)` 在 `Task 9.2b` 完成當下的交接摩擦有多大？有更好的表達嗎？
   **(3b)** 若有，給可直接貼入的替代寫法；若無，說明為何現行最好。
4. **(4a)** 全 repo 是否還有**第四處**未隨 `Task 9.2` 更新的 `event_keys` 建構點或呼叫端？逐處列出。
   **(4b)** 若有，判是否阻擋。
5. **(5a)** 可以進 `Task 9.2b`（批次 `B9C`）了嗎，還是有 BLOCKING 必須先修？
   **(5b)** 若可以，說明你檢查了什麼；若不可以，列**最小**閉合集合。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼、禁改 SPEC、禁改 TODO**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
