# 第二刀主體 SPEC adversarial — 三方 RECONCILE（freeze 前）

> 日期 2026-07-07 | 三腿：`CUT2-XSECTIONAL-SPECADV-{claude,codex,composer}.md` | 依 memory「Claude 自身不享特權」本 reconcile 同須委員戳記核可才可 freeze/發實作 token。

## 收斂總覽（去重後 blocking）
| ID | Blocking | 提出腿 | 裁決 |
|---|---|---|---|
| R1 | test-only 須覆蓋**全部** report 輸出（symbol matrix/validation/rolling_ic 仍 full-sample） | Codex B-1 + Composer B-3（雙家族獨立=強訊號） | **採納**：全域時間邊界後所有 IC 統計同一 test frame |
| R2 | global vs per-symbol 切分語義未定 | Claude B-1/B-2 + Composer B-2 | **裁定=全域同步時間邊界**（見下 D-1） |
| R3 | `expected_freq`/timeframe 接線缺失（實作必炸） | Composer B-1（已驗 contracts.py:516 raise 屬實） | **採納**：D-1 全域時間 mask 繞開 rows-purge 連續性強制；仍傳 timeframe 供 metadata/freq |
| R4 | splitter/base_universe_hash 佔位符無可執行契約 | Composer B-4（已驗 ICSplitAdapter 存在） | **採納**：D-1 用時間 mask（非 split_per_symbol rows），base_universe_hash 用 `ICSplitAdapter._base_universe_hash` 算法 |
| R5 | F2 labels_path 需改 loader+HDF5 schema 否則假綠 | Codex B-2 | **裁定=最小化 F2**（見下 D-2）：fail-closed raise，不建 symbol-aware loader（另立 epic） |
| R6 | F4 覆蓋守衛須 per-symbol + floor 不可拍腦袋 | 三腿一致 | **採納**：per-symbol 覆蓋率 + 可推導下界（見下 D-3），移除 magic 0.5 |
| R7 | mutation 廉價綠燈（purge=0 不 raise；F4 需 meta-test 實關守衛） | Codex M-3 + Composer M-4 | **採納**：改 red-on-break 設計（見下 D-4） |
| R8（MAJOR升） | F1 UTC/單位/孔洞硬斷言不足；5085/5088 三列孔未解釋 | Codex M-1 + Composer M-1 | **採納**：F1 加語義等價斷言 + 解釋孔洞根因 |
| R9（MAJOR） | min_test_rows 不足行為未定（無 full-sample fallback） | Composer M-5 | **採納**：對齊單幣=raise/明確降級，禁靜默 full-sample |
| R10（MINOR） | effective_horizon 預設 5 vs return_1 horizon 1 脫鉤 | Composer m-2 | **採納**：cross_sectional purge 用 label 實際 horizon（1） |

## 技術裁決（committee，非使用者決策；memory「技術決策委派委員會」）

### D-1【R2/R3/R4】F3 改用「全域同步時間邊界」而非 per-symbol 比例切分
- **理由**：cross_sectional IC = 同一 timestamp 跨 symbol rank。per-symbol 各自比例切 → 三幣時間軸不齊時同一時刻半 test 半 train → 橫截面 universe 漂移/樣本縮水（三腿共識）。
- **設計**：由**全體 unique timestamp**（union 時間軸）依 `oos_test_size` 取分割時刻 T；`purge_td = horizon × freq`、`embargo_td = config.embargo × freq`（時間單位）；`train_mask = ts ≤ T_train_end`、`test_mask = ts ≥ (T_train_end + purge_td + embargo_td)`，**對所有 symbol 同一日曆切割**。IC 只在 test_mask 列的 per-timestamp slice 計算。
- **好處**：每個 test 時刻仍含全部在該時刻有資料的 symbol（不漂移）；純時間切 symbol 無關→無跨 symbol row 洩漏；時間 mask 繞開 `split_per_symbol` rows-purge 的 `expected_freq` 連續性強制（R3）。
- **契約**：仍以 per-symbol SplitPlan（`purge_semantic="timedelta"`, `expected_freq=EXPECTED_FREQ_BY_TIMEFRAME[timeframe]`）+ `validate_split_pair_integrity` 做**審計斷言**（train 最大時間 < test 最小時間 − purge−embargo），base_universe_hash 用 `ICSplitAdapter._base_universe_hash`。timeframe 由 `_run_analysis` 傳入 `analyze_cross_sectional(..., timeframe: str)`。

### D-2【R5】F2 最小化——fail-closed，不建 symbol-aware labels loader
- **裁決**：cross_sectional 的 `labels_path` 若 labels_df 為單軸 timestamp（現有 `_load_labels_hdf5` 唯一產出）→ **`raise InvalidInputError`「cross_sectional labels_path 單軸不支援;用 kline 衍生標籤或另立 per-symbol labels epic」**。**不**在本刀建 symbol 維度 HDF5 schema + loader（Codex B-2 指出那是跨棧大改）。
- **理由**：生產走 kline 衍生（Path B），labels_path 在 cross_sectional 無真實用途；fail-closed 消除「靜默廣播」洩漏（原 F2 目標）且不假綠、不 scope creep。symbol-aware labels_path → 另立 epic 登記。
- **使用者可否決點**：若你要保留「外部 per-symbol 標籤檔」能力，改建 loader（scope +1 epic）；預設走 fail-closed。
- **使用者裁定 2026-07-07**：**選項一（fail-closed 擋掉）確認**。理由對話收斂：labels_path 生產未用；且**事件驅動標籤（Phase 2）結構=稀疏/各幣時間不齊/正反案例**，與現行密集橫截面 loader 形狀不相容——現在建通用 dense loader 對 Phase 2 事件驅動幫助不大（會白花工），事件驅動 Phase 2 另建專屬稀疏對齊。故本刀 fail-closed，symbol-aware/event-driven labels → Phase 2 epic。

### D-3【R6】F4 per-symbol 覆蓋守衛 + 可推導下界
- **設計**：per-symbol `coverage_s = notna(label_s)/len_s`；下界 `floor_s = (len_s − effective_horizon)/len_s`（forward return 結構性 NaN 僅末 horizon 列）；`coverage_s < floor_s × (1 − tol)`（tol 小容差如 0.01 容真實孔）→ `raise InvalidInputError` 標明 symbol。全域平均僅記 metadata 不作 gate（避免單幣全壞被稀釋）。移除 magic 0.5。
- **理由**：F1 回歸=覆蓋 0.0，per-symbol floor 精準擋；「1/3 幣全壞」全域 0.67 會漏（三腿一致）。下界可推導=不拍腦袋（符合「無來源不得寫死門檻」）。

### D-4【R7】mutation red-on-break 重設計（禁廉價綠燈）
- F1：mutation 還原 datetime 對齊須走**真 3sym×12h 端到端**（非 mock kline）→ 覆蓋率回 0/5088 才算紅。
- F4：meta-test 用 monkeypatch **實際關閉 per-symbol 守衛** + 餵「1/3 幣全 NaN」→ 斷言 `pytest.raises`；不靠文件宣稱。
- F3：不靠「purge=0 → validate raise」（Codex 證其不必然 raise）；改**直接斷言** `test_min_time − train_max_time ≥ purge_td + embargo_td`，且 mutation 縮小 purge_td → 該不等式斷言 FAIL。

## 無異議閉合（三腿同意）
- F1 根因/修法方向（receipt 可重現）；forward return 無 look-ahead（F3 正名為 selection bias 非 look-ahead）；第一刀漏列 consumer 已補 + SCAR 入帳；`cross_symbol_training_service.load_multi` 為 positional 非 datetime reindex→不在本刀 consumer map（N/A）。

## Freeze 條件
上述 D-1~D-4 + R1/R8/R9/R10 全數寫回 SPEC/TODO；委員（Codex+Composer）append RECONCILE-STAMP APPROVED 後才 freeze、發實作 token。

## 戳記
（委員 append 正規式 `RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<id>`；未齊不 freeze。初審自由格式紀錄見各 FINAL 輸出檔。）
RECONCILE-STAMP: codex APPROVED 2026-07-07 sha256:5be0f6d40c6cb35a63e8bfa117c5b40f3df180468497a2435763b300b6777d86 task:cut2-xsec-stamp-cxfinal
RECONCILE-STAMP: composer APPROVED 2026-07-07 sha256:5be0f6d40c6cb35a63e8bfa117c5b40f3df180468497a2435763b300b6777d86 task:cut2-xsec-stamp-cfinal

Verdict: APPROVED — 三方 adversarial reconcile 完成(Claude+Codex+Composer),D-1~D-4 裁決落實 SPEC/TODO,委員 RECONCILE-STAMP 全數 APPROVED,無殘留 blocking。
