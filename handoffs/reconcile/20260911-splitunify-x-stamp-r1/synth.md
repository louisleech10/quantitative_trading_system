# Reconcile — 20260911-splitunify-x-stamp-r1

**來源** 20260911-splitunify-x-stamp-r1-codex.md　|　**roster** codex

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——codex 之 REJECTED 成立且已修；synth 修正後須三家重新蓋章
（codex 走 `20260911-SPLITUNIFY-X-STAMP-R4`，composer／grok 走 R2／R3）。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **S1 consult synth 處置段未忠實收斂 codex 立場** | P1 | CODEX-R1-P1-07 | **採納，已修**。原文把「時間 purge／embargo 對事件 purge 之 containment」寫成「三家未反駁」並以「事件側較弱」為 D1 之共同理由；`CODEX-R1-P1-02` 明確反駁——containment **未被證明**，理由應改為「所有 row／event projection 共用同一 canonical boundary」。已改寫 D1 之理由段與「我方前提之驗證結果」段，並一併採納 codex 之 §G 要求（未證明 containment 前不得刪除任一既有 guard；§G 須同時 golden 逐 row test fingerprint／逐 event assignments 與 purged IDs／answer-window 完整性／leakage negative case）。 |

### 🔴 主委回頭逐條核對後**自行發現的另外兩處收斂失誤**（codex 未提，但同源）

codex 的 REJECTED 讓我回頭把 6 條 codex consult findings 逐條對 D1–D5 核，結果比它指出的更嚴重：

- `CODEX-R1-P1-04`（**接線缺口**：事件 pipeline 沒有 IC 的 feature row universe，
  不能自行重算一份「看似相同」的邊界）被**誤併進 D4**（GAP-3 延伸檔）而實質丟失。
  這正是 `docs/SPLITUNIFY_SPEC.md` v1 寫出一個**沒有落點**的投影的直接原因。
  ⇒ 已補為 **D6**，並採 codex 之落地建議：單一 boundary builder 住
  `momentum/core/split_preview.py`、orchestrator 與 pipeline 共同呼叫、
  無 canonical feature universe 之匯入流程只能明示 `event-study-only` 不得宣稱 OOS。
- `CODEX-R1-P1-03`（`EventSplitPlan` 語意欄位須由 canonical boundary 重新導出）與
  `CODEX-R1-P1-05`（統一**會改變數值**）**完全未被任何群集引用**。
  ⇒ 已補為 **D7**／**D8**。
- `CODEX-R1-P2-06`（GAP-3 frozen 之路徑字面不一致）原被誤列在 D5（票大小），已移正至 D4。

主委在 R1 自產審查以 `CLAUDE-R1-P0-01` 獨立重新發現了 D6 同一問題，並以探針
`handoffs/20260911-probe-splitunify-universe-gap.py`（receipt
`handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`，rc=1）證明
「兩端各自用同一公式算邊界」不成立——特徵裁切後邊界位移最大 67 小時。
該實測結論與 codex D6 決議③（無共同 universe 即不得宣稱 OOS）一致。

**制度層面的教訓（寫進 SCAR_LEDGER 候選）**：戳記閘攔下的不是「委員寫錯」，
而是**主委收斂時掉項**。本輪一條 REJECTED 連帶挖出三處掉項，其中一處已經污染到 SPEC v1。
⇒ 收斂完成後應機械核對「每條來源 finding 是否被某個決議項實質引用」，
而不只是檢查 ID 字串出現過（現行 `reconcile_cluster_attribution_check.sh` 對本檔回 rc=0，
卻沒抓到 P1-03／P1-05 只出現在附錄）。已列為具名殘留 `SU-RESID-1`。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-07

**斷言**: synth 的 Claude 處置段未忠實收斂 CODEX-R1-P1-02：它把尚未證明的時間 purge/embargo 對事件 purge 的 containment 寫成「三家未反駁」，並以事件側「較弱」作共同理由；CODEX 原立場明確要求不得以「時間 purge 比事件 purge 強」作唯一理由。附錄雖逐字保留 finding，不能抵銷處置段的相反表述。

**碼證**: synth.md:15-19、50-51 寫「三家一致」及「三家未反駁」；codex consult:27-33 明載 containment 尚未證明、理由應改為共用 canonical boundary。`awk` finding-section digest：synth 與目前 codex consult 均為 `1ad6ecc678815fb3e7f08bed9258812b82637dd24dc1b91035058c188f58e3c9`。

**來源摘要**: handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md#ca475ed187f0；handoffs/20260910-splitunify-x-consult-r1-codex.md#78908c8411f1

判定：初次核對時 REJECTED；需待 stamp-target 停止外部改寫後重審。初次附錄 finding 本體未發現被刪改。

BODY_HASH: ca475ed187f0e2d44c770e093030c5ef78fa16516385edd9095d9523ff23ca70
APPENDED_LINE: RECONCILE-STAMP: codex REJECTED 2026-09-10 sha256:ca475ed187f0e2d44c770e093030c5ef78fa16516385edd9095d9523ff23ca70 task:20260911-SPLITUNIFY-X-STAMP-R1 — D1 與我方 P1-02 對 containment 未證明的立場不一致
RESULT: codex 初次不核可；其後 stamp-target 在本 task 仍進行外部改寫，原戳記 hash 已失效，未追加新戳記。

ASSUMPTIONS_VERIFIED: 初次 append 時 synth 本體 hash；目前 codex findings 與當時 synth CODEX appendix digest 相同；目前 consult 與 frozen source snapshot 的 findings section 相同；初次 Claude 處置段與 CODEX-R1-P1-02 的語意衝突由 `nl -ba ... | sed -n '8,58p'` 與 codex `25,34p` 行號對照確認。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` → ca475ed187f0e2d44c770e093030c5ef78fa16516385edd9095d9523ff23ca70；`awk` finding-section digest comparison → identical；pre-append 與 post-append `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` → rc=1（先缺戳記、後因 codex REJECTED）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-stamp-r1-codex.md --family codex` → PreToolUse gate 在執行前阻擋，無 script rc。禁止的 governance 全套測試未執行。
FAILURES_SEEN: 初次 digest 指令誤用缺少 `reconcile/` 的路徑，無檔案變更；修正路徑後 digest comparison 通過。其後外部程序改寫 stamp-target body，觀測 hash 由 `ca475ed...` 變為 `ebd8eb...` 再變為 `9eebe0...`；原 codex stamp 不再匹配。
SCOPE_CHANGES: Codex 僅 append 初次 stamp-target 一行與新增本交件檔；未改 production code、tests、docs/SPLITUNIFY_*.md、根 HANDOFF.md 或 data_cache/。後續 target body 變更非 Codex 所作，已停止追加。
NUMERIC_OR_SCHEMA_IMPACT: 無；本輪只核對文字忠實性與 stamp metadata，未改任何產品輸出。
HANDOFF_OUTPUT: handoffs/20260911-splitunify-x-stamp-r1-codex.md
TEMP_CLEANUP: `/tmp` 是 `/private/tmp`；未找到名為 `workdir` 的目錄，未刪除其他暫存資料；`/private/tmp/claude-501` 已確認保留。
FINAL_OBSERVED_BODY_HASH: 9eebe0637707d9747f24a90a0c07857154f5d54d08eaa709701f130e676003c1；初次戳記宣告的 `ca475ed187f0e2d44c770e093030c5ef78fa16516385edd9095d9523ff23ca70` 已不匹配。
STATUS: BLOCKED — stamp-target 在序列化 task 尚未結束時被外部改寫；無法安全完成單一有效戳記，需 target 穩定後由主委重新派工/重審。
