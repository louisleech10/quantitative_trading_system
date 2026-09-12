# Reconcile — 20260911-splitunify-b9-review-r9

**來源** 20260911-splitunify-b9-review-r9-codex.md, 20260911-splitunify-b9-review-r9-composer.md, 20260911-splitunify-b9-review-r9-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **L1 (G-4c) 擋不住兩邊同錯（三家獨立撞題）**——「G-4c的「同步逐行重寫獨立oracle」「(G-4c)宣稱G-3b在同步改寫`_o」「(G-4c)「同步改寫`_oracle_」 | P1 | CODEX-R9-P1-02, COMPOSER-R9-P1-01, GROK-R9-P1-01 | 採納（**我判斷錯誤**：同步改寫 oracle 只能抓不對稱錯誤。保留 (G-4c) 作 regression，**另加第三份判準**——以 `Task 9.2b` 三段式（含步驟 0）從 fixture 欄位純函式算出每事件期望側，與投影／oracle **雙邊**比對；三家各給出反例 `decision=950/cutoff=900`、`decision=cutoff=train_last=200`、`decision=250/cutoff=200`，皆為兩邊同錯而 G-3b 綠） |
| **L2 (G-4d) 三附帶未進 §V／mutation（三家）**——「G-4d的三個硬條件只寫在§G，未成為§」「K1採納之**(G-4d)三項硬性附帶*」（併入 L1 之 grok 條） | P1 | CODEX-R9-P1-03, COMPOSER-R9-P1-02 | 採納（主委已複驗：`decision != cutoff`／`零位移`／`v8 baseline` 三字面**只在 `:129` 與沿革**，§V 範圍 `:216-257` 無一命中 ⇒ 「寫了要做卻沒做」第五次。§V 增三條具名 ASSERT、mutation 增對應列，並要求 `--write` 另寫新鍵不覆寫 v8） |
| **L3 `Task 9.1` 目標句仍要終端可見（三家）**——「Task9.1的目標仍要求「必須讓終端使」「K2宣稱`:140`標題句等四處同批修正」「K2宣稱「目標句已改」未完成——Task」 | P1 | CODEX-R9-P1-01, COMPOSER-R9-P2-02, GROK-R9-P1-04 | 採納（L137 改為「先消除 **producer 層**之靜默丟棄誠實性缺陷；終端可見性見 §N `SU-RESID-9A-UI`」，並全文 grep「終端使用者看得到」清殘句） |
| **L4 K3 引錯權威範本（三家）**——「K3對「`blocked-by`必須是票」「K3駁回composer「blocked」「K3駁回所引`BRIEF_REVIEW_」 | P1 | CODEX-R9-P1-04, COMPOSER-R9-P2-01, GROK-R9-P1-02 | 採納（**我引錯權威**：§N 之權威為 `templates/SPEC_TEMPLATE.md:107-112`（**三值**＋強制欄 `為何現在不做:`），我引的 `BRIEF_REVIEW_TEMPLATE.md:71` 四值是 brief 內「沒查的那句話」表。三家一致認為**類別 `blocked-by` 仍可成立**（該範本允許「檔/層/前置票」），錯的是依據與缺欄 ⇒ 改引 SPEC_TEMPLATE、補 `為何現在不做: blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/ 呼叫點=0）`、刪去 §N 內的 BRIEF 四值依據句） |
| **L5 K4 逃逸句未擇定（三家）**——「K4的「成本過高時只交前兩層」仍是未裁決」「K4在L149把`metadata.sp」「Task9.1L149「若成本超出9A定」 | P1 | CODEX-R9-P1-05, COMPOSER-R9-P1-04, GROK-R9-P1-03 | 採納（擇定**三層**並刪除 L149 逃逸句）。依據為主委實讀契約：`split_unify.json` 之 `test_segment_count_keys` 為 deny-by-default 封閉登記，但其判準是「鍵名含 `test` 且值為整數」，而 `discarded_rows_by_feature_tf` 之值為 `Dict[str, int]` ⇒ **不落入該登記**，實際須改者為三處（builder 五鍵回傳、`tests/api/test_splitunify_disclosure.py` exact-key、前端型別），低於 codex 原估五處；兩層方案反而會讓「唯一真相源」缺揭露欄而誘發第二份真相源 |
| **L6 §G L127 與 (G-4a)／(G-4c) 互斥**——「§GL127「任一單TF舊值位移即FAI」 | P1 | COMPOSER-R9-P1-03 | 採納（L127 改為「**(G-4d) 允許之差異集合內**位移除外；其餘位移即 FAIL」，刪一刀切句） |
| **L7 三層方案缺 producer→metadata 之 handoff（codex 獨得）**——「三層方案沒有定義producer的`di」 | P1 | CODEX-R9-P1-06 | 採納（🔴 **這正好補上我擇定三層時漏掉的一環**：`build_split_unify_disclosure` 簽名無 `discarded`、唯一 caller 拿不到 `EventSplitPlan` ⇒ 實作者可寫**孤立欄位單測**通過而真實計數在邊界遺失。`Task 9.1` 須指定一條 producer-result／context handoff 使同一份 `discarded_rows_by_feature_tf` 明確流入 metadata，並以 **producer→summary→metadata 整鏈**測試驗值與 exact-key） |
| **L8 baseline「樣本數＝事件數」不是不變式（codex 獨得）**——「C6的「事件級物化前提下baseline」 | P1 | CODEX-R9-P1-07 | 採納（**我 v9 的更正過頭了**：物化允許事件進 `failures` 而不進 `features`（`feature_materialization.py:100-140`），baseline 取 `features_at_decision.index.intersection(test_ids)` 後 `len(idx)` 會少算。反例：test 有 `e1`、物化失敗也有 `e1` ⇒ baseline `n_test=0` 而事件數 1。改法：baseline **同時輸出** `n_test_events` 與 `n_test_samples`，或在 baseline 前要求完整物化並對缺失事件 fail-closed；配 failure fixture） |
| **L9 Step 0 未驗 split pair 完整性（codex 獨得）**——「R8新增的Step0只處理`decisi」 | P1 | CODEX-R9-P1-08 | 部分採納（**採納**：Step 0 須一併要求 train／test **非空**、row sets 不重疊，並在任何 side rule 前呼叫既有 `validate_split_pair_integrity`——碼證顯示 derive 路徑**從未呼叫**它，且 `:498-527` 對 train 空只 `continue`。**駁回**其「`train_last_ms == test_start_ms` 可同時命中」之前提：主委推導 `train` 末位＝`split_point-1`、`test` 首位＝`split_point+purge_gap+embargo`，位置差 `≥ 1`，且 `split_projection.py:213` 明定 `feature_index` **必須嚴格遞增** ⇒ `train_last_ms < test_start_ms` 為既有不變量；但**須在 `Task 9.2b` 具名引用該不變量**，否則讀者無從得知前提來源） |
| **L10 殘留無 owner／權威登記（兩家）**——「`SU-RESID-9A-UI`的tri」「`SU-RESID-9A-UI`觸發條件」 | P2 | CODEX-R9-P2-09, COMPOSER-R9-P2-03 | 採納（於 `docs/SPLITUNIFY_TODO.md` §E 登記該殘留並附 owner 與 recheck 命令；觸發條件寫成可執行 grep（`api/` 之 `EventSamplePipeline().run` 命中數 > 0），列入收 epic 前之固定檢查項） |
| **L11 §V 缺 early／late 斷言**——「K5採納要求「補early／late之§」 | P2 | COMPOSER-R9-P2-04 | 採納（§V 增兩條：`decision_at_ms` 早於 `index_ms[0]`／晚於末列 ⇒ raise，不得進 train/test） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **L1／L8 是我的判斷錯誤**：前者我以為「同步改寫 oracle」可取代 allowlist，三家各給反例推翻；後者我 v9 為了解 K6 而把 baseline 改成「樣本數＝事件數」，**更正過頭**——物化失敗會讓兩者不等。
2. **L2／L3 是我「寫了要做卻沒做」第五、六次**：(G-4d) 自己寫「須進 §V 與 mutation」卻沒進；K2 宣稱「四處同批改完」而目標句 L137 沒改。
3. **L4 是我引錯權威**：拿治理 brief 的範本去駁 SPEC §N 的規則，還據此改壞自己原本正確的記憶。
4. **L7 補上我擇定三層時漏掉的一環**：只寫「加欄位」而沒定義資料怎麼流過去，會產出孤立單測。
5. **收斂性**：R9 共 21 條、三家獨立撞題達五群——數量未降，但性質仍是**具體可閉合**。停輪條件未觸發；真正該改的是我的修訂紀律（每項改完須逐條 grep 自證落點）。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R9-P1-01
**斷言**：Task 9.1 的目標仍要求「必須讓終端使用者看得到」，同一份 SPEC 卻把 API/前端可見性列為 `SU-RESID-9A-UI`、明載本延伸交付後使用者仍看不到；這使「9A 已消除誠實性缺陷」與「只做到 producer」兩種驗收解讀同時存在。失敗面是完成判定可在未達終端目標時被宣稱通過。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '136,150p;262,270p'` 顯示 L137 的終端目標、L142/L147/L150 的 producer-only/殘留決策與 L267 的不可見誠實邊界；`rg -n 'EventSamplePipeline|EventSamplePipeline\(\)|\.run\(' api --glob '*.py'` 未找到投影路徑之生產 `EventSamplePipeline.run` 呼叫點。修復：將 Task 9.1 目標改成「producer 層完整記帳」，並明確指向 `SU-RESID-9A-UI`，待投影生產接線後再驗終端可見性；這不會偽造 API 完成。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/pipeline.py#55ca7327764f`

## CODEX-R9-P1-02
**斷言**：G-4c 的「同步逐行重寫獨立 oracle」不是足以區分換錨改側與兩份共同錯誤的機械閘。具體反例：`index=[100,200,300,400]`、`train_last_ms=200`、`test_start_ms=300`、`decision_at_ms=250`、`feature_cutoff_ms=200`；正確 decision-anchor 結果是 `purged`，若被測投影與 oracle 都誤用 cutoff，兩者都得 `train`，G-3b 仍相等而綠燈。
**碼證**：`nl -ba scripts/freeze_splitunify_golden.py | sed -n '132,155p;340,352p'` 顯示 `_oracle_membership` 目前逐列以 `feature_cutoff_ms` 判側，`main()` 只比較 `g1_membership == g3b_oracle`；同檔 `:112-123` 又把 fixture 的 `decision_at_ms` 直接設成 cutoff，現有資料沒有暴露反例。修復：保留不 import 投影的 oracle，但在 fixture 明列 decision/cutoff 與預期 side，至少加入上述 gap 反例及事件級 expected-membership 斷言；再以 G-3b 做第二份推導對證。可行性證據：現有 `_build_actual()`/`main()` 已是單一擴充入口，無需新增 allowlist 檔。信心：高。
**來源摘要**: `scripts/freeze_splitunify_golden.py#e331623163d2`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-03
**斷言**：G-4d 的三個硬條件只寫在 §G，未成為 §V 的可執行驗收或 mutation：保留 v8 baseline、不覆寫、`decision==cutoff` 零位移、`decision!=cutoff` 單 TF 邊界 fixture。現有 golden 命令雖通過，不能證明這三件事；重凍或 fixture 維持等值都可能把缺口遮住。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '124,130p;216,226p;227,256p'` 顯示 G-4d 在 L129，但 §V 只有多 TF 反例與舊值斷言，mutation 表沒有 G-4d 專屬項；`nl -ba scripts/freeze_splitunify_golden.py | sed -n '112,123p;346,352p;373,377p'` 顯示 fixture 令 decision 等於 cutoff，且 `--write` 可直接寫 golden。實跑 `venv/bin/python scripts/freeze_splitunify_golden.py` rc=0 僅輸出 G-3b/G-5/golden OK。修復：新增命名的 G-4d test/mutation，保留不可覆寫的 v8 鍵、對等值事件做零位移斷言、對非等值事件做單 TF 邊界 expected-side 斷言；讓 `--write` 另寫新鍵。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `scripts/freeze_splitunify_golden.py#e331623163d2`

## CODEX-R9-P1-04
**斷言**：K3 對「`blocked-by` 必須是票號」的反駁方向正確，但採用的權威文件錯了，且 §N 殘留缺少模板要求的 literal `為何現在不做:` 欄；因此目前不能宣稱 `SU-RESID-9A-UI` 治理格式合規。BRIEF 的四值 `reason_code` 是「我沒查的」表格欄，不是 SPEC §N 殘留欄位。
**碼證**：`nl -ba templates/BRIEF_REVIEW_TEMPLATE.md | sed -n '62,72p;167,174p'` 顯示四值只屬 brief 表；`nl -ba templates/SPEC_TEMPLATE.md | sed -n '107,113p'` 與 `nl -ba templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md | sed -n '47,50p'` 明定 §N 必須寫 `為何現在不做:`，且只允許 `blocked-by:<具體依賴（檔/層/前置票）>`、`user-ruling:`、`needs-research:`。`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '262,270p'` 顯示 L267 只有裸 `blocked-by`。修復：保留「不必是票號」的結論，但改引 SPEC_TEMPLATE，並寫成 `為何現在不做: blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/呼叫點=0）`，同時補權威登記處與觸發條件。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `templates/BRIEF_REVIEW_TEMPLATE.md#82dfcbd10f3`; `templates/SPEC_TEMPLATE.md#0b2f68f0c38a`; `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa`

## CODEX-R9-P1-05
**斷言**：K4 的「成本過高時只交前兩層」仍是未裁決的二選一，與同一段已指定 `metadata.split_unify` 欄位、§V 三層斷言、`M-SU-D2-03` 應紅測試互相衝突；實作者可合法選擇兩層或三層，造成半套契約或驗收分叉。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '148,151p;218,225p;231,234p'` 同時顯示三層交付、metadata 斷言與「成本高則前兩層」條件。修復選擇：現在鎖定三層（producer 回傳、`EventSplitPlan.summary`、`metadata.split_unify`），刪除成本條件；理由是 SPEC 已列出 exact-key 契約、欄位型別與既有 mutation/測試落點，縮成兩層反而要同步改寫 §V、mutation、殘留和契約。可行性證據：現有 metadata 只有一個 builder/caller，可在一個資料流內定義 handoff（詳 `CODEX-R9-P1-06`），不需要新增 API。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/split_projection.py#99bfddace904`

## CODEX-R9-P1-06
**斷言**：三層方案沒有定義 producer 的 `discarded` 如何到達實際 `metadata.split_unify`；目前 metadata 產生器只接受 `n_test`/timestamps/counts/reason，唯一現行 caller 也沒有 `EventSplitPlan` 或 `discarded`。因此可寫一個孤立的欄位單測並通過，卻仍讓真實 producer 計數在 metadata 邊界遺失。
**碼證**：`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '123,181p'` 顯示 `build_split_unify_disclosure` signature 無 `discarded` 且固定回五鍵；`nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '1525,1534p'` 顯示唯一 caller 只傳 `n_test`、timestamps、per-symbol counts；`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '138,149p;218,219p'` 卻要求 summary 值再進 metadata。修復：在鎖定三層後指定一個 producer-result/context handoff，讓同一個 `discarded_rows_by_feature_tf` 明確流入 metadata，並以 producer→summary→metadata 整鏈測試驗值與 exact-key；或若架構不能接，收回三層承諾而不是留孤立欄位。可行性證據：`rg` 已盤定唯一 builder caller，變更面是封閉的。信心：高。
**來源摘要**: `momentum/Analysis/event_samples/split_projection.py#99bfddace904`; `momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-07
**斷言**：C6 的「事件級物化前提下 baseline 的 `n_test` 等於樣本數也等於事件數」不是一般不變式；物化允許事件進 failure table 而不進 features，baseline 又只對 features index 與 test IDs 取交集，故一個 assigned test event 可能使 baseline `n_test` 少一個。
**碼證**：`nl -ba momentum/Analysis/event_samples/feature_materialization.py | sed -n '100,140p'` 顯示 warmup/非有限值會寫入 `failures`、不寫 `features`，但只保證 input = features + failures；`nl -ba momentum/Analysis/event_samples/baseline.py | sed -n '105,121p'` 顯示 `idx = features_at_decision.index.intersection(test_ids)` 後以 `len(idx)` 寫 `n_test`。這直接構成反例：test assignment 有 `e1`，materialization failure 也有 `e1`，features 無 `e1`，baseline `n_test=0` 而 test event count=1。修復：明定 baseline 同時輸出 `n_test_events=unique(test_ids)` 與 `n_test_samples=len(idx)`，或在 baseline 前要求完整物化並對缺失事件 fail-closed；補一個 failure fixture，不能靠「事件級」語意推導兩數永遠相等。信心：高。
**來源摘要**: `momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2`; `momentum/Analysis/event_samples/baseline.py#38c7ec473653`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-08
**斷言**：R8 新增的 Step 0 只處理 `decision_at_ms` 在 feature index 首尾之外；它沒有使 train/test plans 本身互斥、有序且非空，因此「三段規則互斥且窮盡」仍未成立。若 `train_last_ms == test_start_ms`，decision 同時命中 train 與 test；若 train 為空，SPEC 要求取 `train_rows[-1]` 而現行程式明許極端切分可空，會先遇到未定義邊界。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '180,187p'` 的 Step 0 僅驗 index 首尾；`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '498,527p'` 顯示只對 test 空 fail-closed、train 空則 `continue`，並直接建立 `train_ms/test_ms`；`nl -ba momentum/core/contracts.py | sed -n '404,415p;676,712p'` 顯示 `SplitPlan.__post_init__` 無 pair 關係檢查，雖有 `validate_split_pair_integrity`（含非空/洩漏檢查）但該 derive 路徑未呼叫。修復：Step 0 一併要求 train/test 非空、`train_last_ms < test_start_ms`、row sets 不重疊且 pair integrity 通過，或明定空 train 的 fail-closed 訊息；在任何 side rule 前執行既有 pair validator。可行性證據：validator 與所需 row/time 資料已存在，無需改數值語意。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/split_projection.py#99bfddace904`; `momentum/core/contracts.py#1471cef968a3`

## CODEX-R9-P2-09
**斷言**：`SU-RESID-9A-UI` 的 trigger 雖可由 grep 觀察，卻沒有 owner、權威登記列或 gate/task 使它在後續輪次自動收斂；目前它只出現在 SPEC §N，TODO 仍是五鍵 metadata 舊形狀。這是治理追蹤缺口，不是把尚未接線誤宣稱為已接線。
**碼證**：`rg -n 'SU-RESID-9A-UI|EventSamplePipeline\.run|production.*run' scripts tests api momentum docs --glob '*.py' --glob '*.sh' --glob '*.md'` 只命中 SPEC/brief/handoff 類文字，未命中專門 gate；`rg -n -C 3 'SU-RESID-9A-UI|metadata\.split_unify' docs/SPLITUNIFY_TODO.md` 只見舊 Task 4.1 五鍵契約。修復：在 epic authority/TODO 登記該 residual 的 `為何現在不做`、owner、recheck command 和觸發後續票，並讓完成檢查固定重跑生產 caller 掃描；若不建立 gate，至少把 manual recheck 命令與責任人寫入權威登記。信心：中高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `docs/SPLITUNIFY_TODO.md#e44da6448b01`

K1-K8 / D-001 / golden / residual trigger 的新衝突集中在上述 finding：K1 的 G-4c 仍是共同錯誤可綠；K2 的 Task 9.1 目標與 residual 互斥；K3 引錯 brief 模板；K4 三層方案未決且無 handoff；K5 Step 0 未覆蓋 pair 完整性；K6 baseline 計數前提不成立；K7/K8 的具名測試與 mutation 清單本輪未另發現缺檔或漏號，但它們仍不能補足 G-4d 與 producer→metadata wiring。

ASSUMPTIONS_VERIFIED: 已實跑 golden、obligation block、doc format 與 caller/template/source grep；G-4c、Step 0 exhaustiveness、C6 baseline equality、UI trigger 均有反證或未閉合證據。
TESTS_RUN: `venv/bin/python scripts/freeze_splitunify_golden.py` rc=0（G-3b/G-5/GOLDEN OK）；`bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；其餘 `rg`/`nl` 為唯讀證據命令。
FAILURES_SEEN: none（未修改實作以消除任何測試失敗）。
SCOPE_CHANGES: none；只新增本交件檔，未改 SPEC/TODO/程式碼/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無實際輸出變更；finding P1-05/P1-06 指出計畫中的 `metadata.split_unify` 新欄位與資料流仍需裁決/施工。
TMP_CLEANUP: 已檢查並清理本 task 可辨識的 `/tmp` workdir；未觸碰並保留 `/tmp/claude-501`。
VERDICT: blocked
BLOCKED-BY: CODEX-R9-P1-01,CODEX-R9-P1-02,CODEX-R9-P1-03,CODEX-R9-P1-04,CODEX-R9-P1-05,CODEX-R9-P1-06,CODEX-R9-P1-07,CODEX-R9-P1-08
CLOSED: CODEX-R8-P1-03,CODEX-R8-P1-04
STATUS: DONE
## COMPOSER-R9-P1-01

**斷言**: (G-4c) 宣稱 G-3b 在同步改寫 `_oracle_membership` 後自動成為「換錨 vs 寫錯」區分閘，但**兩份實作可被同步寫入同一錯誤語意**而 G-3b 仍綠，與 R8 allowlist 方案**不等效**。

**碼證**: `freeze_splitunify_golden.py:346-350` 僅 `g1_membership != g3b_oracle`；探針 `venv/bin/python`（`/tmp/composer-r9-g4c-probe.txt`）⇒ `bug=True proj=purged oracle=purged g3b_pass=True correct=train`（`decision=cutoff=train_last=200`）。RECHECK: 重跑探針；對讀 §G L128-129 與 oracle `:133-155`（現仍 cutoff 判側）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。Task 9.2b 實作者若同步 typo，重凍後 golden 固化錯側且 G-3b 全綠。**修法**：G-4c 保留 + 加 allowlist 或 cutoff 平行鍵 diff（R8 三家原案）；G-4d② 寫進 §V 為對 v8 舊鍵之硬 ASSERT。**可行性**：fixture 內 `decision_at_ms`／`feature_cutoff_ms`／`train_last_ms` 皆可讀，set equality 可腳本化（grok R8-P1-01 已論證）。

## COMPOSER-R9-P1-02

**斷言**: K1 採納之 **(G-4d) 三項硬性附帶**僅寫在 §G 散文，**未**落入 §V 或 mutation——實作者可跳過②零位移③單 TF `decision!=cutoff` fixture 而宣稱 G-4 已閉。

**碼證**: §G L129 要求②③；§V `Task 9.2b` L221 僅多 TF 錨定反例，**無** `decision_at_ms != feature_cutoff_ms` 單 TF 案例；`rg 'decision_at_ms != feature_cutoff|零位移|g1_membership_cutoff' docs/SPLITUNIFY_SPEC.D-002.md tests/ scripts/` 除 §G／沿革外 **0 施工面**。mutation 表 L229-256 **無** G-4d 專列。RECHECK: 上述 rg；對讀 L129 vs L216-227。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[BLOCKING] 信心度=High。G-4c 區分閘缺③則換錨改側永不觸發測試；缺②則 off-by-one 可混進重凍。**修法**：§V 增 `Task 9.2b-G4d` 三條 ASSERT + 新 mutation（例 off-by-one 判側、decision!=cutoff 單 TF）；Task 9.5 明寫 v8 鍵保留比對。**可行性**：純 SPEC＋測試派工，無架構阻礙。

## COMPOSER-R9-P1-03

**斷言**: §G L127「任一單 TF 舊值位移即 FAIL」與 (G-4a)／(G-4c)「Task 9.2b 後允許因換錨改側並重凍」**同檔互斥**，第九次修訂未更正 L127。

**碼證**: L127 vs L128-130；換錨必改側之碼證 `test_start=1000,decision=1000,cutoff=900`（§G L130）。RECHECK: `sed -n '127,130p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;momentum/Analysis/event_samples/alignment.py#0da3c48b2668

[BLOCKING] 信心度=High。實作者依 L127 拒絕合法重凍，或依 G-4a 重凍却被 L127 判 FAIL。**修法**：L127 改為「(G-4d) 允許之差異集合內位移除外；其餘 FAIL」；刪「任一…即 FAIL」一刀切。**可行性**：一字級 SPEC 同步。

## COMPOSER-R9-P1-04

**斷言**: K4 在 L149 把 `metadata.split_unify` 第三層成本**再次推遲決策**，但 §V L218／§N L267／`M-SU-D2-03` 仍強制交付該層，屬 R7 J3 同型「二擇一但自己沒擇」。

**碼證**: L149「若成本超出…應改為只交付前兩層」；§V L218 `ASSERT metadata.split_unify 帶該鍵`；`ic_filter_orchestrator.py:1530-1534` 現 caller 不傳 discarded；五處 exact-key 未改。RECHECK: `sed -n '149p;218p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293

[BLOCKING] 信心度=High。Task 9.1 實作者要麼做五處大改（違 9A 低成本），要麼只寫 summary 測試（違 §V）⇒ 假綠或 scope 爆炸。**修法**：**現在定案**採 L149 前兩層-only：刪 §V metadata discarded 斷言、mutation 03 改指 summary、§N 新增 metadata 殘留。**可行性**：R8 已盤點五處；延後第三層比半套 exact-key 安全。

## COMPOSER-R9-P2-01

**斷言**: K3 駁回 composer「blocked-by 須指名票號」時引用 `BRIEF_REVIEW_TEMPLATE.md:71`，該範本**不治理** SPEC §N；且即使類推，`R-BRIEF-1` 亦具名 `committee_run.sh` 而非模糊「架構」。

**碼證**: `templates/BRIEF_REVIEW_TEMPLATE.md:62-72`（表用途＝unverified 未查）；`templates/SPEC_TEMPLATE.md:108-109`（§N 三值 + 具體依賴）；§N L267 引 brief 範本。RECHECK: 對讀三檔上述行。

**來源摘要**: templates/BRIEF_REVIEW_TEMPLATE.md#82dfcbd10f3e;templates/SPEC_TEMPLATE.md#0b2f68f0c38a;docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[MAJOR] 信心度=High。錯誤依據會讓後續殘留都引用 brief 四值閉集，與 SPEC gate 漂移。**修法**：§N `SU-RESID-9A-UI` 改引 `SPEC_TEMPLATE`；`blocked-by:` 後接具名依賴（例 `blocked-by: 投影生產接線 Task（待開）`）或改 `needs-research`。**可行性**：純 SPEC 文案。

## COMPOSER-R9-P2-02

**斷言**: K2 宣稱 `:140` 標題句等四處同批修正，但 `Task 9.1` **目標句 L137 仍要求「終端使用者看得到」**，與 L142「不再列入 9A 完成條件」並存。

**碼證**: `sed -n '137p;142p' docs/SPLITUNIFY_SPEC.D-002.md` → L137 含「終端使用者」；L142 寫 producer-only。RECHECK: 同上。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[MAJOR] 信心度=High。Phase 9A 驗收標準仍讀成終端可見。**修法**：L137 改為「producer 層誠實記錄丟棄列數；終端可見見 §N SU-RESID-9A-UI」。**可行性**：一字級。

## COMPOSER-R9-P2-03

**斷言**: `SU-RESID-9A-UI` 觸發條件（`api/` 出現投影 `run()` 生產呼叫）**無任何機械檢查者或檢查時點**，殘留可永久沉睡。

**碼證**: §N L267 觸發條件；`rg 'SU-RESID-9A-UI|EventSamplePipeline\(\)\.run' scripts/` → 無 gate；`docs/GOV_ENFORCEMENT_REGISTRY.md` 未登記。RECHECK: 上述 rg。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[MAJOR] 信心度=Medium。接線後無人開票解除殘留。**修法**：在 `scripts/` 或 preflight 加 grep 探針：非測試 `api/` 出現 `EventSamplePipeline().run` 且走投影分支 ⇒ fail 並提示開 SU-RESID-9A-UI 解除票。**可行性**：grep 級，成本低。

## COMPOSER-R9-P2-04

**斷言**: K5 採納要求「補 early／late 之 §V 斷言」，但第九次修訂只在 Task 9.2b 規則寫步驟 0，**§V 無** `decision_at_ms=50`／`450` 之 raise 斷言。

**碼證**: R8 synth K5 處置「並補 early/late」；§V L216-227 無界外案例；Task 9.2b L182 有 codex 反例敘述。RECHECK: 對讀 §V 與 L182。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md

[MAJOR] 信心度=High。步驟 0 可被實作者漏實作而無紅測。**修法**：§V 增兩條 ASSERT（decision 早於 index[0]／晚於末列 ⇒ raise，不得進 train/test）。**可行性**：單元測試可構造。

## GROK-R9-P1-01

**斷言**: (G-4c)「同步改寫 `_oracle_membership` 使 G-3b 成區分閘」**不能**取代 allowlist——投影與 oracle 被改成**同一錯誤語意**時 G-3b 仍綠；且 (G-4d)③ 要求的 `decision != cutoff` 邊界 fixture／零位移斷言尚未進入 §V 與 mutation。

**碼證**: SPEC L128 (G-4c)、L129 (G-4d)。`freeze_splitunify_golden.py:133-154`（oracle 用 cutoff；docstring 散文紀律）、`:117`（`decision_at_ms`←`feature_cutoff_ms`）。VERIFY 探針：`gapX` decision=950 cutoff=900 train_last=900 test_start=1000 ⇒ 正確 purged、R6 不等式 train、兩邊同寫時 G-3b 綠且 (G-4d)② 不適用。§V L216-226 無零位移／邊界 fixture ASSERT；mutation 01–26 無對應列。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r9/probe_g4c.txt` 邏輯；`grep -n '零位移\\|decision != cutoff' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中 §G。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。不改則 Task 9.2b 落地＋重凍時，實作者可把「忘記隔離帶」同時寫進投影與 oracle，G-3b 放行，錯誤成員集成為新 golden。(G-4d) 附帶條件若只留在 §G 散文，實作 checklist 掃 §V／mutation 會漏。**修法**：①保留 G-3b 同步改寫（抓不對稱錯）；②**另加**與投影／oracle 皆獨立的第三份判準——以 Task 9.2b 三段式（含步驟 0）從 fixture 欄位純函式算出每事件期望側，ASSERT 投影側與之全等（此即 allowlist／oracle-of-oracle；可內嵌測試、不必新檔）；③§V 具名 `ASSERT decision==cutoff ⇒ 相對 v8 baseline 零位移`、`ASSERT decision!=cutoff 邊界事件側別＝三段式期望`；④mutation 至少一條「只改投影、不改 oracle ⇒ G-3b 紅」＋一條「投影與 oracle 同寫成 R6 不等式 ⇒ 第三份判準紅」。**可行性**：三段式所需 `train_last_ms`／`test_start_ms`／`decision_at_ms`／`feature_cutoff_ms` 皆在 fixture；探針已展示 `gapX` 可區分；現成 G-3b 比對骨架在 `freeze_splitunify_golden.py:346-352` 附近，第三份比對可並列。

## GROK-R9-P1-02

**斷言**: K3 駁回所引 `BRIEF_REVIEW_TEMPLATE` **不適用於 SPEC §N**；§N 權威為 `SPEC_TEMPLATE.md` 之三值＋強制欄 `為何現在不做:`——`SU-RESID-9A-UI` 缺該欄，且條目正文仍錯引 BRIEF 四值當依據。

**碼證**: `templates/SPEC_TEMPLATE.md:107-112`「值**只允許三種**…每條殘留**必須**帶 `為何現在不做:`」；`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:47-50` 審 §N 同三值；`templates/BRIEF_REVIEW_TEMPLATE.md:71` 四值＋`:171` `R-BRIEF-1` 屬 **brief** 殘留。SPEC L267 `SU-RESID-9A-UI`：有觸發條件與 `blocked-by` 字樣，但 `grep`／探針確認**無** `為何現在不做:`；同段括號「類別依據：BRIEF_REVIEW_TEMPLATE…四值」為錯引。RECHECK: `sed -n '107,112p' templates/SPEC_TEMPLATE.md`；`sed -n '267p' docs/SPLITUNIFY_SPEC.D-002.md | grep -c '為何現在不做'` 期望 0。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;templates/SPEC_TEMPLATE.md#0b2f68f0c38a;templates/BRIEF_REVIEW_TEMPLATE.md#82dfcbd10f3e;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa

[BLOCKING] 信心度=High。類別 `blocked-by` 在 SPEC_TEMPLATE「`blocked-by:<具體依賴（檔/層/前置票）>`」下**仍可**形容「投影層無生產接線」——問題不是類別必錯，而是**依據文件引錯＋強制欄缺失**，後續審核會繼續用錯閉集（甚至把 `cost`／`out-of-scope` 寫進 SPEC §N）。**修法**：①L267 刪 BRIEF 四值依據，改引 `SPEC_TEMPLATE.md` §N；②補 `為何現在不做: blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/ 呼叫點=0）`；③若 epic 有權威殘留登記處則同步 pointer（無則於 §N 明寫「登記處＝本 SPEC §N」避免假同步）。**可行性**：純文件同步；零呼叫點事實已多次 grep 實證。

## GROK-R9-P1-03

**斷言**: Task 9.1 L149「若成本超出 9A 定位，應改為只交付前兩層並併入殘留」是**未擇定的二擇一**，與同 Task 已寫死的三層交付、`M-SU-D2-03`、§V `ASSERT metadata.split_unify` 互斥——實作時可合法砍第三層。

**碼證**: L148 本延伸交付含 `metadata.split_unify`；L149 逃逸句；L218 `ASSERT metadata.split_unify 帶該鍵`；mutation L233 `M-SU-D2-03`「summary 帶了但**不傳入** `metadata.split_unify`」。契約現恰五鍵（`split_unify.json` → `n_test,split_authority,boundary_hash,per_symbol_counts,reason`）；加鍵須改契約＋exact-key 測試（L149 前半已承認）。RECHECK: `sed -n '148,149p;218p;233p' docs/SPLITUNIFY_SPEC.D-002.md`；`python3 -c "import json;print(json.load(open('momentum/Analysis/contracts/split_unify.json'))['split_unify_keys'])"`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15

[BLOCKING] 信心度=High。與 R7 J3 同型：規格把決策推給實作者。**修法（擇 A）**：刪除 L149 逃逸句，鎖定三層＋五處同步為 9A 完成條件（與現行 mutation／§V 一致）。**若改擇 B**：同批刪 `M-SU-D2-03`、改 §V、改 L148「本延伸交付」為兩層、第三層併入 `SU-RESID-9A-UI`——不得留逃逸句。**可行性**：擇 A 是刪一句；五處清單與型別已寫好，無未決工程問題需要「實作時再估成本」。

## GROK-R9-P1-04

**斷言**: K2 宣稱「目標句已改」未完成——Task 9.1 L137 仍要求「必須讓**終端使用者**看得到」，與 L142／`SU-RESID-9A-UI`「終端可見性不在 9A 完成條件／使用者仍然看不見」正面衝突。

**碼證**: L137 逐字「且必須讓**終端使用者**看得到」；L142「API 與前端隨 §N 殘留延後，**不再**列入 9A 完成條件」；L267 誠實邊界「靜默丟棄對**終端使用者仍然看不見**」。沿革 L283 只記「`:140` 標題句刪去…」，未提 L137。RECHECK: `sed -n '137,142p;267p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[BLOCKING] 信心度=High。這是 R8 `GROK-R8-P1-02` 的**殘留未閉**（同型「改一處漏一處」）。驗收若讀目標句會要求終端面；讀殘留又禁止做終端面。**修法**：改 L137 為「先消除靜默丟棄之**producer 層**誠實性缺陷（終端可見性見 §N `SU-RESID-9A-UI`）」；全文再 grep「終端使用者看得到／必須讓…看得到」清殘句。**可行性**：一字級目標句修訂；與已落地之 L142／§N／mutation 02–03 同向。

---

