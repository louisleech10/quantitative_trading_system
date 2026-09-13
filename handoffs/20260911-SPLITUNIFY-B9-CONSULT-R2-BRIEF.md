# SPLITUNIFY b9 — 未 commit 生產碼保留或回退（技術裁定）

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 本輪是**裁定輪，不是規格審查輪**。D-002 v13 之停輪判準已於 `handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md` 觸發並由三家確認；**不要再審 D-002 的規格內容本身**，除非你的 finding 直接決定下列必答之答案。

## 要裁什麼（一句話）
工作區有一批**未 commit、無 impl token、規格從未蓋章**的 b9 生產碼。請三家裁定：**整批保留（補程序）**、**整批回退（`git checkout --` 丟棄）**、或**部分保留**（須逐 hunk 具名）。這是技術決策，不問使用者。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **本輪 diff**（就是被裁定的全部標的，四檔）：
  - `git diff -- momentum/Analysis/event_samples/split_projection.py momentum/Analysis/event_samples/pipeline.py`
  - `git diff -- tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py`
- **current block**（規格側，只看這幾節，勿讀全檔）：
  - `docs/SPLITUNIFY_SPEC.D-002.md` §V（`sed -n '254,312p'`）、§P Phase 與依賴（`sed -n '172,250p'`）、`### D-002-C0`（`sed -n '24,41p'`）
  - `docs/SPLITUNIFY_TODO.md` §E 具名殘留（`grep -n '^## §E' -A200 docs/SPLITUNIFY_TODO.md`）
- 🔴 **不在審查範圍**：修訂沿革（`HISTORY-BEGIN`～`HISTORY-END`、「沿革與追溯索引」節）與逐字標記「作廢／前版／舊敘述／原寫」之字面。**finding 之 source anchor 落在歷史段者不受理**（`completeness --single` 會 fail-closed 拒收），請改指其對應之現行條文。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 這批碼**沒有** impl token，且 `docs/SPLITUNIFY_SPEC.D-002.md` 至今**零 RECONCILE-STAMP** → `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` 逐字輸出「未獲全數委員核可」，codex／composer／grok 三家皆列「缺 APPROVED 戳記」；body sha256 = `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`。
fact-verified: 這批碼**現在是紅的** → `python -m pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py -q` 得 **2 failed／91 passed**，失敗者為 `test_duplicate_event_id_is_fail_closed`（斷言訊息仍期待舊的「每事件一列」語意）與 `test_multi_feature_tf_opposite_sides_must_fail_closed`（fixture 之 `manifest.table` 對同一 `event_id` 放兩列，先被 manifest 事件級唯一性擋掉，regex `同一事件|異側|同側` 不match）。
fact-verified: 這批碼**未**實作 v13 之 O4 → `grep -n "validate_split_pair_integrity" momentum/Analysis/event_samples/pipeline.py` 命中數 **0**；全 repo 只有 `momentum/Analysis/ic_split_adapter.py:22,305`（IC 路徑）。v13 §V 要求「進入 `derive_event_split_from_plans` **之前**，由 `EventSamplePipeline.run` 以 `feature_index` 之時刻作 `ts`、`train_plan.symbol` 廣播作 `symbols` 呼叫 validator」。
fact-verified: `docs/SPLITUNIFY_TODO.md` **沒有** `Task 9.1`–`9.5` 的任務段 → `grep -nE '^#+ *Task ' docs/SPLITUNIFY_TODO.md` 只列到 `Task 4.1`；字串 `Task 9.1` 全檔只出現在 §E 殘留 `SU-RESID-9A-UI` 的內文一處。
fact-verified: `tests/golden/splitunify/splitunify_golden.v8.json` **不存在**（`ls tests/golden/splitunify/` 只有 `clusters_oracle.json`／`report_int_keys.json`／`splitunify_golden.json`），且 SPEC 內 `V8_BASELINE_SHA256=<64-hex>` 錨點行**未寫入**（`grep -n "V8_BASELINE_SHA256"` 只命中 §V／§P 的**要求文字**，無 64-hex 字面）⇒ v13 自己已標「凍結當下才生效」。
fact-verified: 無 OPEN 債 → `bash scripts/debt_ledger.sh --list` 全數 `state=CLOSED`；`--has-open` rc=0。派工後預期值: `--has-open` rc=1（本輪開債），三家交件並 `debt_clear` 後回到 rc=0。

assumed: 這批碼是**對著 v12 以前的 D-002 寫的**，因此與 v13 的 O1／O3／O4 三處修訂在語意上不相容，保留它會讓 `Task 9.2b` 的具名落點落空。**我的否證觀測（已先跑）**：若此假設為假，`pipeline.py` 的 diff 裡應能看到 v13 O4 要求的 validator 呼叫或至少 `symbols` 陣列構造——實查 `grep -n "validate_split_pair_integrity\|symbols" momentum/Analysis/event_samples/pipeline.py` 對前者 0 命中。**但我沒查**：diff 內容是否與 v13 的 O1（metadata 兩條 ASSERT 移入殘留）相容——有可能它本來就沒碰 metadata，那 O1 對這批碼是 no-op。← **請直接攻這條**，特別是「部分相容」的可能。

assumed: 「回退」的成本上界是**重寫這 4 檔的 diff**，沒有其他檔依賴它。**我的否證觀測（已先跑）**：`git status --porcelain` 顯示 `momentum/`／`tests/` 底下只有這 4 檔 ＋ 3 個 `__pycache__/*.nbi` ＋ `tests/golden/l65/test_inventory.txt`（後者是跑測試的副作用，`bash scripts/restore_golden_inventory.sh` 可還原）。**但我沒查**：`handoffs/20260911-splitunify-b9-probe-multitf.py`（已 staged）是否依賴新的 `build_event_keys` 兩回傳值簽章；也沒查是否有別處呼叫 `build_event_keys`。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| `build_event_keys` 簽章由 `DataFrame` 改為 `Tuple[DataFrame, Dict]` 的破壞範圍 | — | **全 repo 呼叫點盤點**（含 `handoffs/*.py` 探針、`api/`、`tests/`）——請實跑 `grep -rn "build_event_keys" --include='*.py' .` 並逐筆判是否會壞 |
| `assignments`／`purged` 兩表新增 `feature_timeframe` 欄的下游消費面 | — | D-002 register 29 條裡哪幾條被這個欄位變更命中；`extract_event_patterns`（TODO §E `R-4` 說無 production caller、測試 caller 8 處）是否會紅 |
| 兩條紅測試是「測試過時」還是「實作錯」 | — | 請逐條判並給碼證：若判「測試過時」，須指出 v13 現行條文哪一句授權該語意變更；若判「實作錯」，須給 MUTATION |
| 規格側停輪判準是否仍成立 | 三家已於 R12 確認四項已閉（見 r12 synth「停輪判斷」段） | — |
| golden／baseline 影響 | `splitunify_golden.v8.json` 不存在、錨點未寫（見 fact-verified 第 5 條）⇒ `Task 9.5` 尚未開工，本批不觸及 golden byte | 這批 diff 是否會移動**既有** `splitunify_golden.json` 的 11 個頂層鍵任一值 |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 整批保留、整批回退、還是部分保留？請給**單一**裁定字面：`KEEP` / `REVERT` / `PARTIAL`。
   **(1b)** 你這個裁定若是錯的，會以什麼形式在後面爆掉？請給一個**可執行的觀測**（命令 ＋ 期望 rc 或輸出特徵），讓主委在下一批就能發現裁錯。
2. **(2a)** 若 `PARTIAL`：逐 hunk 具名要保留哪幾段（`檔:行區間`）、丟哪幾段，且**必須**說明保留段在「規格未蓋章」下如何不變成既成事實。
   **(2b)** 若 `KEEP` 或 `REVERT`：說明你為何**不**選 `PARTIAL`——具體是哪個技術理由讓逐 hunk 切分不可行或不划算。
3. **(3a)** 兩條紅測試（`test_duplicate_event_id_is_fail_closed`、`test_multi_feature_tf_opposite_sides_must_fail_closed`）：判「測試過時」還是「實作錯」？逐條。
   **(3b)** 你的判定要怎麼被推翻？給出「若我判錯，跑 X 會看到 Y」的可證偽觀測。
4. **(4a)** 補 `docs/SPLITUNIFY_TODO.md` 之 `Task 9.1`–`9.5` 時，**每個 Task 的驗收命令**該長什麼樣？請逐 Task 給**可直接貼進 TODO 的驗收命令字面**（`pytest ... -k ...` 或 `bash scripts/...`）。🔴 **禁寫聚合期望數**（不得寫「應 N passed」之類會漂的值）；寫**具名測試函式名**或 mutation 轉紅的判準。
   **(4b)** 這 5 個 Task 的**依賴順序**為何？哪些可並行、哪些必須序列（給理由，不要只排清單）。
5. **(5a)** 本輪之後要派一個 **stamp 輪**替 `docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb…`）補 `RECONCILE-STAMP`。以現行 v13 內容，你**現在**會 APPROVED 還是 REJECTED？若 REJECTED，列出阻擋條目（每條須可在一次修訂內關閉）。
   **(5b)** 若你在 (5a) 答 APPROVED，請指出 v13 裡**最可能在實作期變紅**的那一條條文（具名），以及它變紅時該怎麼處理（改碼 or 改規格）。
6. **(6a)** 可以進 `Task 9.1` 實作嗎，還是有 BLOCKING 必須先修？
   **(6b)** 若有 BLOCKING，列出**最小**閉合集合（不是願望清單）；若無，說明你檢查了什麼才敢說無。

## 🔴 本輪格式硬約束（DOCROT／CXSTAMP 2026-09-13 上線，違反會被機械閘退件）
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**（缺則 `completeness_check.sh --single` fail-closed 拒收整份交件）：
   - `CODE-ANCHOR: <path>:<line>`（或 `<path>:<A>-<B>`）
   - `MUTATION: <可執行的破壞>`（要能真的跑）
2. **anchor 不得落在標的 SPEC 的 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**；落在歷史區＝整份被拒。指現行條文。
3. **欄位內容必須與標籤同一行**（逐行判）。`**碼證**:` 後面接換行再條列＝空殼，會被退件（codex 於 CXSTAMP 已連續踩兩次）。
4. **零 findings 時**不得只寫散文：須用 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的零 findings sentinel 形態，且 sentinel 內同樣要有**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` 空值或 finding ID 清單。

## 🔴 本輪同時是 DOCROT 的成效量測點之一
DOCROT 的成效判準是 `doc_friction_ratio`（唯一權威＝`handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md`）。這代表：**若你的 finding 是在講「同一個決定寫在多處／漏同步一處／前版修法沒回寫」**，請照實寫，不要為了讓數字好看而不提；但**請先確認該落點不是歷史段**（見上「不在審查範圍」），歷史段的重複不算現行缺陷。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼**（只產 review 檔；本輪連測試檔也不准動）。收尾清 /tmp workdir（保留 claude-501）。
