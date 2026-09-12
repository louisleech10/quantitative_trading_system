# Reconcile — 20260911-splitunify-x-review-r13

**來源** 20260911-splitunify-x-review-r13-codex.md, 20260911-splitunify-x-review-r13-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 sentinel：保全性無遺漏、無互斥、構造題無解，同意收斂策略**——「本輪逐項核對後無finding；主委提議」 | P3 | CODEX-R13-P3-00 | 採納（紀錄；該家逐行核對九份收斂檔未抽樣，逐條列出每條定案之落點，並機械確認編號義務項共 18 條與 `(4.1)`–`(4.18)` 相符。構造題以**有限枚舉實跑**作答：嚴格遞增序列 16 條、同集合非恆等且遞增者 0 條、被遞增閘擋掉之非恆等排列 49 條。裁決 proceed，且明言 D-001 機制審查**再需 0 輪**） |
| **W2 sentinel：九輪 43 主 ID 逐條保全，四閘合取下構造不出**——「本輪逐項核對後無finding；九輪群集」 | P3 | GROK-R13-P3-00 | 採納（紀錄；該家以 55 列／43 主 ID 之對照表逐條給出落點與判定，結論「已定案義務無消失、無弱化」。其構造題第 6 點給出關鍵論證：在往返條件下該標的之排序位置為固定雙射，故序號由列號**唯一決定**，無法在保持往返與同一列號下改動序號。裁決 proceed） |
| **W3 引用漂移二則（非擋項，主委本輪一併修掉）** | P3 | GROK-R13-P3-00 | 採納（①變異表某條之描述仍寫「解 B 之 `row_index`」而同檔斷言已改用 `row_index_local`，已同步 ②觸及面之 BASE 例外條款原列三個行號，主委查證後發現其一不存在、且實際落點多達十餘處 ⇒ **不換新行號**，改寫為可 grep 之形狀判準「凡 BASE 中形如 `feature_index[row_index]` 之索引句一律適用」，避免製造下一個過期引用） |

**Verdict**: 可合併——兩家皆 `proceed` 且零實質 finding，為本票規格階段**首次雙方一致放行**。保全性、互斥、四閘構造三項皆無擋項；兩則引用漂移已於本輪修畢。下一步＝三家戳記輪（歷輪戳記因規格續改皆已失效，須對現行 body hash 重簽），戳記過後進 b8 實作。

## 本輪程序記錄

- 本輪為**保全性驗證輪**，非開放式攻擊輪：主委於 R12 後判定「機制已收斂、未收斂的是文件內部一致性」，遂把 C2 第 4 點整節重寫為單一現行態、沿革移出至各輪收斂檔、義務逐條編號，並在派工單把「重寫有沒有漏掉已定案義務」設為唯一可終結之問法，同時將收斂策略本身列為必答交兩家表決。
- **兩家對收斂策略均表同意**，並各自給出剩餘輪數估計：一家為「再需 0 輪機制審查，直接進 b8」，另一家為「0 輪機制審查＋1 輪戳記」。兩者一致。
- 主委對兩家之保全性結論做交叉核對：兩家各自獨立列出落點且互相吻合；一家另以機械計數確認編號義務項為 18，與重寫後之 `(4.1)`–`(4.18)` 相符。
- 🔴 **主委自查補正（W3 第二則）**：該家指出之三個 BASE 行號，主委實跑 grep 後發現其一根本不存在，另兩個正確，且真正符合該形狀之落點共十餘處。⇒ 結論不是「換成正確行號」，而是**不寫行號**——行號會再漂，寫死等於預約下一個過期引用。此與本輪整體教訓同源。
- 一家回報既有收斂檔以戳記檢查器檢查得 rc=1（缺 `## 戳記` 區段），該家未升為 finding。主委確認：本 repo 之戳記慣例為獨立行格式，該工具落差屬既知，不影響本輪裁決。
- 本輪兩家所附戳記對應 D-001 當時之 body hash；主委於本輪修畢兩則引用漂移後 hash 已變動，故**戳記輪須對修訂後之現行 hash 重簽**。

## 戳記

> 三家 RECONCILE-STAMP；body sha256 ＝「## 戳記」前全部內容（`bash scripts/reconcile_body_hash.sh`）。
> 歷輪戳記因規格續改皆已失效，本輪為對現行態之重簽。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R13-P3-00

**斷言**: 本輪逐項核對後無 finding；主委提議的「一次重寫現行態、只驗保全性與互斥、再進 b8 並由 mutation 證明述詞邊界」可採納，無須再開 D-001 機制審查輪。

**碼證**: 已完整讀取 `HANDOFF.md`、`CLAUDE.md`、R13 brief、D-001、BASE、TODO、範本與九份指定 synth；現行 D-001 `numbered_current_items=18`。D-001:20-21 保全 BASE C-4 非簽名義務與座標例外；:43-53 保全 Mapping、hash、三角相等與 per-symbol 空間；:73-94 覆蓋 (4.1)-(4.18)、邊界、指紋、oracle、首尾 guard；:96-148 覆蓋 Task 8.1/8.2；:150-156 覆蓋逐 symbol 門檻；:162-184 覆蓋 mutation。

**來源摘要**: `docs/SPLITUNIFY_SPEC.D-001.md#5d4fe1e2afa5`；`docs/SPLITUNIFY_SPEC.md#3e39458b00e4`；`docs/SPLITUNIFY_TODO.md#e44da6448b01`；`handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md#590f66e0d93d`；`handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md#fcb22c3019b`；`handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md#5b9922ac6fce`；`handoffs/reconcile/20260911-splitunify-x-review-r7/synth.md#6dea00640e8e`；`handoffs/reconcile/20260911-splitunify-x-review-r8/synth.md#54dd8fdff576`；`handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md#249fe2729b18`；`handoffs/reconcile/20260911-splitunify-x-review-r10/synth.md#c8f4e5dd23ef`；`handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md#86e13c32b9fd`；`handoffs/reconcile/20260911-splitunify-x-review-r12/synth.md#11c2029a3358`

1. 共識決：同意；再需 0 輪 D-001 closure review，直接進 b8。剩餘工作是 implementation gate 本身：三 producer 寫入/attest、投影只讀 local、golden refreeze、獨立 oracle 與 mutation 測試，不是本輪新增阻塞。
2. 群集逐條對照（九份表逐行核對，未抽樣）：consult-r2 的 U1（CODEX-R1-P1-01／COMPOSER-R2-P1-01／GROK-R1-P2-01）由 :47-53 保全；U2（CODEX-R1-P1-02／COMPOSER-R2-P1-02／GROK-R1-P2-03）、U4（CODEX-R1-P1-04／COMPOSER-R2-P2-03）、U5（CODEX-R1-P1-08）、U6（CODEX-R1-P1-05／GROK-R1-P1-01／COMPOSER-R2-P2-01）、U7（CODEX-R1-P1-06／GROK-R1-P2-02／COMPOSER-R2-P2-02）明確列為 R-5/SU-RESID-2/D1 範圍外並由 BASE C-0、C-4、§N 保留；U3（CODEX-R1-P1-03／COMPOSER-R2-P1-03）由 :55-94 保全；U8（CODEX-R1-P1-07）由 :96-112、:150-156 保全。
2. R5 synth 的 V0（CODEX-R5-P0-01）是已駁回程序主張，非現行義務；V1（COMPOSER-R5-P1-01／GROK-R5-P1-01）由 Task 8.2 :117-125、:131-148 保全；V2（COMPOSER-R5-P1-02）由 :16、:20、:29-45 保全；V3（GROK-R5-P1-02）由 :43、:52、Task 8.1 :104-105 保全；V4（COMPOSER-R5-P2-01）由 :59-63、Task 8.2 :126 保全；V5（COMPOSER-R5-P2-02）由 :73-78 保全；V6（GROK-R5-P2-01）由 :59-65、:91-94 保全；V7（GROK-R5-P2-02）由 :51-52 保全；V8（COMPOSER-R5-P2-03／GROK-R5-P2-03）由 :53、:107、M-SU-D1-07 保全。
2. R6 synth 的 W1（CODEX-R6-P1-01）由 (4.1)-(4.9) 保全；W2（CODEX-R6-P1-02）由 Task 8.2 檔案列、:126-149 與 oracle 條款保全；W3（GROK-R6-P1-01）由 :59-63 保全；W4（GROK-R6-P2-01）由 :51 保全；W5（GROK-R6-P2-02）由 :16、:20-21 保全；W6（COMPOSER-R6-P3-00）為 sentinel 記錄，無義務待移入。
2. R7 synth 的 W1／W2（CODEX-R7-P1-01，同一來源 ID 的兩個對照列）由 :45、(4.1)-(4.6)、:90、Task 8.1 :107-109 保全；W3（GROK-R7-P3-00）為 sentinel。R8 synth 的 W1（CODEX-R8-P1-01）已由 producer `row_index_local`、投影端禁止全框輸入、缺欄 fail-closed（:45、(4.3)-(4.5)、(4.10)-(4.12)）承接，並非遺漏。
2. R9 synth 的 W1（CODEX-R9-P1-01）由 (4.13)-(4.16)、Task 8.2 :137、:148 與 M-SU-D1-13/14/17 保全；W2（GROK-R9-P3-00）是已被 R10 判準取代的 sentinel，時間序往返與亂序放行現載於 (4.5)-(4.7)、(4.17)。R10 synth 的 W1（CODEX-R10-P1-01）由 (4.13)-(4.15) 保全；W2/W3（CODEX-R10-P1-02，同一來源 ID 的兩個對照列）由 (4.5)-(4.8)、(4.17)、M-SU-D1-15 保全；W4（GROK-R10-P3-00）為 sentinel。
2. R11 synth 的 W1（CODEX-R11-P1-01）與 W1b（GROK-R11-P1-01）由 (4.5)-(4.7)、Task 8.2 :140、:147 保全，沒有 helper/frame-order 正向 ASSERT；W2/W3（CODEX-R11-P2-02，同一來源 ID 的兩個對照列）由 (4.7)、(4.14)、M-SU-D1-18/19/20 保全。R12 synth 的 W1（CODEX-R12-P1-01）由 :21、:73-94 與 BASE 座標例外保全；W1b（GROK-R12-P1-01）由 :77-79、:140、:147 保全；W1c（GROK-R12-P1-02）由 :82-84、Task 8.2 :122 保全；W2（GROK-R12-P2-03）由 :80、:144-145、M-SU-D1-21 保全；W3（CODEX-R12-P2-02）由 :79-80、:146、M-SU-D1-22 保全；W4（GROK-R12-P2-04）由 :85-87、:143、M-SU-D1-16/19/20 保全。以上沒有消失或弱化的已定案義務。
3. 互斥核對：同檔無互斥；BASE C-4 舊簽名與新 Mapping 已由 :16、:20 明確限定覆寫範圍，BASE 其餘 keyed input／禁 positional zip／兩段式判定／producer 義務仍有效；BASE 舊 `feature_index[row_index]` 座標由 :21 的唯一例外改讀 `row_index_local`。 (4.1)-(4.18) 彼此一致，尤其 (4.5) 時間序往返、(4.7) 前置閘、(4.13) 入口重驗、(4.14) 指紋與遞增合取沒有互斥。
4. 構造題：構造不出。固定 universe 下，若改集合，(4.13) 的重算 fingerprint 改變而 fail-closed；若只重排同集合，指紋雖相同但 (4.7)/(4.14) 的嚴格遞增 fail-closed；同集合且嚴格遞增的序列只有恆等。若只改 `row_index`，(4.5) 往返不再相等，且投影端不消費它；若改 index/symbol/hash，則指紋或三角相等失配。有限枚舉實跑 `valid_strictly_increasing_sequences=16`、`same_set_nonidentical_strict_sequences=0`、`nonidentity_permutations_rejected_by_strict_order=49`。
5. 可進實作：`VERDICT: proceed`；本輪沒有 (a) 遺漏、(b) 互斥或 (c) 四閘可行竄改。
ASSUMPTIONS_VERIFIED: 九份指定 synth、D-001、BASE、TODO、範本與兩份根規範已讀；18 個 (4.1)-(4.18) 項目逐一存在；BASE 座標引用共 10 處皆落在 :21 的全框→local 唯一例外範圍；D-001 body hash 實跑為 `9e1ef3d1ff91a391f3ba47afb9da436236dd39b10da30abc24de194063fc4aa9`。
TESTS_RUN: `bash scripts/agent_preflight.sh` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-001.md` → rc=0；`bash scripts/template_check.sh dext docs/SPLITUNIFY_SPEC.D-001.md` → rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → 上述 hash；`rg -c '^   \*\*\(4\.[0-9]+\)' ...` → 18；四閘有限枚舉 probe → 上述三項輸出；未跑 `tests/governance` 全套，未改碼。
FAILURES_SEEN: `bash scripts/reconcile_stamps_check.sh ...r12/synth.md` → rc=1，原因是既有 synth 缺 `## 戳記` 區段；該檔仍有 codex/grok 兩條獨立 `RECONCILE-STAMP ... APPROVED`，本輪依 brief 的獨立行格式處理，未將此工具格式差異升為 finding。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-x-review-r13-codex.md`，未改 tracked code/data、SPEC、TODO、測試或 root `HANDOFF.md`。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪唯讀 closure review，未改產品數值、schema、golden 或輸出檔大小。
OUTPUT_PATH: `handoffs/20260911-splitunify-x-review-r13-codex.md`
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:9e1ef3d1ff91a391f3ba47afb9da436236dd39b10da30abc24de194063fc4aa9 task:20260911-SPLITUNIFY-X-REVIEW-R13
VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
## GROK-R13-P3-00

**斷言**: 本輪逐項核對後無 finding；九輪群集已定案義務均在 D-001 現行態保留，(4.1)～(4.18) 與 C1／Task／mutation 無互斥，四閘合取下構造不出可改投影歸屬之竄改。

**碼證**: 對照九份 synth 群集表（55 列／43 主 ID）→ 必答 2 表；通讀 `docs/SPLITUNIFY_SPEC.D-001.md` C1／C2(4.1)–(4.18)／Task 8.1–8.3／mutation／殘留 與 BASE `feature_index[row_index]` 三處（`:458`／`:460`／`:500`）＋例外條款 `:21`；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `9e1ef3d1ff91a391f3ba47afb9da436236dd39b10da30abc24de194063fc4aa9`；四閘構造推理見必答 4（集合→指紋、重排→僅恆等過遞增、負索引→前置閘、雙改指紋→凍結／重驗）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#5d4fe1e2afa5；handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md#590f66e0d93d；handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md#fcb22c3019b1；handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md#5b9922ac6fce；handoffs/reconcile/20260911-splitunify-x-review-r7/synth.md#6dea00640e8e；handoffs/reconcile/20260911-splitunify-x-review-r8/synth.md#54dd8fdff576；handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md#249fe2729b18；handoffs/reconcile/20260911-splitunify-x-review-r10/synth.md#c8f4e5dd23ef；handoffs/reconcile/20260911-splitunify-x-review-r11/synth.md#86e13c32b9fd；handoffs/reconcile/20260911-splitunify-x-review-r12/synth.md#11c2029a3358；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R13-BRIEF.md#c74fc21f1f29

本輪為保全性閉合確認（非開放式新攻擊面）。R12 本家四條（P1-01／P1-02／P2-03／P2-04）已落入 (4.5)–(4.8)、(4.10)、(4.13)–(4.14) 與對應 ASSERT／mutation，列於 CLOSED。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:9e1ef3d1ff91a391f3ba47afb9da436236dd39b10da30abc24de194063fc4aa9 task:20260911-SPLITUNIFY-X-REVIEW-R13

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R12-P1-01,GROK-R12-P1-02,GROK-R12-P2-03,GROK-R12-P2-04
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief 五題；九輪 synth 群集表全列對照；D-001 重寫後 (4.1)–(4.18) 與 C1／Task／mutation／殘留；BASE 座標句＋例外條款；body hash 實跑；四閘構造否證推理。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `9e1ef3d1ff91…fc4aa9` rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r13-grok.md --family grok`（交件後實跑）。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r13-grok.md
TMP_CLEANUP: 清 `/tmp` 本輪 workdir；保留 `claude-501`。
