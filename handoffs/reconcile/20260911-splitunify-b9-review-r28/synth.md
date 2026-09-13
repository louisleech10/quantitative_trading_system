# Reconcile — 20260911-splitunify-b9-review-r28

**來源** 20260911-splitunify-b9-review-r28-codex.md, 20260911-splitunify-b9-review-r28-composer.md, 20260911-splitunify-b9-review-r28-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **N1 M1 之「超集」護欄只擋丟鍵、不擋改值**——「M1的「既有頂層鍵集合為超集」不等價於S」 | P1 | CODEX-R28-P1-01 | 採納（該家實跑把 g4_per_symbol_n 改成 999 ⇒ --write 直接接受。🔴 **主委 r27 自標之 assumed「處置等效」被此探針否證，該家判不成立、主委接受**。已改**逐值**閘：既有頂層鍵之值若會改變即 fail-closed，要改須在命令列 --accept-value-changes 逐一具名，且列了未實際改變的鍵也拒。🔴 **主委再次具名偏離該家逐字修法**：該家要「任一值改變即 fail-closed」，但那會讓**正當重凍**（例如本批新增 bnd_shift）也無法進行；改為顯式具名——把「悄悄改」變成「必須寫下你要改哪一個」，仍是機械閘而非紀律。主委實跑複驗：未具名 ⇒ rc=1 並指名該鍵） |
| **N2 外部錨寫在 helper 而非 SPEC，且無 write-once**——「M2的三層runtime比對仍未完成cu」 | P1 | CODEX-R28-P1-02 | 採納（🔴 **該家指出 SPEC §V 早在 v13 之 O2 就定死「錨在已提交文件、helper 只讀」——主委 r27 寫成 helper 常數等於又是第二份真相**。已改：①SPEC §V 新增逐字錨點行、helper 只讀且不自帶常數；②v8 與旁檔改 O_CREAT 與 O_EXCL write-once，已存在即拒絕再次建立。主委實跑複驗：拿掉 SPEC 錨點 ⇒ 正常模式 rc=1 並指名 ANCHOR MISSING；對已存在之 v8 再次建立 ⇒ rc=1 並指名 write-once） |
| **N3 人手判準只有側別，時刻仍與投影共因**——「M3的人手`expected_side`」 | P1 | CODEX-R28-P1-03 | 採納（🔴 **主委 r27 自標之 assumed「第三份判準」被該家加 1 毫秒探針否證**：側別是人手填的，但事件**時刻**仍由 `_plans` 與邊界函式推導 ⇒ 整批位移 1 毫秒、側別不變，golden 仍通過。已加第二欄人手判準 `expected_decision_at_ms`，值由兩個 fixture 常數**逐筆手算**、不讀 index、不經邊界函式，main 先做逐筆時刻對帳再做三方側別相等。主委實跑複驗該家探針：13 筆逐筆相符；加 1 毫秒 ⇒ 逐筆對帳轉紅並指名事件） |
| **N4 TODO 邊界②仍為 live「界外 ⇒ purged」（同型第八次）**——「`docs/SPLITUNIFY_TOD」 | P1 | CODEX-R28-P1-04 | 採納（逐字採該家修法：②改為「`decision_at_ms` 落在 feature_index 範圍**之外** ⇒ fail-closed raise（訊息含 `event_id`），**不是** purged」，③補上隔離帶之現行表述；舊字面刪節保留。🔴 **同型第八次**——前七次見 v19–v22 沿革） |
| **N5 composer 零 findings、v22 APPROVED**——「本輪逐項核對M1–M9閉合與v22bod」 | P3 | COMPOSER-R28-P3-00 | 採納（判 proceed） |
| **N6 grok 零 findings、v22 APPROVED**——「本輪逐項核對後無finding——本家`」 | P3 | GROK-R28-P3-00 | 採納（判 proceed） |

### 本輪裁定

1. **composer 與 grok 零 finding、對 v22 APPROVED 並 append 戳記；codex 四條 P1 全數採納並修完。**
2. 🔴 **主委 r27 自標之四條 assumed，本輪被否證兩條**（M1 等效性、M3 第三份判準），**兩條都由 codex 的實跑探針打穿**；M5／M6 兩條經該家以 malformed manifest 與 extreme many-to-one 探針複驗**成立**。⇒ 連續第六輪（R18／R21／R22／R25／R27／R28）自標疑慮被證實或被具體否證。
3. 🔴 **本輪主委兩處具名偏離該家逐字修法**（N1 之「顯式具名」取代「一律禁止改值」；理由：後者會讓正當重凍不可能）。**r27 那次偏離已由本輪 N1 證明是錯的**——主委當時說「等效」，該家探針顯示不等效。本輪這次偏離請 r29 覆核，**不得再以「等效」自我認定**。
4. **SPEC 進 v23**，新 body sha256 為 52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d（含本輪之沿革條目；本裁定寫下當時為 4c1c7b72…，補沿革後變為此值——**以本值為準**）⇒ v22 之戳記失效須重簽。回歸六路 **732 passed、0 failed、0 xfailed**。
5. 🔴 **同型第八次（N4）**：契約面一改動，舊段就落後。連續八次 ⇒ `Task 9.3` 之動工前置再確認一條：**register 重掃 receipt 須同時列出本批契約在 SPEC 與 TODO 的全部落點**（r27 已定，本輪確認仍為必要）。
6. **下一步**：派 `review-r29` 做 N1–N4 閉合再驗證 ＋ 對 v23 新 body 三家重簽；齊備後進 `Task 9.3`（批次 **B9D**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R28-P1-01

**斷言**: M1 的「既有頂層鍵集合為超集」不等價於 SPEC/TODO 要求的「既有 11 鍵逐值不變、差異只落在 v9 新鍵」；`--write` 可接受並覆寫既有鍵的不同值。

**碼證**: `scripts/freeze_splitunify_golden.py:505-523` 只計算 `_prev_keys - _new_keys`，沒有任何既有值比較或允許差異集合檢查。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:505`。`MUTATION: monkeypatch _build_actual()` 將 `actual["g4_per_symbol_n"]` 改為 `{"ETHUSDT": 999}`，以既有 main golden 執行 `main()` with `--write`；實跑輸出 `changed-existing-value RC 0 written_value {'ETHUSDT': 999}`。同一探針加入 `legacy_sentinel` 時才輸出 `lost-existing-key RC 1`，證明目前 guard 只擋丟鍵。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; docs/SPLITUNIFY_TODO.md#a6d888654276

P1，信心度 High。修法：在 `--write` 寫入前載入既有 main，逐值比較契約指定的 11 鍵；任一值改變即 fail-closed；新增鍵只允許 `g1_membership_v9`／`g3b_oracle_v9`，並以 mutation 測試證明既有值改動轉紅。可行性證據：目前既有主檔已列出 v9 新鍵與舊鍵，失敗分支可在 `write_text` 前直接判斷，不需改 golden schema。

## CODEX-R28-P1-02

**斷言**: M2 的三層 runtime 比對仍未完成 current contract：外部 digest 錨實際寫在被審查 helper 的 Python 常數，不在 SPEC §V 的 `V8_BASELINE_SHA256=<64-hex>` literal；且沒有 v8 首次 `O_EXCL` 建立／既存再次建立拒絕流程。

**碼證**: `scripts/freeze_splitunify_golden.py:402-432` 定義 `V8_BASELINE_SHA256` 並在缺檔時直接 return 1，沒有 `O_EXCL`／write-once 建立路徑。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:405`。`MUTATION: remove both v8 and sidecar, then run venv/bin/python scripts/freeze_splitunify_golden.py --write`；實跑輸出 `GOLDEN V8 MISSING ... (fail-closed)`、`M2_MISSING_RC 1`。同步改寫檔案與旁檔亦回 `M2_SYNC-TAMPERED_RC 1`，但 `rg -n '^V8_BASELINE_SHA256=' docs/SPLITUNIFY_SPEC.D-002.md` 無輸出，故目前只證明阻擋繞法，未證明 SPEC 錨與 write-once 契約已落地。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; docs/SPLITUNIFY_TODO.md#a6d888654276

P1，信心度 High。修法：同一修訂在 SPEC §V 寫入固定 `V8_BASELINE_SHA256=<64-hex>`，helper 只讀該 literal；為 v8 與 sidecar 增加明確 `O_CREAT|O_EXCL` 首次建立，檔案存在時再次建立直接 raise，並補缺檔、同步改寫、二次建立與 SPEC literal 一致性的測試。可行性證據：缺檔與同步篡改兩個現行 probe 已可辨識錯誤分支，新增建立／二次建立測試只需包住目前 `main()` 的 baseline 初始化邏輯。

## CODEX-R28-P1-03

**斷言**: M3 的人手 `expected_side` 是獨立側別字面，但事件時間仍由與投影共用的 `_plans`／`holdout_boundary`／`index` 推導；因此三方側別相等不能檢出 decision timestamp 或 boundary 的共因偏移。

**碼證**: `scripts/freeze_splitunify_golden.py:93-154,179-210` 中 `_event_keys` 以 `index[pos]` 建時間，`_hand_expected_membership` 只攤平 `expected_side`，而 oracle 仍使用同一批 event keys。`CODE-ANCHOR: scripts/freeze_splitunify_golden.py:103`。`MUTATION: monkeypatch _event_keys()` 對每列 `decision_at_ms` 加 1 ms、保持 `expected_side` 與 feature cutoff 不變，再跑 `venv/bin/python scripts/freeze_splitunify_golden.py`；實跑輸出 `M3_DECISION_TIMESTAMP_DELTA 1`、`M3_SAME_SIDE_OUTPUT_ACCEPTED True`，且 golden 仍 `GOLDEN OK`。

**來源摘要**: scripts/freeze_splitunify_golden.py#afc9390cc451; tests/momentum/Analysis/test_splitunify_golden.py#2419bee21dc4; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2

P1，信心度 High。修法：fixture 另以人手 literal 保存每個 event 的 `expected_decision_at_ms`／邊界時間，`main()` 先逐筆比對生成 event key 的 decision timestamp，再做三方 side 比對；保留 `expected_side` 作為獨立側別 judge，並新增 +1 ms mutation 必紅測試。可行性證據：目前 G-4e 已能獨立比對 side，新增欄位只增加一個 fixture 對帳閘，不需讓 hand judge 呼叫投影或 oracle。

## CODEX-R28-P1-04

**斷言**: `docs/SPLITUNIFY_TODO.md:273` 仍有未標 superseded 的 live 邊界規則「事件不在 `feature_index` ⇒ purged」，與 Task 9.2b current contract「`decision_at_ms` 越出 index 範圍必須 raise、不是 purged」互斥；實作者照 TODO 會回退已修正的 fail-closed 行為。

**碼證**: `docs/SPLITUNIFY_TODO.md:271-274` 的 live 邊界列直接要求 out-of-index purged，對照 `tests/momentum/Analysis/test_splitunify_derive.py:1771-1787` 的兩個 raise tests。`CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:273`。`MUTATION: implement the live TODO rule by classifying an out-of-range decision_at_ms as purged; run venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'decision_before_index_start_raises or decision_after_index_end_raises'`；目前正確實作的對照結果為 2 tests passed，該 mutation 應轉紅。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a6d888654276; docs/SPLITUNIFY_SPEC.D-002.md#aa1eace953c2; tests/momentum/Analysis/test_splitunify_derive.py#2419bee21dc4

P1，信心度 High。修法（可直接貼入）：`- 邊界：① event_keys 為空 ⇒ 三態皆空（不 raise）；② manifest.table.decision_at_ms 落在 [index_ms[0], index_ms[-1]] 之外 ⇒ fail-closed raise（訊息含 event_id），不是 purged；feature_cutoff_ms 不參與 split_label；③ train_last_ms < decision_at_ms < test_start_ms ⇒ assignments 空而 purged 為全集（隔離帶合法且預期）。` 可行性證據：現有兩個 out-of-range raise tests 與 728 路回歸已對應 ②，現有 golden 對隔離帶 purged 對應 ③。

### 3. assumed 四條

- M1「處置等效」：**不成立**。上列 P1-01 探針實際寫入既有鍵新值；可落地修法是既有 11 鍵逐值相等＋v9 允許鍵白名單。
- M3「第三份判準」：**不成立**。side 是第三份字面，但 timestamp／boundary 不是；上列 P1-03 的 +1 ms probe 仍接受。
- M6「移動 guard 未改錯誤型別」：**成立**。`venv/bin/python -m pytest -q ...` 8 tests passed；另以缺少 `decision_at_ms`、單欄 NaN、重複 event 混合 NaN 的 malformed manifest probe 均觀測到 `ValueError`，未出現非預期 `AlignmentViolationError`。
- M5「唯一性不擋合法多 TF」：**成立**。`build_event_keys` 的 extreme many-to-one probe 輸出 `M5_MANY_TO_ONE_LABEL_END_VALUES [20, 20]`、`M5_LEGAL_MULTI_TF_UNIQUE True`；不一致值仍由唯一性 guard fail-closed。

### 4. 強制自立詞表掃描

自立詞表：`decision_at_ms`, `feature_cutoff_ms`, `cutoff`, `split_label`, `train_last_ms`, `test_start_ms`, `feature_index`, `index_ms`, `side`, `purged`, `assignments`, `不參與`, `錨定`, `三段式`, `界外`, `SUPERSEDED`。

命令：`{ awk 'NR<335{print}' docs/SPLITUNIFY_SPEC.D-002.md; sed -n '1,$p' docs/SPLITUNIFY_TODO.md; } | rg -n 'decision_at_ms|feature_cutoff_ms|cutoff|split_label|train_last_ms|test_start_ms|feature_index|index_ms|side|purged|assignments|不參與|錨定|三段式|界外|SUPERSEDED'`，再逐段讀取命中行並排除 brief 明定的 HISTORY／沿革／前版標記。

逐段結論：SPEC D-002-C3、§P Task 9.2b、§V 與 §G current block 均以事件級 `decision_at_ms` 定側，明示 `feature_cutoff_ms` 不參與 `split_label`；TODO Task 2.2 的點 1/2/4 已 `SUPERSEDED`，Task 9.2b 與 §E `SU-RESID-2` 亦為 current 語意。唯一未標 superseded 且互斥的 live 命中是 `docs/SPLITUNIFY_TODO.md:273`，即 CODEX-R28-P1-04；其餘命中為 current 相容敘述或歷史追溯。

### 5. Task 9.3 gate

不能進 Task 9.3。最小閉合集合：`CODEX-R28-P1-01`、`CODEX-R28-P1-02`、`CODEX-R28-P1-03`、`CODEX-R28-P1-04`；四項各自有一次修訂內可執行的修法與反向驗證。728 路回歸通過不抵銷四個規格／golden gate 缺口。

### 收尾

VERDICT: blocked
BLOCKED-BY: CODEX-R28-P1-01,CODEX-R28-P1-02,CODEX-R28-P1-03,CODEX-R28-P1-04
CLOSED: CODEX-R27-P1-01,CODEX-R27-P1-02,CODEX-R27-P1-03,CODEX-R27-P1-04,CODEX-R27-P2-05,CODEX-R27-P2-06,CODEX-R27-P2-07
ASSUMPTIONS_VERIFIED: M1 不成立；M3 不成立；M5 成立；M6 成立；M1/M2/M3 探針與 current source anchors 已實跑；詞表掃描定位 TODO:273。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → 728 passed in 69.06s; 定向 8 tests → 8 passed; `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`; `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → expected hash、rc=0; both `doc_format_precheck.sh` targets → rc=0。
FAILURES_SEEN: 初版 M1/M2 temp harness 曾有 harness-only `relative_to`／cleanup traceback，未影響產品判定；改用 repo-independent temp harness 後取得上述 rc/output。一次錯誤 pytest node 名稱造成 collection rc=4，已改用存在的 8 個測試 node 並 rc=0；completeness 首次抓到 P1-01 缺 `CODE-ANCHOR:`，補字面後以同組參數重跑 rc=0；無產品測試 failure。
SCOPE_CHANGES: 未改程式碼、SPEC 正文或 TODO；僅新增本報告、append D-002 戳記、及新增本 task 交接檔；未觸碰 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 無；本輪為 review，未改 runtime、數值、schema 或 golden artifacts。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r28-codex.md
STATUS: DONE
## COMPOSER-R28-P3-00

**斷言**: 本輪逐項核對 M1–M9 閉合與 v22 body 後無需阻擋收斂的 finding；r27 本家 `COMPOSER-R27-P2-01` 已由 M9 關閉。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132` rc=0；`pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → **136 passed** rc=0；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK` rc=0；換詞表 awk+grep（必答 4）無 live per-cutoff 施工句。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#dece985e17e9; handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md#b1ec3d0c

doc-literal-only；信心度=High。M1 之「允許改值重凍」與 SPEC §V (vii) 字面差為 r27 已裁定偏離，不阻擋 B9D。

---

## GROK-R28-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 `GROK-R27-P1-01`／`P1-02`／`P2-01` 反例已 CLOSED；M1–M9 修補與四條 assumed 經探針／成對測試／自立詞表掃描後，無與「側別由事件級 `decision_at_ms` 錨定、`feature_cutoff_ms` 不參與 `split_label`」互斥之 live 阻擋項；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132`；Task 2.2 之 `SUPERSEDED BY Task 9.2b` 計數＝3；`SU-RESID-2` 尚未關閉者＝Task 9.3；M1 `--write` 拒 `legacy_sentinel`（rc=1）；M2 缺席／雙改皆 rc=1；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；pytest derive＋wiring＋golden → **136 passed**；M5／M6 成對＋缺欄／NaN 探針皆具名 fail-closed；詞表 `grep` live 互斥命中＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R28-BRIEF.md#afddb78295dd; docs/SPLITUNIFY_SPEC.D-002.md#32fccef8d08a; docs/SPLITUNIFY_TODO.md#b9fbd797573a; handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md#b1ec3d0c

---

