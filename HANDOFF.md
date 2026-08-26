# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口）

含：§0 狀態與各批交付物＋R3 出口清單、§1 開工前稽核（含期望值）、§2B **Phase 4 之偵察與定案**
（**不必重查**）、§3 派工管線（逐字指令＋三件套 RECHECK ＋常設條款 5）、§4 完成判準與 mutation 寫法
（**九個假綠實例**）、§5 未辦、§6 地雷與治理現況、§7 具名殘留全文、§8 檔案地圖。
**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（`factkey_write_guard.sh` 會擋），亦避開「某某已完成」句型。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）、D-002（`51f1a65e`）、**D-004**（Phase 4 之契約修補，A-020／A-021／A-022）
皆三家 APPROVED；D-003（`09884811`）尚未過戳記（收 epic 前補）。
42 個 Task 之計數：**28 ✅／0 🔧／14 ⬜**（逐 Task 狀態一律看看板）。

Task 5.0／5.1／5.2／5.3（訊息與表頭）之**五輪** code review findings **5 → 1 → 4 → 2 → 0**，
三家一致收；commit `ebd77b87`；mutation 19 條 `closure: CLOSED`（隔離環境重跑）。
收斂檔在 `handoffs/reconcile/20260827-gap3ux-b8-review-r{1..5}/synth.md`（兩道機檢皆 rc=0）。
🔴 收斂**非單調**：第三輪跳回 4 條，是因為主委首次請三家**獨立重掃全部 21 條 definition**
＝新開的攻擊面，不是修法退步。

🔴 **該批九條自傷同一種病**：詞彙表之 definition 在**重述公式**，而主委是讀碼推論寫的、
沒有一條實跑驗證過（`n_eff` 實為等權恆等於 n／`prevalence_full` 分母是 n_labeled／
`horizon` 自進場根起算／`macro_mean` 是保留集×uniqueness 加權／`n_test` 為三者交集且改了三次）。
修法＝每條補**把定義釘在真實算式上**的測試，算式一改先紅。
**三家修正主委判斷**：病根只講對一半，另一半是**審查方法本身沒跑不對稱反例探針**。

🔴 **一次工作區事故**：`import_contract.py` 之未 commit 實作整段回到 HEAD（composer 複驗時發現）。
**機制未判定**——主委初判「執行端違約 `git checkout`」屬過度宣稱、**已撤回**；
grok 查出該批 runner 缺 `IsolatedWorktree`（B7 範本已退化而交接沒記，缺陷延續兩批）
＝主委自身缺陷，已補隔離並在隔離環境重跑全部 mutation。
**新增兩條鐵律**（見唯一入口 §3 第 9、10 條）：**派 review 前先 commit**；
**runner 須同時具備隔離＋備份閘＋開跑前刪 receipt**。

前六批之 code review 輪數與 findings 收斂：第三批 **6 → 3 → 0**、第四批 **7 → 4 → 4 → 1 → 1 → 0**、
第五批 **6 → 3 → 1 → 0**、第六批 **5 → 2 → 2 → 1 → 兩家零 → 0**，皆三家一致收；
收斂檔在 `handoffs/reconcile/2026082{5,6}-gap3ux-b{3,4,5,6}-review-r*/synth.md`（兩道機檢皆 rc=0）。

Task 4.1／4.1b／4.1c／4.2／4.3（匯出端報酬欄與揭露）之三輪 code review findings **7 → 3 → 0**，
三家一致可收。收斂檔在 `handoffs/reconcile/20260826-gap3ux-b7-review-r{1,2,3}/synth.md`（兩道機檢皆 rc=0）。

`D-004` 之戳記歷**三輪**，R1／R2 皆 composer／grok APPROVED 而 **codex REJECTED 且兩次都正確**：
R1＝`RULING-3(c)` 實為 2 vs 1，主委誤採少數版並標「三家一致」（形態＝**未逐家交叉核對即宣稱一致**）；
R2＝A-020 漏記**三家一致**之三項限制（`future_*` 不進 `ic_feed`／保留 `receipt_schema.batch` 同名鍵／
驗批內一致性），而該輪 composer 與 grok 標「一致」時**也沒回讀自己的 consult 原文**。
R3 三家全數 APPROVED（sha `12a8fc74…`／`befd04f7…`）。

🔴 **本輪三次「宣稱大於實作」（累計第五、六、七次），全部由委員實跑抓出**：
① D-004 R1 之誤採少數版；② D-004 R2 之漏記三家一致限制；
③ **review R1 三家同時抓到**——主委在 brief 宣稱「深度拿不到就擋」而實作只擋了「有條件」那一半。
另有兩條形態不同但同樣重要：
④ **review R2 之群集 E 是 R1 修法自身開的破口**，且**正是主委自己寫進 brief 請委員攻、卻沒先自己打過的嫌疑點**；
⑤ 收尾時 `verify_pretooluse.sh` 擋下一次**指向 `closure: OPEN` receipt 卻宣稱全通過**的寫入
（根因＝委員複驗時覆寫了 repo 內 receipt，見交接 §6.4 新增條）。

三家另裁定：TODO 之 Task 4.2 邊界②與 Phase 4 Gate 之「須重凍」句為隨 `D-004 A-022` 失效之
**過期副本**（層級規則＝語意權威在 SPEC、TODO 不得作為第二份斷言副本），**不另開 D-005**。

🔴 **G-2 golden ＝不會改變、不重凍**（`D-004 A-022`）。交接 §2B.1 與 §8 檔案地圖兩處原宣稱皆已更正
（後者由 R1 之 `GROK-R1-P3-02` 抓出——主委開工稽核時就看到卻說「稍後一併修」）。

**下一步＝Phase 5（訊息與表頭），依 §B 拓撲前置為 Task 5.0。**
其後才是使用者 **UAT B 段 13 項簽字** ⇒ epic 收案（未簽字不收案）。

看板 `白話說明/GAP-3施工看板.md`；歷史 `白話說明/GAP-3施工進度.md`。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b7-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| mutation | 32／14／13／15／19／23／**22** 條（七批），皆 `closure: CLOSED` |
| 本批驗收 | `pytest -k gap3_attached_columns_contract` 16（下限 7）；vitest `eventExportHorizonColumns` 6（下限 6）／`eventExportDisclosureLegacy` 5（下限 2）／`eventExportNoIcDecay` 4／`exportMissingColumnDialog` 5（下限 2）／`eventExportGuardRuntime` 7／`eventTablesHorizonWiring` 4／`-k horizon_curve` 4（下限 3） |
| 全套 | `pytest tests/momentum/event_samples` 299 passed；gap3 api 選測 179 passed；vitest 54 檔 310 條；build rc=0；**`npx tsc --noEmit` B7 相關 0 錯**；`gap3_freeze_golden --check` rc=0（sha 未變） |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
🔴 `--record` 出現 `紅=[]` 一律當作假綠信號，先查根因（交接 §4.2 有九個實例；本批又抓到一條）。
🔴 **`npm run build` 不涵蓋測試檔** ⇒ 前端收案前須另跑 `npx --prefix frontend tsc --noEmit -p frontend/tsconfig.json`
（本批由 `CODEX-R2-P2-03` 抓出；主委全掃後另找到 3 處，含已刪除選項 `horizonBars` 之殘留）。
🔴 **收尾前必查 receipt 之 `closure` 欄**——委員複驗會覆寫它（見交接 §6.4）。

## 具名殘留

**全文一律見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.2／§7.3**（本檔不複列，避免副本漂移）。
代號：`R-GOV7-1`／`R-GOV7-2`／`R-B1-1`／`R-A005-1`（Phase 4 不觸發，仍待 producer 段）／
~~`R-B2-1`~~／`R-B2-2`／`R-B4-1`／~~`R-B3-1`~~／~~`R-B3-2`~~／`R-B3-3`／~~`D-002 A-004`~~／
`D-001-D-003 provenance`／純 JS 手刻 sha256 ＋ SPEC 末節 `F-1..F-4` ＋ TODO R3 reconcile 四條。
**本批新增兩條**：`label_value` 仍走 `_is_num` 故仍收 NaN（**既有**行為、非本批弱化；
三值理由 `blocked-by` Task 7.0b 之 label producer 重寫）；
前端既有型別錯 6 條（`FactorReturnChart.test.tsx` 4／`useFeatureFactory.batchDate.test.ts` 2，
三值理由 `user-ruling`＝面向未來不溯及既往）。

## 四條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  唯一已授權例外＝mutation 併發隔離（已完成，用法見交接 §4.1）。
- **不要用原始碼形狀證明執行期性質**——同一病已五度出現（§6.2）；
  「比對範圍過寬／失真」已犯**七次**（§6.1）。一律字面錨點、禁行號；
  檢查寫完要用**已知會紅的輸入**試一次。
- 🔴 **列出嫌疑點 ≠ 驗過嫌疑點**（本批新增）：寫進 review brief 請委員攻的攻擊面，
  自己也要先打一遍——本批之群集 E 就是主委列了卻沒打、由委員構造出來的。
