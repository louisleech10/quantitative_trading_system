# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 TODO **R3 已改完**，r9 戳記輪（＝Frozen 前最後審查）跑完即 **Frozen → 開工 B1**

**現行文件三件套**：
- TODO **R3**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（`template_check todo` PASS；sha 前 12 `7ef0ec44e111`）
- **SPEC 延伸檔**：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`（**A1-1..A1-18**；母 SPEC 定版故不就地改，**衝突以延伸檔為準**；sha `31c3fddb05f0`）
- 收斂兩份：`…/20260817-gap1-x-review-r8/synth.md`（J1–J6，22 條，**戳記 PASS**）
  ＋`…/20260817-gap1-x-review-r9/synth.md`（J7–J9，6 條，body sha `67a5a742319c`，**戳記進行中**）

**接手順序**：
1. **查 r9 戳記**：`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-x-review-r9/synth.md`。
   - **PASS** ⇒ 銷該輪債（`debt_clear.sh --abandon --round-id <r10 round> --kind no-findings-expected`）
     → TODO 標頭改 **Frozen** → commit（訊息骨架見 `.claude/tmp/gap1_r2_commit.txt`，需補 R3 段）→ 開工 B1。
   - **任一家 BLOCKED** ⇒ 讀其產出檔理由，修 → 重派同輪戳記（**不**跳過）。
2. 開工順序：B1(1.1–1.4) → B2(2.1–2.3) → B3(3.1–3.4) → **B4(4.1→4.2→4.3→2.4)**；
   wiring 閘 rc=0 **只**在 B4 收尾要求（2.4 已移入 B4 末，且 B4 ⊃ B3）。每批完成交三家 code review。
3. **R9 三條修補之意圖**（實作時勿誤改回去）：① reporter 只捕 `(OSError, JSONDecodeError, ContractViolation)`，
   `InvalidValidationArgument` 上拋 5xx；`None`＝未提供、`<=0`＝呼叫方 bug（**二分，不得正規化**）
   ② wiring W1／W4 只認**函式頂層無條件**字面鍵（死分支不算），故 `report.py` 必須頂層字面組裝
   ③ 回退順序 B4→B3。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l`（**尚未 commit 本輪；push 需使用者明示**） |
| 戳記狀態 | 已 PASS：consult-r1／review-r1／r2／r4／r5／r6／**r7／r8**。**進行中**：review-r9（task `20260817-GAP1-X-STAMP-R10`） |
| 未 commit 變更 | TODO R3、延伸檔（新檔，A1-1..18）、registry、ROADMAP（＋PA-CUMSUM 小票）、白話說明、r8／r9 收斂＋六份委員 review 檔＋主委自產版＋4 份 receipt |
| 收斂軌跡（TODO 側） | R8 **22** → R9 **5 實質**（＋1 sentinel）；SPEC 側前七輪 23→7→11→7→4→1 |
| 待補完 | `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-1 待補完登記」G1-R1..R7＋**R9**（R8 已收回為 ROADMAP 小票） |
| 既有紅（勿誤認新紅） | 產品套件 14 條（A/B 隔離證明）＋治理段5 4 條（f50f9d0f 舊契約遺留） |

## ⚠ 本輪新增之操作紀律（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 **`committee_run --session` 命名規約**：`<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，`kind ∈ {impl,review,stamp,consult,fix}`；
  用 `x-todoadv-r1` 會 fail-closed 不派工（本輪踩到一次）。輪次號**全 epic 連號**（GAP-1 已用到 R9）。
- 🔴 **延伸檔命名避開 `SPEC`**：`doc_format_precheck.sh` 以檔名含 `SPEC` 判為 spec 型並要求 §RISK/§A/…；
  amendment 檔名用 `<EPIC>_AMENDMENTS.md`（同 `GOVB0_FRICTION_AMENDMENTS.md` 先例）。
- 🔴 **`completeness_check` 正式入口**：`--synth <path> --lock <path>`（裸 argv 會 fail-closed）。
- 🔴 **主委自產版走非鎖來源**：lock 只放三家；自產版之 ID 用 `CLAUDE-Rn-…` 但**不下 `## ` heading**於 synth，
  否則會被當來源 ID 檢查。
- 🔴 **§G/§V 之數值 golden 必須實跑才算定版**：本輪三條假 oracle（alpha band／RNG 未指定／不可證偽 mutation）
  在 SPEC 七輪 adversarial 全數漏掉，是主委實跑探針才現形 ⇒ 凡 band／atol／「改壞會轉紅」皆須附 receipt。
