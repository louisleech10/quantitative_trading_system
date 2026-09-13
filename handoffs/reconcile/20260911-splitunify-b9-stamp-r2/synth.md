# Reconcile — 20260911-splitunify-b9-stamp-r2

**來源** 20260911-splitunify-b9-stamp-r2-codex.md　|　**roster** codex

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **Y1 殘留段之「20 列」字面在 `C5-25` 補錨後已過期**——「current`SU-RESID-C5-」 | P2 | CODEX-R2-P2-01 | 採納（主委複驗成立：現行 register 為 keyed **10**／basename **4**／`NO-ANCHOR` **15**，缺精確 `path:line` 者實為 **19** 列，而 `SU-RESID-C5-TARGETS` 殘留段仍寫 20。已改為 19 並註明來源。🔴 **這是同一個「改 A 沒同步 B」的第三次**——`C5-25` 補錨這一個動作先後打翻了驗收第 5 點的「9／20」（r17 X3）與殘留段的「20」（本條），兩次都不是同一行。該家另於必答 2b 給出 (乙) 4 列之逐字 ID `C5-15`／`C5-16`／`C5-17`／`C5-18`，主委以機械複驗四列皆「有檔名、無行號」屬實 ⇒ 一併寫入條文，取代原本的「29 − 10 − 15」算式） |

### 本輪裁定
1. **`CODEX-R17-P1-01`／`CODEX-R17-P1-02` 由原提出方 CLOSED**，其對 `docs/SPLITUNIFY_SPEC.D-002.md` body `d42b3f14…` 之戳記由 REJECTED 轉 **APPROVED**。
2. 🔴 **`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0——三家（codex／composer／grok）全數 APPROVED 且本體雜湊相符**。本檔自 R1 起十七輪，至此首次取得完整且有效之三家戳記。
3. **Y1 已修**（`Task 9.3` 驗收第 5 點之 (乙) 段具名四列；`SU-RESID-C5-TARGETS` 之 20 改為 19）。本條為 P2、該家明示不阻擋重簽。
4. **下一步＝領 impl token 進 `Task 9.1`**（`docs/SPLITUNIFY_TODO.md` `§C-9` 動工前置三條已全數滿足）。

Verdict：可合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P2-01
**斷言**: current `SU-RESID-C5-TARGETS` 仍寫「那 20 列」；現行 register 是 10 keyed／4 basename／15 `NO-ANCHOR`，故缺精確 `path:line` 實為 19 列，殘留字面會過度指示 TARGETS 範圍。
**碼證**: VERIFY: `awk` register 分類輸出 `keyed=10 basename=4 no_filename=15 total=29`，另算 `rows_without_exact_path_line=19`；CODE-ANCHOR: `docs/SPLITUNIFY_TODO.md:670`; MUTATION: 依「20 列」建立 TARGETS 清單再以 current register 重掃，會得到實際 19 列，且把已在 keyed 組的 `C5-25` 重複納入；RECHECK: 同兩條 awk 命令重跑。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#0c76ece1efac`
修法：將殘留段的 20 改為 19；可行性為單一字面同步。本 P2 不阻擋本輪 body 重簽。


## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
> 本收斂檔為 SPLITUNIFY b9 進入 `Task 9.1` 實作之授權依據（`gate.sh dispatch --risk high` 之 `--adversarial` 標的）。

RECONCILE-STAMP: composer APPROVED 2026-09-13 sha256:3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb task:20260911-SPLITUNIFY-B9-STAMP-R3
RECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb task:20260911-SPLITUNIFY-B9-STAMP-R3

RECONCILE-STAMP: grok APPROVED 2026-09-13 sha256:3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb task:20260911-SPLITUNIFY-B9-STAMP-R3
