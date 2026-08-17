# Reconcile — 20260817-gap1-x-review-r9

**來源** 20260817-gap1-todoadv-r9-codex.md, 20260817-gap1-todoadv-r9-composer.md, 20260817-gap1-todoadv-r9-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；R9 受限複驗 → TODO R3＋延伸檔 A1-16..A1-18）

三家共 **6 條** canonical ID（codex 3／grok 3／composer 1 sentinel）；下列三群集**引用全部 6 條，0 掉項**。
**收斂軌跡（TODO 側）：R8 22 → R9 5 實質**（另 1 sentinel）；三家 Verdict＝codex／grok「需修補後 Frozen」、
composer「可 Frozen」⇒ **取較嚴版**（三條皆為便宜之文件級修補，無理由留到實作期）。
段 A closure（三家自報＋主委對證）：**R8 22 條中 18 CLOSED、4 PARTIAL**，四條 PARTIAL 皆為
「處置正確但延伸出新一輪之更精細攻擊」（codex P0-01→G1-R9 已具名；P1-05→本輪 J7；P1-08→本輪 J8；P1-09→本輪 J9），
**無**「處置無效」型。
段 B（J1 三條數值 golden＋§V-4 新 mutation＋驗收⑨）：**codex 與 grok 皆獨立實跑重現，數值與主委 receipt 逐位一致**
（composer 以 receipt 對照）⇒ J1 全部 closure，不再列殘留。

### J7 — reporter 例外集合含裸 `ValueError` ⇒ 吞掉呼叫方參數 bug（三方一致，含主委自產）
**引用**: CODEX-R9-P1-02, GROK-R9-P1-01

A1-8 第 4 點之捕獲集合 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)` 與 A1-5 之
「`t_years<=0`／`target_sharpe<=0`／`x>700` ⇒ `ValueError`」**互相打到**：呼叫方傳負 `t_years` 這種
**程式錯誤**會被映射成 `reason="reporter_failed"` 的 2xx 降級（兩家各自實跑：`negative_t_years='reporter_failed'`），
與同一條 A1-8 自己要求之「程式錯誤保留可觀測失敗（`TypeError` ⇒ 5xx）」矛盾。
主委自產版 `CLAUDE-R9-P1-02` 獨立得到同一結論與同一修法 ⇒ 四方一致。

**處置（TODO R3＋A1-16）**：
1. `min_btl.py` 新增 `class InvalidValidationArgument(ValueError)`；Task 3.1 之三處參數驗證（`n_trials<1`／
   `target_sharpe<=0`／`t_years<=0`）與 `max_trials_budget` 之 `x>700` **一律** raise 之
   （仍是 `ValueError` 子類 ⇒ 呼叫方既有 `except ValueError` 語意不變，但可被精準排除）。
2. reporter 捕獲集合**收窄**為 `(OSError, json.JSONDecodeError, ContractViolation)`；
   **`ValueError`／`InvalidValidationArgument` 不捕獲** ⇒ 上拋，由 route 既有 500 路徑處理。
3. reporter **入口語意二分**：`None` ＝「未提供」⇒ 誠實 `unavailable`／`n_unknown`（不呼叫 `assess_eligibility`）；
   「提供了但非法」（`t_years <= 0`／`target_sharpe <= 0`）＝呼叫方 bug ⇒ **不正規化**，交由
   `assess_eligibility` raise `InvalidValidationArgument` 上拋（5xx）。兩者混同＝換一種吞法，意圖落空。
4. Task 3.4 驗收⑤ 擴為 `TypeError` **與** `InvalidValidationArgument` 各一案例，兩者皆須 **5xx**；
   新增⑧「`t_years=-1.0` 由 route 傳入（模擬未來 G1-R1 接線錯誤）⇒ 5xx，不得回 `reporter_failed`」。

### J8 — AST wiring 之死／條件分支假綠（codex MAJOR、grok MINOR；主委探針未覆蓋此形）
**引用**: CODEX-R9-P1-01, GROK-R9-P2-01

A1-11 第 4 點寫「取 `Return` 及其 body 內組裝該 dict 之 `ast.Constant` 鍵」，**未定義可達性**
⇒ `if False:` 內寫滿五節／九鍵可使 W1／W4 集合齊備而 runtime 缺鍵（codex 實跑：
`return_sections` 五節齊、`w4_seen` 九鍵齊、`runtime_eligibility={}`）。
🔴 **主委自產探針之誠實邊界**：`handoffs/run_receipts/20260817T160000Z-gap1-ast-wiring-probe.{py,log}`
只測了 helper／迴圈／`{**a,**b}`／docstring 四形（結論：**無假綠但兩形誤擋**），
**沒測死分支** ⇒ 本條是委員補上的真缺口，主委自產版漏。

**處置（TODO R3＋A1-17）**：
1. W1／W4 之收集範圍**收窄為無條件路徑**：只接受 ① 函式**頂層**（非嵌在 `If`／`For`／`While`／`Try`／`With` body 內）
   之 `Return` 之 `ast.Dict` 字面鍵 ② 函式**頂層**之 `out["<literal>"] = …` 指派 ③ 頂層 `{**a, **b}` 之
   來源 dict 若亦在頂層以字面定義。**凡出現在條件／迴圈／try 內之組裝一律不計入**，因此節名不足 ⇒ rc=1。
2. Task 2.4 新增 **mutation ⑥**：`if False:` 內寫滿五節名（或九個 eligibility 鍵）而 return dict 缺該節
   ⇒ rc=1（死分支假綠回歸鎖）。
3. **配對條款（主委自產 `CLAUDE-R9-P1-01`；閘門選「寧誤擋」則被擋方須有明文可行寫法）**：
   Task 3.3「不可做」新增——`build_validation_section` **禁**以 helper 函式、迴圈變數鍵、
   `setattr`／`dict(**kwargs)` 組裝五節；必須在**自身函式頂層以字面鍵**組裝
   （主委實跑證實此三形皆 `assembled=∅` ⇒ 會誤擋）。
4. Task 2.4「誠實邊界」補一句：本閘只做**語法層無條件路徑**判定，不做 CFG／型別推導；
   Task 3.3 之 `validate_against_contract`（runtime）為第二道防線（grok 據此判 MINOR 之理由，予以保留並具名）。

### J9 — 母 SPEC §R 回退契約與新拓撲矛盾（codex MAJOR、grok MINOR；主委自產同）
**引用**: CODEX-R9-P1-03, GROK-R9-P2-02, COMPOSER-R9-P3-00

母 SPEC:653-654 逐字「B4 依賴 B1+B2，**不依賴 B3** ⇒ B3 與 B4 可獨立 revert」，而 A1-11 把 Task 2.4 移入 B4 末
並使 B4 依賴 B3 Task 3.3（`report.py`）⇒ 保留 B4 而 revert B3 時 wiring 之 AST 標的消失、B4 gate 不成立。
composer 之 sentinel 亦把本條與 J7 記為「段 C 結論、不升 finding」，主委裁定**取較嚴版**（codex）：
延伸檔須具名覆寫 §R，否則冷啟動讀母 SPEC 會做出錯誤回退。

**處置（A1-18）**：延伸檔新增 §R 覆寫條：
1. 依賴：**B4 ⊃ B3**（僅因 Task 2.4 之 wiring 閘讀 `report.py`）；統計核心 4.1–4.3 **不**依賴 B3。
2. revert 順序：**先 B4 再 B3**；若須單獨 revert B3，則同時 revert Task 2.4 之兩個 `scripts/` 檔
   （或接受 wiring rc=2 並於 receipt 具名）。
3. 明示**不採**之替代案（codex 提及）：把 wiring 拆成 B4 之後的獨立 post-B4 phase——理由＝
   會多一個批次與一輪 review，而雙向獨立 revert 在本票無實際需求（新模組無既有 caller，
   §R 之價值在「壞了能退」而非「任意順序退」）。

### 收斂結論（主委）
- 6 條全數處置（0 掉項）；三群集 J7／J8／J9 皆為**文件級修補**，不動已定案之統計契約與數值 golden。
- **J1 三條數值處置經兩家獨立實跑重現** ⇒ 本 epic 之 §G／§V golden 自此有 receipt 支撐（R8 前七輪皆無）。
- 淨變動：延伸檔 **A1-16／17／18**（新增 3 條，A1 共 18 條）；TODO R3 動 Task 2.4／3.1／3.3／3.4 四處；
  新增例外類別 `InvalidValidationArgument`；Task 2.4 mutation 5 條 → **6 條**；Task 3.4 驗收 7 項 → **8 項**。
- **不再派新一輪 adversarial**：三條修法皆由委員逐字指定（非主委自創），且可 grep 驗證；
  改以 **r9 戳記輪之核可判準夾帶「三條修補落地」之機械檢查**（同 r8 戳記輪之作法，brief 明列 grep 條件）。
  依據＝「95% 解法就收＋殘留具名」與「精確≠便宜」：此處不是免審，是把驗證放進**必跑的**戳記關卡。
- **Frozen 條件**：r9 收斂檔三家 RECONCILE-STAMP APPROVED（含三條修補之 grep 核可）⇒ TODO 標 **Frozen**，
  隨即開工 B1。

**Verdict**: 需修補後合併 → 修補落 TODO R3＋A1-16..A1-18，經 r9 戳記輪（含落地機械核可）後 Frozen。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R9-P1-01

**斷言**: Task 2.4 的 AST W1/W4 仍可被條件／死分支中的 `ast.Dict` 常數假性滿足，讓 wiring check rc=0 而實際 `build_validation_section` 回傳缺少 eligibility keys 的報告。

**碼證**: TODO:425-434 宣稱掃 Return 與 function body 的 Constant 鍵且「dead branch 之字面不再造成假綠」，但未定義控制流或可達性分析。實跑等價 probe：`return_sections=['eligibility','min_btl','dsr','pbo','provenance']`、`w4_seen` 含九鍵、`runtime_eligibility={}`；因此上述 snippet 會通過集合子集檢查而 runtime contract 不完整。RECHECK：以同 snippet 加入 `if False` 或未涵蓋的 `if flag`，跑該 probe 或 Task 2.4 scanner，確認 gate 靜態集合仍齊而回傳 dict 缺鍵。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e6d673841704

[MAJOR] 信心度=High；helper／loop／unpack／setattr 多數是 fail-closed 誤擋，但死／條件分支是可執行假綠。修法：做可達性／資料流封閉分析，或明確禁止 indirect/control-flow assembly 並對這些 mutation 強制 rc=1；加一條實際回傳缺鍵但靜態鍵齊全的 mutation。現有 24 案例可擋被測到的 runtime 缺鍵，但不能替代 wiring gate 的閉包。

## CODEX-R9-P1-02

**斷言**: A1-8 的 reporter 捕獲集合含裸 `ValueError`，因此 `assess_eligibility` 的呼叫方參數錯誤會被誤報為 `reporter_failed`，而非暴露程式 bug。

**碼證**: TODO:235-240 將 `t_years<=0`／`target_sharpe<=0` 定義為參數驗證 `ValueError`；TODO:319-324 又要求捕獲 `ValueError` 並回 `reporter_failed`，只把 TypeError/AttributeError/KeyError 上拋。等價實跑命令輸出 `negative_t_years='reporter_failed'` rc=0，證明此類 bug 可進降級 2xx 路徑。RECHECK：對 `for_study_trial(..., dataset_key='k', t_years=-1.0, target_sharpe=1.0)` 的 `assess_eligibility` 注入負值，觀察 reporter reason。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#44556a29f5c1

[MAJOR] 信心度=High；這會把不合法輸入與可預期資料不可用混同，造成錯誤被吞且 API 狀態不可觀測。修法：移除裸 `ValueError`，或讓參數驗證使用不在 catch tuple 的專用 `InvalidReporterArgument`；只捕獲明確的 ledger／JSON／I/O data failure，保留 `logger.error(..., exc_info=True)`。

## CODEX-R9-P1-03

**斷言**: R2 把 Task 2.4 移到 B4 末並加入 B3 Task 3.3 依賴後，母 SPEC §R 仍宣稱 B3/B4 可獨立 revert，形成未解的拓撲／回退契約矛盾。

**碼證**: TODO:49、51-58 及 A1-11:184-187 明定 B4 依賴 B3 `report.py`；母 SPEC:650-654 仍逐字寫「B4 ... 不依賴 B3」並推出「B3 與 B4 可獨立 revert」。實際保留 B4 而回退 B3 時，wiring 的 AST target 不存在，B4 gate 不能成立。RECHECK：`rg -n 'B4.*不依賴 B3|可獨立 revert|B3 Task 3.3|B4.*B3' docs/GAP1_STRATEGY_OVERFIT_{SPEC,TODO,AMENDMENTS}.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=High；不是要求改回不可達的 B2 落點。修法：在 A1-11 明確覆寫 §R，紀錄 B4→B3 的依賴與「先 revert B4、再 revert B3」順序；若必須維持雙向獨立回退，將 wiring gate 拆成 B4 之外的 post-B4 commit／phase。

## COMPOSER-R9-P3-00

**斷言**: 本輪對 R8 本家族三條 closure、J1 五項數值 oracle、段 C 五類新增機制攻擊面逐項核對後，無達 BLOCKING／MAJOR 門檻之可證偽缺陷。

**碼證**: 段 A 表三 ID 皆 CLOSED；段 B 表五項實跑 PASS（命令見檔首 VERIFY）；段 C-1 `composer-r9-ast-probe.py` 五模式皆 rc=1；段 C-2–5 對照 `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` A1-4／A1-7／A1-8／A1-11 與 TODO Task 2.2–3.4／2.4。RECHECK：`venv/bin/python /tmp/workdir/composer-r9-b-probe.py`；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-todoadv-r9-composer.md --family composer`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-review-r8/synth.md#32271ad1ccab

[NON-BLOCKING] 信心度=High。§R 漂移（C-5）與 `ValueError` 邊界（C-3）已記於段 C 結論，不構成新 finding；勿為湊數捏造實質缺陷。

---

## GROK-R9-P1-01

**斷言**: A1-8／Task 3.4 將 `ValueError` 列入 reporter 捕獲集合，會使 `assess_eligibility`（及 `max_trials_budget`）的參數驗證 raise 被映射為 `reason=reporter_failed` 的 2xx 降級，而非可觀測的程式／呼叫錯誤。

**碼證**: A1-8 第 4 點與 TODO:319-324 捕獲 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)`；TODO:237 參數驗證 `t_years<=0`／`n_trials<1`／`target_sharpe<=0` ⇒ `ValueError`；TODO:238 `x>700` ⇒ `ValueError`。本輪：`assess_eligibility(t_years=-1.0, …)` 落入 `except ValueError` → `("reporter_failed", "ValueError")`。RECHECK：對讀 A1-8 與 TODO 3.1／3.4；用最小 try/except 重跑上式。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#44556a29f5c1

[MAJOR] 信心度=High。會怎麼失敗：G1-R1 接上後 route 傳錯 `t_years`／錯誤組裝 optional 時，API 測試仍 2xx＋`reporter_failed`，與驗收⑤「`TypeError`⇒5xx」的 fail-closed 精神不一致，且掩蓋 bug。修法：自訂非 `ValueError` 之 param 例外並排除於捕獲元組；或入口把非法參轉 typed `unavailable` 而讓真正的 `ValueError` 來自非預期路徑時改記 metric 後重拋。不影響 B1–B4 純函式數值路徑。

---

## GROK-R9-P2-01

**斷言**: Task 2.4 W1 若對 `build_validation_section` body 做無控制流之 Constant 鍵收集，死分支內的完整 `ast.Dict` 可使契約節名集合被視為已組裝，造成 wiring rc=0 假綠。

**碼證**: TODO:425-428 寫 Return 之 Dict 鍵＋「body 內對該回傳 dict 之 Constant 鍵指派」，未要求 CFG／可達性分析；mutation ④只覆蓋註解／docstring。本輪 AST 探針：`out={"only_runtime":1}; if False: out={五節…}; return out` → 收集鍵 ⊇ `{eligibility,min_btl,dsr,pbo,provenance}`。RECHECK：對 `ast.parse` 該片段 walk `ast.Dict` 的 `Constant` 鍵。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e6d673841704

[MINOR] 信心度=Medium-High（取決於實作是否做 name→dict 資料流而無 CFG）。運行時 `validate_against_contract`（Task 3.3）仍是第二道防線，故不升 MAJOR。修法：W1 只接受**無條件**組裝路徑，或新增 mutation ⑥「`if False:` 內寫滿節名 ⇒ rc=1」；文件誠實邊界加「不保證排除死分支」。

---

## GROK-R9-P2-02

**斷言**: A1-11 使 B4 依賴 B3 Task 3.3 後，母 SPEC §R「B3／B4 可獨立 revert」已失效，但延伸檔未具名改寫 §R，留下回退敘事漂移。

**碼證**: 母 SPEC:653-654「B4 依賴 B1+B2，不依賴 B3 ⇒ B3 與 B4 可獨立 revert」；A1-11 第 1–2 點與 TODO:49、51-53 改為 B4 依賴 B3 3.3；A1 全文無 §R 條目。RECHECK：`grep -n '獨立 revert\|不依賴 B3' docs/GAP1_STRATEGY_OVERFIT_{SPEC,AMENDMENTS,TODO}.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MINOR] 信心度=High。不造成 B1–B4 數值錯；冷啟動以 TODO 為準可避開。修法：A1 增一條改 §R（可單獨 revert B4；revert B3 須連動 2.4／接受 wiring 紅）。**勿**把 2.4 移回 B2。

---


## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。

RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9 task:20260817-GAP1-X-STAMP-R10

RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9 task:20260817-GAP1-X-STAMP-R10
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9 task:20260817-GAP1-X-STAMP-R10
