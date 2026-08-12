# `票 B-25` 站 2.5（狀態事實入 fact-key）— 範圍延伸與具名偏離

> 凍結文件（`docs/GOVB1_INPUT_QUALITY_SPEC.md`／`_TODO.md`）**不就地修改**；
> 本檔為其延伸，記錄本次交付相對凍結宣告的每一處偏離與理由。
> 體例同 `docs/GOV_B6_SCOPE_AMENDMENT.md`、`GOV_B7_`、`GOV_B8_`。

- **標的**：`票 B-25` scope 擴充（`docs/GOVERNANCE_EXECUTION_ORDER.md` 序 `032` 站 2.5）
- **底本**：`docs/GOVB25_STATUS_FACTKEY_SPEC.md`（r5 定案）／`docs/GOVB25_STATUS_FACTKEY_TODO.md`
- **實作端**：主委自任　**審查**：codex ＋ composer（兩個非實作者家族）　**日期**：2026-08-10

---

## §1 偏離的凍結宣告

`docs/GOVB1_INPUT_QUALITY_TODO.md`「Task 2.1 實作要點 1」宣告 fact-key 註冊表
**初始只收 `governance-execution-order` 一項**，該宣告由
`tests/governance/test_govb1_factkey_gen.py::test_registry_is_valid_json_object_with_the_single_initial_key`
以 `assert fact_keys == [KEY]` 機械錨定。

站 2.5 之閉合條件要求「批次／票的完成狀態納入 fact-key」⇒ **必然新增 key** ⇒ 該斷言必然轉紅。

## §2 宣告之 fact-key 清單（**本節為機械 SoT，測試逐行讀取**）

```
FACTKEY-FROZEN: governance-execution-order
FACTKEY-ADDED: governance-batch-status
FACTKEY-ADDED: governance-ticket-closure
FACTKEY-ADDED: governance-worklist
FACTKEY-CRITERIA: governance-criteria
```

🔴 **第三種宣告 `FACTKEY-CRITERIA`（2026-08-13，待辦清單 `WL-02` 新增）**：
判準 key **不是**狀態 key（其第 2 欄為適用範圍而非識別碼，併入狀態偵測會大量誤擋）。
原契約 2 要求「`FACTKEY-ADDED` 恰等於 `status_keys`」，若把判準 key 寫成 `FACTKEY-ADDED`
會使該契約失效；改用第三種宣告，三條集合相等同時成立，反循環性質不變。

🔴 `governance-worklist`（使用者指示「寫在自己一定會看到、不會漏也不會讀錯的地方」）：
宿主＝`HANDOFF.md`（SessionStart 自動注入 ⇒ 接手必見）＋`白話說明/接下來要做什麼.md`。
待辦項之狀態自此為**機械投影**，任何文件手寫該狀態即 `--check` 非零。

**契約（測試強制，四條缺一即紅）**：
1. `scripts/fact_keys.json` 之 fact-key 集合 **恰等於** `FACTKEY-FROZEN` ∪ `FACTKEY-ADDED` ∪ `FACTKEY-CRITERIA`。
   （🔴 `WL-02` 起加入第三個聯集項；三個清單互不相交，亦以集合相等鎖死。）
1b. `FACTKEY-CRITERIA` 集合 **恰等於** `_schema.criteria_keys`。
2. `FACTKEY-ADDED` 集合 **恰等於** `scripts/fact_keys.json` 之 `_schema.status_keys`
   （🔴 原文寫「兩個狀態 key」，該數字於新增 `governance-worklist` 後過期；
   **不再寫死個數**——個數以 `status_keys` 為準，本檔只放指標）。
   🔴 此條為 r3 `CODEX-R3-P1-04` 之修法：單靠第 1 條是**自我循環**
   （延伸檔漏列一個 key，registry／測試／延伸檔三方仍互相一致而無人轉紅）。
3. 本檔缺失、或任一清單含重複項、或含未註冊之 key ⇒ 測試 fail-closed。
4. 比對一律為**集合相等**，禁 `issubset`／`>=`／`in`。

## §3 `票 B-51` 事前裁決 receipt

`票 B-51` 要求偏離凍結宣告**須先取得裁決才動碼**。本次裁決於 SPEC r2 審查輪取得：

| 家族 | 裁決 |
|---|---|
| codex | **(C) 核可但附條件** |
| composer | **(A) 核可**（附條件） |

出處：`handoffs/reconcile/20260810-govb25-x-review-r2/synth.md`「B-51 事前裁決 receipt」節。
使用者 2026-08-10 已授權此類技術裁決由主委與委員共識決、不上呈。

**兩家條件合併後之六項，逐條核對結果**：

| # | 條件 | 本次落實 |
|---|---|---|
| ① | 延伸檔體例對齊 `GOV_B8_SCOPE_AMENDMENT.md` | ✔ 本檔 |
| ② | 測試斷言與延伸檔 key 清單**集合相等**（禁 `issubset`／`>=`） | ✔ §2 契約 1、4 |
| ③ | 不得就地改凍結 `docs/GOVB1_INPUT_QUALITY_{SPEC,TODO}.md` | ✔ 兩檔未動 |
| ④ | 凍結 hash 閘須綠 | ✔ 收尾實跑 |
| ⑤ | 延伸檔 commit 帶 `Governance-Scope: out-of-epic` ＋ `--only g7` | ✔ 收尾實跑 |
| ⑥ | 延伸檔缺失／key 重複／含未知 key ⇒ 測試 fail-closed | ✔ §2 契約 3 |

## §4 本次交付相對 SPEC 的具名殘留

1. Phase 2（偵測器＋拆除 37 行字面狀態）**尚未交付**；依 SPEC §R 末列，
   **只交 Phase 1 判 BLOCKED、非完成**。
2. `docs/` 前綴除已登記 target 外不納入偵測範圍（多為凍結檔）。
3. `status_scope_grandfathered` 所列 7 個歷史日誌檔維持手寫；清單以集合相等鎖死，新增檔案不得靜默加入。
4. `票 B-25` 原條文之「判準資料化」（兩欄表格型 schema）不在站 2.5。
