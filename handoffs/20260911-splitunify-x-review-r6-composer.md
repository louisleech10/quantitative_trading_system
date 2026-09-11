# SPLITUNIFY D-001 延伸 — COMPOSER R6

task-id: 20260911-SPLITUNIFY-X-REVIEW-R6  
family: composer  
brief: `handoffs/20260912-SPLITUNIFY-D001-REVIEW-R2-BRIEF.md`  
findings-round: R6  
review-target: `docs/SPLITUNIFY_SPEC.D-001.md`（R5 修訂版；sha256[:12]=`9bb033a39a73`）  
BASE: `docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| R5 十條實質 finding 已入 D-001 | brief fact-verified | **成立** — 對讀 R5 synth 群集表與 D-001 逐段；本輪五條 composer finding 全可定位修法 |
| 生產碼無 `row_time_fingerprint` | brief fact-verified | **成立** — `rg row_time_fingerprint momentum/ --glob '*.py'` → 0 命中 |
| 八 anchor 逐字存在（含 C-4 新列覆寫） | brief assumed | **成立** — `git show b095cc7:docs/SPLITUNIFY_SPEC.md` 八條 `rg -F` 各 1 hit；D-001 觸及面 `:16-17` 已把 C-4 移入「覆寫」 |
| `debt_ledger.sh --has-open` rc=0 | brief 前提 | **不成立（本輪 OPEN）** — 實跑 `rc=1`（與 brief 預期一致，非阻塞審查） |

---

## 必答 1：R5 composer findings 閉合表

| R5 ID | 處置 | R6 狀態 | 重驗碼證 |
|---|---|---|---|
| COMPOSER-R5-P1-01 producer 寫入點 | 採納 | **已閉合** | Task 8.2 `:83-87` 具名 `split_per_symbol`／`_build_plan_pair`／orchestrator holdout；`:90-91` derive 缺欄 fail-closed；`:97` 生產路徑 ASSERT |
| COMPOSER-R5-P1-02 C-4 應列覆寫 | 採納 | **已閉合** | 觸及面 `:16` 覆寫含 C-4；`:20-21` 註解；D-001-C1 `:28-42` 新簽名＋薄 wrapper |
| COMPOSER-R5-P2-01 payload vs G-5 | 採納 | **已閉合** | D-001-C2 `:56-57` 四元組 `(position, feature_ts_ms, symbol, base_universe_hash)` 對齊 §G G-5①；`freeze_splitunify_golden.py:152-155` 同形狀 |
| COMPOSER-R5-P2-02 producer 取 ts 來源 | 採納 | **已閉合** | D-001-C2 `:59` 釘死 post-trim `feature_index`＋positional ordinals；禁全框 ts |
| COMPOSER-R5-P2-03 C1.4 無 mutation | 採納 | **已閉合** | `M-SU-D1-07` `:117`；Task 8.1 ASSERT `:76` 跨 symbol row 空間混用 |

---

## 必答 2：實質審查（八項）

**① 類別判定 D vs R**  
**立場：D 延伸成立。** BASE `Task 3.2` 存活至語句預告 per-symbol 改寫 raise；D-001 檔頭 `:8-9` 與 R5 兩家覆核一致。**反面**：若無 Task 3.2 授權，C-2 字面「多 symbol fail-closed」與 per-symbol 支援互斥而需 R——但存活至已寫死，不成立。

**② 觸及面四欄錨點**  
**立場：八 anchor 逐字存在、C-4 已正確移入覆寫。** 實跑 `git show b095cc7:…` 八條 `rg -F` 各 1 hit（含 C-4）。D-001 `:15-18` 新增／覆寫／依賴／不觸與 BASE 對得上。**反面**：若 C-4 仍列依賴會與 Task 8.1 簽名衝突——R5 修法已消除。

**③ hash 不變式**  
**立場：自洽。** D-001-C1 `:44-47` 同 symbol train/test hash 一致、跨 symbol 允許 joint hash；碼證 `ic_split_adapter.py:189-199`＋`ic_filter_orchestrator.py:907`。**反面**：若寫「跨 symbol hash 必互異」會拒收現行 IC 多標的計畫——D-001 已明文禁止。

**④ 指紋可重算性**  
**立場：封閉。** C2 `:56-60` 四元組、`int(...)` 強制、點名 `_index_as_ms`／`assert_epoch_ms_array`、排除 `_coerce_timestamp_array`、post-trim 取數、重複 position／NaT fail-closed、空 plan `sha256("[]")`。**反面**：三處 producer 若各寫一套 helper 仍可能漂移——但算法逐步寫死＋Task 8.2「同一 index 重算兩次」ASSERT 可抓；非規格缺口。

**⑤ golden 重凍與獨立 oracle**  
**立場：足夠。** C2 `:61-62` 要求改前／改後逐值對照重凍＋獨立 oracle；`freeze_splitunify_golden.py:108-111` 序列化與 C2 一致。**反面**：Task 8.2 檔案列未點名 freeze 腳本——但驗證列 `splitunify_golden.json`＋C2 第 7 點程序已足；實作者重凍時自然會改腳本或手動對照，不構成 b8 阻塞。

**⑥ ASSERT 可證偽性**  
**立場：可執行。** Task 8.1 `:71-78` 與 Task 8.2 `:91-97` 皆固定文法；R5 `GROK-R5-P1-02` 互斥已拆——`:73-74` 分「未給 Mapping」vs「給了但 symbol 不一致」。**反面**：若實作硬編碼常數 hash 仍可能過 happy path——但 `-k fingerprint` 含中間列 ts 不同＋獨立 helper 重算 ASSERT，可證偽。

**⑦ mutation 對照**  
**立場：M-SU-D1-01～07 各對應 `-k` 切片。** `:109-117` 表與 Task 8.1／8.2／8.3 ASSERT 一一覆蓋；`M-SU-D1-07` 補上 R5 P2-03 缺口。**反面**：無。

**⑧ 範圍切割**  
**立場：中間態可接受。** `:11` 排除 D1／R-5；`:123-124` SU-RESID-2 多 TF 仍 fail-closed；`pipeline.py:745-748` 現行單標的呼叫在 b8 後經 wrapper 接新簽名，不與多 TF 未解矛盾。**反面**：b8 後投影層支援多 symbol 但事件掃描仍 event-study-only——consult 已明示，非本延伸自相矛盾。

---

## 必答 3：駁回之重驗（CODEX-R5-P0-01）

**① 立場：接受駁回。** `AGENTS.md` Rule 12 逐字「**動工前**…**不動工**」——規範對象是實作動工，本輪為唯讀規格審查；R5 synth 第 5 點先例（先前三輪上游收斂檔無戳記仍照審）與 codex 本輪主張不一致。

**② 反面（若仍主張須先蓋章）**：須在 Rule 12 找到「唯讀審查」四字或同義語——**無**；「所依 reconcile/SPEC」在審查情境下指審查對象本身（D-001）之 stamp，非 consult synth 的機械戳記區。consult r2 為諮詢層產物，brief 已說明慣例不對每份收斂檔蓋章。

---

## 必答 4：C-4 覆寫後新面

**① wrapper 是否成第二份判定邏輯？**  
**否。** D-001-C1 `:42` 明文「wrapper **不得**含第二份判定邏輯」；判定全在 Mapping 主簽名內（三角相等、指紋、row 空間）。wrapper 僅 `{symbol: (train, test)}` 單鍵包裝。**否證觀測**：若 wrapper 內需獨立分支才能成立，應見 spec 要求 wrapper 判斷 multi-symbol——未見。

**② `pipeline.py` 應改哪一式？**  
**保留現行四參呼叫，走薄 wrapper。** 現行 `pipeline.py:745-748` 傳 `train_plan, test_plan, …, feature_index`；Task 8.1 `:68` 列 `pipeline.py`「改呼叫新簽名**或 wrapper**」；C1 `:42` 保留舊簽名為 wrapper。實作應在 `split_projection.py` 以 overload／wrapper 轉 Mapping，**pipeline 不必改呼叫形狀**，避免兩套 API 並存。若改為直接傳 Mapping，亦合法但非必須。

---

## 必答 5：可否進入實作

**是（`proceed`）。** 本輪 composer R5 五條全閉合；八項實質審查無 P0/P1；C-4 wrapper 路徑明確。生產碼仍無指紋欄為預期（b8 實作項），非規格缺口。

---

## §1 必查摘要（11 類）

| # | 結果 |
|---|---|
| 1 矛盾/互斥 | 無（R5 C-4／ASSERT 互斥已修） |
| 2 漏項/端到端 | 無 blocking（producer 三處＋derive 比對已列） |
| 3 不可測驗收 | 無 |
| 4 quant 假設 | 無新 blocking |
| 5–11 | 無額外 blocking |

---

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 composer 五條處置、D-001 修訂版八項實質審查、C-4 wrapper 新面與程序駁回重驗後，無新增可證偽 P0/P1 finding。

**碼證**: `sha256sum docs/SPLITUNIFY_SPEC.D-001.md`→`9bb033a39a73`；`rg row_time_fingerprint momentum/ --glob '*.py'`→0；八 anchor `git show b095cc7` 各 1 hit；D-001 Task 8.2 `:83-97` producer＋ASSERT；C-4 覆寫 `:16`＋C1 `:28-42`；`M-SU-D1-07` `:117`；`pipeline.py:745-748` 單標的呼叫；`bash scripts/debt_ledger.sh --has-open`→rc=1。RECHECK: 重讀 D-001 全文＋上述命令。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md

[P3] 信心度=High。R5 採納項均已落字；殘差（Task 8.2 生產 ASSERT 未逐字點名 orchestrator holdout、freeze 腳本未列檔案）在檔案清單與 C2 第 7 點已覆蓋，缺欄會在 derive fail-closed，不構成 b8 假綠路徑。勿捏造 finding。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R5-P1-01,COMPOSER-R5-P1-02,COMPOSER-R5-P2-01,COMPOSER-R5-P2-02,COMPOSER-R5-P2-03

---

ASSUMPTIONS_VERIFIED: D-001 sha256[:12]=`9bb033a39a73`；八 anchor @ b095cc7 各 1 hit；`rg row_time_fingerprint momentum/`→0；`ic_split_adapter.py:189-199` joint hash；`pipeline.py:745-748`；`freeze_splitunify_golden.py:152-155` 四元組；`bash scripts/debt_ledger.sh --has-open`→rc=1
TESTS_RUN: `sha256sum docs/SPLITUNIFY_SPEC.D-001.md`；`git show b095cc7:docs/SPLITUNIFY_SPEC.md` 八 anchor loop；`rg row_time_fingerprint momentum/ --glob '*.py'`；`bash scripts/debt_ledger.sh --has-open`；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r6-composer.md --family composer`→見下
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-x-review-r6-composer.md
TMP_CLEANUP: 已清 `/tmp/workdir-su-r6`（保留 `claude-501`）

STATUS: DONE
