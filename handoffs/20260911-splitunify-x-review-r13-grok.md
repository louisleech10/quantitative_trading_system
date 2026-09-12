# SPLITUNIFY D-001 閉合確認 R13（grok）

brief-kind: closure  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R13  
family: grok  
findings-round: R13  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（C2 第 4 點重寫為 (4.1)～(4.18)；`bash scripts/reconcile_body_hash.sh` → `9e1ef3d1ff91a391f3ba47afb9da436236dd39b10da30abc24de194063fc4aa9`）  
SCOPE: 只讀 closure；禁改碼、禁動 tracked 檔、禁 commit/push、禁跑 `tests/governance` 全套。  
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`（canonical finding 四欄＋末段 VERDICT／BLOCKED-BY／CLOSED；P0/P1 須修法＋可行性證據）。

### §0 前提

fact-verified: R12 六條皆採納並已落 D-001 → `handoffs/reconcile/20260911-splitunify-x-review-r12/synth.md` W1／W1b／W1c／W2／W3／W4  
fact-verified: C2 第 4 點已重寫為 (4.1)～(4.18) 現行態；沿革移出 → D-001:67-90  
fact-verified: 觸及面已含 BASE 座標語彙唯一例外 → D-001:21  
fact-verified: body hash 實跑 → `9e1ef3d1ff91…fc4aa9`  
assumed: 重寫未遺漏已定案義務 → 否證＝必答 2 九輪群集逐條對照  
assumed: 四閘合取下無可改歸屬之竄改 → 否證＝必答 4 構造題

---

## 必答 1–5

### 1. 收斂策略共識決

**同意**主委提議：「一次重寫成現行態 → 本輪只驗保全性與互斥 → 過則進 b8，述詞邊界交 mutation 證明」。

理由：R10～R12 機制面（時間序往返、前置合法性閘、指紋∧遞增合取、權威＝入口重驗）兩家皆未構造成功繞過；R12 六條擋項全是殘句／舊座標語彙，不是新機制洞。繼續在原句旁疊加沿革，只會再生攻擊面。重寫成單一現行態並以編號義務做機械比對，是比再開機制輪**更快且不降嚴謹度**的做法。

預估：本輪若保全性與互斥皆過 → **0 輪**額外機制審查；依 HANDOFF 仍須 **1 輪戳記**（歷輪戳記因規格續改已失效）後進 b8。卡點只剩戳記重簽與 b8 實作／mutation，不卡機制敘述。

### 2. 保全性逐條驗（九輪群集）

盤點：九份 synth 群集表共 **55** 資料列、**43** 個主 ID（U1–U8、V0–V8、R6–R12 之 W*；brief「44」與主 ID 數差 1，以下以表列全集為準，不抽樣）。駁回 3 列（U3 反面、U6 反面、V0）與 sentinel 紀錄列不要求寫入義務正文。

| 群集 | 定案義務（摘要） | 重寫後落點 | 判定 |
|---|---|---|---|
| **consult U1** | 同 symbol train/test hash 一致；跨 symbol 允許 joint hash；禁「必互異」閘 | C1.2:47-50；`M-SU-D1-02` | 保留 |
| **consult U2** | R-5 per-symbol/TF ref manifest；禁 auto-discover | 殘留:191「R-5／D1 不在本延伸」 | 保留（範圍外，未弱化） |
| **consult U3** | SU-RESID-3＝完整逐列 producer 指紋 | C2.1–8；Task 8.2 | 保留 |
| U3 反面 | 只做首尾 | — | 駁回，正確未採 |
| **consult U4/U5** | SU-RESID-2 additive＋下游單鍵；未完成前多 TF fail-closed | 殘留:190 | 保留 |
| **consult U6** | D1 走 R 重開 | 殘留:191；檔頭:11 | 保留 |
| U6 反面 | D1 走 D 延伸 | — | 駁回，正確未採 |
| **consult U7** | b8＝R-1+SU-RESID-3 → b9 → D1 R → b10＝R-5 | 檔頭:11；殘留 | 保留 |
| **consult U8** | per-symbol 測試門檻 | Task 8.3；`M-SU-D1-06` | 保留 |
| **R5 V0** | STAMP-BLOCKED 不審 | — | 駁回，正確未採 |
| **R5 V1** | 三 producer 入 Task 8.2；derive 缺欄 fail-closed；相容 default | Task 8.2 檔案清單:118-121；:125；(4.12) | 保留 |
| **R5 V2** | C-4 簽名覆寫＋wrapper | 觸及面:16／:20；C1.1 | 保留 |
| **R5 V3** | Mapping 缺失 vs symbol 不一致訊息分立 | C1.3:52；ASSERT:104-105 | 保留 |
| **R5 V4/V6** | 四元組 list[list]、int、正規化點名、空=`sha256("[]")` | C2.1–3、.5 | 保留 |
| **R5 V5** | ts／position 取自該 symbol post-trim index | C2.1；(4.1) | 保留 |
| **R5 V7→R6 W4** | 指紋含 symbol，三角仍獨立必查 | C1.2:51 | 保留 |
| **R5 V8** | 跨 symbol 混用負例＋`M-SU-D1-07` | C1.4；ASSERT:107；mutation:168 | 保留（見下方觀察） |
| **R6 W1→R8** | 全框 vs local → 終態 `row_index_local` producer attest | (4.1)–(4.4)、(4.10) | 保留（經 R8 等價樞紐） |
| **R6 W2** | freeze 腳本＋wiring＋oracle vs producer | Task 8.2；C2.7；ASSERT:132 | 保留 |
| **R6 W3** | list[list] 釘死；禁 list[dict]；註解舊欄名 | C2.1；`M-SU-D1-08` | 保留 |
| **R6 W5** | C-4 只覆寫簽名段 | 觸及面:20 | 保留 |
| **R7 W1→R8** | 投影不得用全框列號索引短 index | (4.10)–(4.11)；ASSERT:108；`M-SU-D1-10` | 保留（R8 改 producer 欄，非入口轉換） |
| **R7 W2** | `feature_index_by_symbol`＝短索引；不採全框同空間讀法 | C1.1:45 | 保留 |
| **R8 W1** | `row_index_local`；投影只消費；缺欄不回退；`M-SU-D1-11/12` | (4.3)(4.10)(4.12)；mutation | 保留 |
| **R9 W1→R10** | copy＋唯讀；後改為縱深防禦＋誠實邊界 | (4.15)；ASSERT:137-139；`M-SU-D1-13/14/17` | 保留 |
| **R9 W2→R10** | timedelta 前提 → 改時間序往返，刪「frame≠時間即紅」 | (4.5)(4.6)(4.17) | 保留（R10 取代，非遺漏） |
| **R10 W1** | 權威＝入口指紋重驗；`SU-RESID-5` | (4.13)(4.16)；殘留:194；`M-SU-D1-16` | 保留 |
| **R10 W2/W3** | 時間序往返；禁 helper／frame 序判準 | (4.5)(4.6)；`M-SU-D1-15` | 保留 |
| **R11 W1/W1b** | 刪 helper 正向 ASSERT | 驗證段無 helper 相等正向綠徑；僅 (4.6) 禁止句＋`M-SU-D1-15` | 保留 |
| **R11 W2** | 前置閘：整數／範圍／唯一／嚴格遞增；複用 `assert_positional_rows`；不得關 `require_sorted` | (4.7)；ASSERT:141-142；`M-SU-D1-18/19` | 保留 |
| **R11 W3** | 指紋∧遞增合取入規格 | (4.14)；ASSERT:143；`M-SU-D1-19/20` | 保留 |
| **R12 W1** | 全文座標統一 `row_index_local`；BASE 例外條款 | :21；C1.4；C2.7 oracle；ASSERT:107-108 | 保留（見觀察） |
| **R12 W1b** | 禁 `symbol_positions` 作 attest；改 `sorted_positions` | (4.5)(4.6) | 保留 |
| **R12 W1c** | 刪「先轉換／無損轉換 helper／解釋 row_index」 | (4.10)；Task 8.2:122；C1.4 | 保留 |
| **R12 W2** | 等長前置；禁 zip；空×非空應紅 | (4.8)；ASSERT:144-145；`M-SU-D1-21` | 保留 |
| **R12 W3** | dtype 須 numpy 整數型；不得靠轉型救 | (4.8)；ASSERT:146；`M-SU-D1-22` | 保留 |
| **R12 W4** | 改集合→指紋；改順序→遞增；合取後無法既過又改歸屬 | (4.13) 已加「若改變成員集合」；(4.14) | 保留 |

**結論：已定案義務無消失、無弱化。**  
非擋項觀察（不屬 brief 三類擋項）：①`M-SU-D1-07` 描述仍寫「解 B 之 `row_index`」，同檔 ASSERT:107 已是 `row_index_local`——義務本身在 C1.4／ASSERT，mutation 措辭未同步（建議 b8 順手改字，不開擋項）。②觸及面:21 所引 BASE 行號 `:165`／`:224-225`／`:307` 與現行 `docs/SPLITUNIFY_SPEC.md` 實位 `:458`／`:460`／`:500` 不符；例外**語意**仍成立（凡 BASE 以全框 `row_index` 索引該 symbol index 之句由本延伸取代），屬引用漂移非義務互斥。

### 3. 重寫後內部／跨檔互斥

通讀 D-001（C1、C2(4.1)–(4.18)、Task 8.1–8.3、mutation、殘留）＋ BASE 座標句：

| 檢查 | 結果 |
|---|---|
| (4.5) 時間序往返 vs (4.6) 禁 frame 序 | 同向，無互斥 |
| (4.10) 只消費 local vs (4.11) 封閉清單／docstring | 同向；無「先轉換」殘句 |
| (4.13) 指紋擋**集合**變更 vs (4.14) 遞增擋重排 | 同向（R12 W4 已收斂） |
| (4.15) 縱深防禦 vs「不得宣稱不可變」 | 同向 |
| (4.17) 無「frame≠時間即紅」vs (4.5) | 同向 |
| C1.4「解釋 `row_index_local`」vs BASE `feature_index[row_index]` | 由:21 唯一例外消解，非未標示互斥 |
| hash 不變式 vs `M-SU-D1-02` | 同向 |
| oracle 用 `row_index_local` vs `M-SU-D1-23` | 同向 |

**無內部互斥、無未標示之跨檔互斥。**（BASE 行號漂移見必答 2 觀察，不構成義務互斥。）

### 4. 機制面最後一擊（四閘合取下之竄改構造）

目標：同時通過 **(4.5) 往返 ∧ (4.7) 前置閘 ∧ (4.13) 指紋重驗 ∧ (4.14) 遞增閘**，且改變投影歸屬（`feature_index[row_index_local]` 之成員集合或有序序列）。

構造嘗試與否證：

1. **改集合（增刪／換元）**：指紋 payload 含 `position` 與 `feature_ts_ms`，且先依序號排序再雜湊 → 集合一變指紋必變 → (4.13) 擋。  
2. **同集合重排**：指紋對排列無感 → (4.13)  alone 不過；但 (4.7)/(4.14) 要求嚴格遞增 → 同集合之嚴格遞增排列**只有恆等** → 有序序列不變，歸屬不變。  
3. **負索引／越界／重複**：回捲可使往返偶然相等，但 (4.7) 在往返前擋下。  
4. **只改 `row_index`、不動 local**：投影不讀 `row_index`（4.10）→ 投影歸屬不變（殘留屬 `SU-RESID-5`／全框端）。  
5. **改 local 且同步改指紋字串使重算吻合**：若 `SplitPlan` 凍結，字串欄改綁被擋（4.13）；若經 `pickle`／`deepcopy` 得到可寫陣列只改 local、指紋仍舊 → (4.13) 重算不符而紅。若攻擊者**重建**一個 local 與指紋自洽的新 plan，那是另一份合法 plan，不是「通過四閘的不一致竄改」。  
6. **在 (4.5) 仍成立下改 local**：`sorted_positions` 為固定雙射時，滿足 `sorted_positions[local]==row_index` 的 local 由 `row_index` **唯一決定** → 不能在保持 (4.5) 與同一 `row_index` 下改 local。

**構造不出。** 四閘合取下，能通過者必為（或等價於）誠實寫入態；無法在不一致狀態下既過閘又改投影歸屬。不新開機制面擋項。

### 5. 可否進入實作？

**可以。`VERDICT: proceed`。**  
保全性無遺漏／弱化；無互斥擋項；四閘構造題無可行竄改。建議下一動作＝戳記輪（重簽現行 body hash）→ b8 實作（含 mutation `M-SU-D1-01`～`23`）。必答 2 兩則觀察可於 b8 順手改字，不阻 proceed。

---

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
