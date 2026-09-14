# HANDOFF — 當前任務狀態

**更新：2026-09-13｜現行 topic：SPLITUNIFY b9 復工**。DOCROT／CXSTAMP 已結票（三家戳記、無欠債），**不重開**。本 session 進度：①開工稽核抓到 HANDOFF 一處過時（原寫「四個測試檔」，實為 **2** 個）並更正；②派 `20260911-splitunify-b9-consult-r2` 三家裁定未 commit 生產碼去留——**composer／grok 皆判 `REVERT`，codex 依 `AGENTS.md:40` Rule 12 判 blocked（不裁）**；收斂 `handoffs/reconcile/20260911-splitunify-b9-consult-r2/synth.md`（10 findings 全歸戶、completeness PASS、`debt_clear` rc=0）；③**REVERT 已執行**（四檔 ＋ staged 的 `handoffs/20260911-splitunify-b9-probe-multitf.py` 全還原至 HEAD，備份在 scratchpad 之 `b9_reverted_worktree.patch`），重跑 `test_splitunify_derive.py`＋`test_splitunify_wiring.py` 得 **87 passed／0 failed**；④**`docs/SPLITUNIFY_TODO.md` 已補 `§B` 之 `B9A`–`B9F` 與 `§C-9` 之 `Task 9.1`–`9.5`**（`doc_format_precheck` rc=0、`spec_xref_check --synth` rc=0／18 概念同步）；⑤**戳記輪 `20260911-splitunify-b9-stamp-r1` 完成**——三家皆 APPROVED，`reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **PASS**（十三輪來第一次）；同輪 codex 對 §C-9 提四條 P1（`VERDICT: blocked`）、grok 一條 P2，**五條全採納並已修**；收斂 `.../20260911-splitunify-b9-stamp-r1/synth.md`，`debt_clear` rc=0。⑥**review-r13 完成（＝DOCROT 成效量測第一輪）**：stamp-r1 五條 finding **全數由原提出方 CLOSED**；composer／grok 零 finding proceed；codex 新開兩條 P1＋一條 P2，**全採納並已修**——T1 `C5-20` 之 mutation 錯配（另主委同型自查補 `C5-21`）⇒ 新增 `M-SU-D2-35`／`M-SU-D2-36`、條數 34→**36**、SPEC 進 **v14**；T2 `Task 9.3` receipt 閘只比行數可被繞過 ⇒ 改 exact ID set ＋ TASK／COMMIT 綁定；T3 `B9D` 描述與表列列數不符 ⇒ 逐列具名。**`doc_friction_ratio` = 0/5 = 0.00，finding 總數 5（≤20）⇒ 第一輪達標**。🔴 **T1 使 SPEC body 變更 ⇒ v13 之三家戳記失效**，新 body sha256 `7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2` 須重簽。⑦**review-r14 完成（＝DOCROT 量測第二輪）**：r13 三條全數由 codex CLOSED；但**逐列窮舉揭出一整類存量缺陷**——register 之 mutation 欄再有**五列**錯配（`C5-24`／`25`／`27`／`29` 改指或補掛、`C5-28` 之 `—` 經複驗確為刻意並已具名 `blocked-by`），新增 `M-SU-D2-37`..`40`、條數 36→**40**、SPEC 進 **v15**；另兩類：`M-SU-D2-35`／`36` 應紅欄可被 `in df.columns` 軟包短路（兩家撞題，已加欄位存在斷言＋軟包禁令＋多 TF fixture）、`Task 9.3` receipt 閘可用「分類全填同值＋占位碼證＋任意 COMMIT」假完成（三家撞題，已加改前分類對證 SPEC 現況、碼證 path:line 須真實存在、COMMIT 須等於 audit 之 round-start HEAD）。🔴 **`C5-01`..`29` 之逐列核對已窮舉完成**（三家獨立確認 `C5-01`..`23`／`C5-26` 無誤），此類存量到此為止。**DOCROT 兩輪皆達標**：r13 = 0/5、r14 = 0/10（現行判準）；若採 codex 提議之加強字面集合則 r13 = 1/5 = 0.20、r14 = 0/10，兩種判準下皆 ≤0.30 且每輪 ≤20。🔴 **誠實邊界**：本輪十條有七條屬「指標指錯／閘不夠緊」，那是**另一種**文檔病，現行 `doc_friction_ratio` 完全量不到；「0.00」只證明 DOCROT 針對的那一種病沒再發作，**不等於**文件健康。⑧**review-r15 完成**：U1–U3 全數由原提出方 CLOSED（codex 3／composer 2／grok 4）；composer／grok 對 v15 body APPROVED、codex REJECTED 並開四條 P1——🔴 **四條全打在主委 v15 自己新增的 mutation 上，其中兩條是空殼**：`M-SU-D2-38` 被測輸入**不可達**（`ic_feed.py:109` 單一 TF 過濾、`WindowRow` 只有事件級欄位，主委實讀確認）、`M-SU-D2-40` 破壞描述**與 pandas 實際行為不符**（重複索引 `reindex` 直接 `ValueError`，非靜默取錯值，主委實跑確認）；另 `M-SU-D2-39` 只有門檻斷言無計數斷言、receipt 閘之碼證檢查只驗「存在」故每列填同一真實行仍全過。**四條全採納並修完**，SPEC 進 **v16**，條數維持 40。🔴 **教訓已入沿革**：日後新增 mutation **必須先驗可執行性**（實讀 seam 或實跑一次），不得只憑描述——這與本檔一路在打的「指向不存在的落點」同型，只是犯在 mutation 欄。**收斂判斷（三家）**：composer 判「已進入窮舉遞減報酬」並給停輪判準——**R16 若再出 register 錯配或條數不一致 ⇒ 停輪回報使用者；若只剩 P2 級字面 ⇒ 進 impl 並於 `Task 9.3` 驗收補洞**；grok 以「同缺陷類在已宣告窮舉子空間的復發次數」計，對應維本輪 **0 復發**。主委逐字採 composer 版判準。⑨**review-r16 完成 ⇒ 🔴 停輪判準觸發、三家歸類分裂、已回報使用者（等裁定）**。V1–V5 中四條 CLOSED，唯一 STILL-OPEN ＝ `CODEX-R15-P1-01`（本輪化為 W1）。**W1**：主委 v16 寫的「逐列 keyed 碼證對證」**實測在 29 列中的 20 列跑不動**（消費面欄無 `path:line`）⇒ 是**假閘**。處置＝**收窄而非補齊**：9 個有錨列走精確 keyed、其餘走 basename 封閉判準；補齊 20 列 `TARGETS:` 降級為具名殘留 **`SU-RESID-C5-TARGETS`**（`blocked-by`；codex 逐字修法已原樣錄入，觸發條件＝`Task 9.3` 開工時 basename 判準誤判）。**W2**：`C5-25` 施工點與 `M-SU-D2-38` 破壞點不同行 ⇒ 具名 seam `ic_feed.py:56-65` 並明定去重須在 seam 內；無錨列 20→**19**。SPEC 進 **v17**，條數維持 40、register 29。新 body sha256 `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0` 待重簽。
⑩**使用者 2026-09-13 逐字裁定：「技術問題, 你們委員會共識決。我無法給出答案」** ⇒ 派 **review-r17** 共識決輪（brief 內補上三家在 r16 都沒拿到的 `HANDOFF.md:32` 使用者裁定原文，並明文禁止把球踢回使用者）。**結果：composer `PROCEED`／grok `PROCEED`／codex `FIX-FIRST` ⇒ 採 `PROCEED`**。🔴 **依據不是數人頭**：兩家均引該裁定並說明適用；而 **codex 自己在必答 1b 寫下退讓條件逐字「若本立場不採，至少保留 `SU-RESID-C5-TARGETS` 並把這 15 個 ID 具名化」——該條件已於本輪全額滿足** ⇒ 三家在實質處置上其實無分歧。
- **r17 另抓三條，三家撞題，全採納並修完**：**X1** 收窄後的 basename 判準對 **15 列**仍不可執行（三家各自算出同一組，與主委機械掃描逐字一致）⇒ `Task 9.3` 驗收第 5 點改**三段式、29 列互斥窮盡**：(甲) 10 列精確 keyed／(乙) 4 列 basename／(丙) **15 列明文排除**（`C5-01`..`C5-12`／`C5-20`／`C5-22`／`C5-24`，碼證欄填 `NO-ANCHOR`）；**X2** 殘留觸發條件無機械觀測（無判定人／無命令）⇒ 改兩條客觀事件＋owner＋時機；**X3** 「9 列／20 列」字面在同輪補 `C5-25` 錨後已過期 ⇒ 同步為 10／4／15。🔴 X3 正是本檔一路在打的「改 A 沒同步 B」，這次是主委在同一輪內自己造成的。
- 🔴 **具名殘留 `SU-RESID-C5-TARGETS`（不得讀作已解決）**：(丙) 那 15 列之 receipt **碼證欄不受機械對證保護**，只靠分類欄對證 SPEC 現況；理由類別 `blocked-by`，觸發條件與 owner 見 TODO `Task 9.3` 該段。
⑪**stamp-r2（codex 單家閉合＋重簽）完成 ⇒ 🏁 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **rc=0，三家全數 APPROVED 且雜湊相符**（body `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`）。本檔自 R1 起十七輪，至此首次取得完整且有效之三家戳記**。codex 之 `CODEX-R17-P1-01`／`P1-02` 由原提出方 CLOSED；另提一條 P2 亦已修——`SU-RESID-C5-TARGETS` 殘留段仍寫「20 列」（`C5-25` 補錨後應為 **19**），並給出 (乙) 4 列之逐字 ID `C5-15`／`C5-16`／`C5-17`／`C5-18`（主委機械複驗四列皆「有檔名、無行號」屬實）。🔴 **同一個「改 A 沒同步 B」第三次**：`C5-25` 補錨這**一個動作**先後打翻驗收第 5 點的「9／20」（r17 X3）與殘留段的「20」（本條），兩次落在不同行。
⑫**stamp-r3 三家零 finding APPROVED** ⇒ stamp-r2 收斂檔取得三家戳記（body `3f3d0d79…`、`reconcile_stamps_check` rc=0），作為 impl token 之 `--adversarial` 授權依據。三家並各自確認 `Task 9.1` 施工條文可直接開工、無未解歧義，亦無一家主張授權依據應改指 r17 收斂檔。
⑬🔴 **`Task 9.1`（B9A）已實作完成**（impl token `20260911-SPLITUNIFY-B9-IMPL-T91`）：
  - `build_event_keys` 回傳改為 `(keyed, discarded)`；`discarded` 之鍵為被單選濾掉之 feature TF 字面、值為列數，無丟棄時為 `{}`。**單選行為與 `selected_timeframe` 必填性皆未動**（改可選全量是 `Task 9.2`）。
  - `_derive_single_symbol`／多 symbol 分派器新增 keyword-only `discarded_rows_by_feature_tf`，**原樣**寫入 `EventSplitPlan.summary["discarded_rows_by_feature_tf"]`；`_build_summary` 由 12 鍵增為 **13 鍵**。
  - `pipeline.py` caller 同批改為 unpack 兩值並沿用傳遞。
  - 測試：四條具名測試全補（`test_build_event_keys_discarded_counts_dropped_feature_tf`／`..._empty_when_single_feature_tf`／`test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer`／`test_discarded_layer_is_independently_revertible`）；既有 `test_summary_has_all_twelve_keys` 依 13 鍵更名並改斷言。
  - **實跑**：`tests/momentum/Analysis/test_splitunify_derive.py` ＋ `tests/momentum/event_samples/` ＋ golden ＋ contract ＋ `tests/api/test_splitunify_disclosure.py` ＋ `..._event_study_only.py` 合計 **692 passed、0 failed**。
  - **mutation 自證（實跑）**：`M-SU-D2-01`（刪 summary 寫入行）⇒ **3 failed**；`M-SU-D2-02`（`_derive_single_symbol` 改傳 `{}`）⇒ **1 failed**（由**值相等**斷言抓到；只驗鍵存在會漏）。兩者皆已還原。
- 🔴 **與 TODO 條文之具名偏離（交審碼輪裁）**：TODO `Task 9.1` 實作要點 2 寫「多 symbol 分派器逐 symbol **相加**」，但實際呼叫圖中 `build_event_keys` 是**對整批 `receipts.per_tf` 呼叫一次**（`pipeline.py` 單一呼叫點），`discarded` 為批次級、不存在逐 symbol 分量 ⇒ 實作採**原樣傳遞**，若照字面相加會**重複計數**。已於碼中具名註記。
⑭**review-r18（首輪審「程式碼」）完成，六群全採納並修完**——逐群內容、回歸命令與筆數、每條新測試之破壞驗鑑別力紀錄，**唯一權威＝`handoffs/reconcile/20260911-splitunify-b9-review-r18/synth.md`**（本檔不複述數字）：
  - **A1（grok，P1）生產接線可靜默失效**——四條具名測試全在 `derive_*` 層，`pipeline.py` 省略 `discarded_rows_by_feature_tf=` 則全部仍綠 ⇒ 新增掛在 `EventSamplePipeline.run` 上的 wiring 測試。
  - **A2（三家）多 symbol 分支無具名測試** ⇒ 新增值相等＋**防放大**測試。
  - **A3（兩家，P1）`timeframe` 缺值會被記成假 TF `nan`** ⇒ 計數前 `isna` fail-closed。
  - **A4（三家，P1）探針檔未隨二值回傳更新**——🔴 **根因是主委自己造成**：consult-r2 REVERT 時把該探針一併還原到單值形態，Task 9.1 改簽章後就壞了，**回退與前進之間漏了這一步**。
  - **A5（兩家）TODO「逐 symbol 相加」與資料流互斥** ⇒ 兩家一致判「實作對、條文錯」，TODO 改「原樣傳遞、不得相加」。
  - **A6（兩家）`_build_summary` docstring 仍寫 12 鍵且引用不存在行號** ⇒ 改 13 鍵並明寫鍵數權威是 exact-set 斷言。
- 🔴 **本輪最值得記的一件事**：主委在 brief 自標的兩條 assumed（多 symbol 相加、`value_counts` 之 dtype 陷阱）**兩條都被證實為真問題**，A1 之「第三種破壞」也是主委自己問出來的 ⇒ **把沒把握的面寫進 brief 交出去攻，比自己再讀一遍有效**。
⑮**review-r19 完成**：**r18 之十三條 finding 全數由原提出方 CLOSED**（codex 五／composer 三／grok 五）；composer／grok 零 finding proceed。主委自標的兩條 assumed 皆由 codex 實跑**否證為無問題**——`Categorical`／`StringDtype` 下不會混入值為 0 之偽項；**無第二條生產路徑**（全 repo 掃 `build_event_keys` 只有 `pipeline.py` 一處，另三處在 `scripts/freeze_splitunify_golden.py` 屬 golden 工具）。
  - 🔴 **codex 一條新 P1（`CODEX-R19-P1-01`）已修**：**SPEC 之 `§P Task 9.1` 落後於自己的 §V 與實作**，兩處互斥字面——①仍寫「producer → summary → `metadata.split_unify` **三層**」（v13 之 O1 已把 metadata 移入 §N 殘留、§V 已同步，**只有 §P 沒改**）；②仍寫「多 symbol **逐 symbol 相加**」（R18 已定案原樣傳遞）。**SPEC 是權威**，下一輪實作者依 §P 會引入 double-count。兩處已同步、SPEC 進 **v18**。
  - 🔴 **教訓**：v13 改 §V 沒改 §P，與本檔一路在打的「一個決定散在多區段而漏同步」**完全同型**，隔了五輪、直到實作完成才被逼出來 ⇒ **文件層自證掃不到「§P 與 §V 互斥」這種跨區段矛盾，實作才掃得到**；反證 r12 停輪判準「殘餘規格缺陷交由實作期暴露」是對的。
⑯**stamp-r4 三家零 finding APPROVED** ⇒ `reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **rc=0**（v18，body `76006a76…`）。三家並各自回答主委自標之兩條 assumed：`§P Task 9.1` 與 `§V Task 9.1` 逐句對讀**無第三處互斥**；`Task 9.2`–`9.5` **無條文引用被改掉的舊字面**。
🏁 **`Task 9.1`（批次 `B9A`）完整收束**：實作 → 首輪審碼 6 群修補 → 閉合再驗證 13 條全關 → SPEC 同步 → 重簽 rc=0。
⑰🔴 **`Task 9.2` ＋ `Task 9.2a`（批次 B9B）已實作**——本批是**第 9 批核心**（沒有它，下游全改完 `SU-RESID-2` 仍不解決）。回歸與 mutation 實跑結果見 `handoffs/reconcile/20260911-splitunify-b9-review-r20/synth.md`（待建），receipt `20260913T165740Z-splitunify-b9b-task92-92a`。
  - **`Task 9.2`（四層，缺一層即白做）**：①producer `selected_timeframe` 改 `Optional[str] = None`、`None`＝全量；②caller 移除 `str()` 強制轉型（留著會把 `None` 變字面 `"None"`）；③`pipeline.py` 投影門檻由**四鍵改三鍵**（`selected_timeframe` 移出必填集合）＋docstring 同步；④merge 改以 `per_tf` 為行粒度、`validate` 由 `1:1` 改 `many_to_one`，**新建** `feature_timeframe` 欄取自 `per_tf`（不得以 `event_level.timeframe` 冒充）。
  - **`Task 9.2a`**：`assignments`／`purged` 兩表加 `feature_timeframe` 欄（含**空批欄集一致**）；兩道 guard 判準改 `(event_id, feature_timeframe)` 複合鍵唯一、**錯誤型別維持 `ValueError`**；`manifest.table` 維持事件級唯一；`clusters` **不加該欄**；summary 增 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 三鍵（12→**16** 鍵）。
  - **三條 TODO 明文指定之既有測試處置**：`test_summary_has_all_thirteen_keys`→`..._sixteen_keys`；`test_duplicate_event_id_is_fail_closed` 之 `match=` 改「複合鍵重複」（裁定＝測試過時，不得改實作）；`test_splitunify_wiring_partial_boundary_is_fail_closed` 之 `selected_timeframe` 參數化案例**替換**為 `test_partial_boundary_gate_accepts_none_selected_timeframe`（不得只新增而留舊的）。
  - **`scripts/freeze_splitunify_golden.py`** 之 fixture 補 `feature_timeframe`（**刻意維持單 feature TF** ⇒ golden 既有值逐值不變；擴維屬 `Task 9.5`）。
  - **mutation 自證（實跑後皆還原）**：`M-SU-D2-20`（producer 保留預設單選）⇒ 紅；`M-SU-D2-21`（門檻改回四鍵）⇒ 2 紅；`M-SU-D2-23`（`validate` 改回 `1:1`）⇒ 2 紅；`M-SU-D2-26`（以 `event_level.timeframe` 冒充）⇒ 紅；`M-SU-D2-36`（`purged` 不寫該欄）⇒ 紅。
⑱**review-r20（B9B 審碼）完成，三家全 blocked、撞同兩題，全採納並修完**——逐群內容、回歸筆數與破壞驗鑑別力紀錄，**唯一權威＝`handoffs/reconcile/20260911-splitunify-b9-review-r20/synth.md`**（本檔不複述數字）：
  - **D1（三家 P1）🔴 主委真漏**：`Task 9.2a` 機械驗收第 6 條之逐字錨點測試 `test_multi_feature_tf_opposite_sides_must_fail_closed` **整段缺席**——它在 consult-r2 裁定「整批 REVERT」時隨偷跑碼一起消失，而 `Task 9.2a` 實作時沒補回，**等同刪測換綠**，且使 `Task 9.2b` 失去可解除之 xfail 標的。已依 consult-r2 之三重問題裁定重建（fixture 改事件級 manifest、以 `xfail(strict=True)` 明示）。
  - **D2（三家 P2）**：多 symbol 分支三計數無具名測試，省略 kwargs 後 summary 會靜默變 0 ⇒ 新增 `test_multi_symbol_branch_summary_counts_are_named`（逐值＋**明文擋 0 值**）。
  - 三家另否證主委兩條 assumed：golden 11 頂層鍵 `cmp` **逐位元組未變**；NaN 全欄 fail-closed **為預期**（不修）；cutoff 不同之多 TF **確會混態**但**屬 `Task 9.2b`**、本批不加第二份判側邏輯。
- 🔴 **根因值得記（同一病第二次）**：`Task 9.1` 的 A4（探針檔沒跟著改）與本輪 D1（xfail 錨點沒補回）**是同一根因的兩次發作**——consult-r2 的「整批 REVERT」把東西一起還原了，而前進時**沒有逐項檢查「回退掉的哪些需要重建」**。⇒ 日後凡整批回退，須同時產出「回退清單 vs 需重建清單」對照。本輪已順手補掉 codex 掃出的第三個同型漏網（`handoffs/20260911-probe-splitunify-negative-injection.py`），不留第三次。
⑲**review-r21 完成**：**r20 六條全數由原提出方 CLOSED**；composer／grok 零 finding proceed；codex 兩條新 P1 **全採納並修完**（`handoffs/reconcile/20260911-splitunify-b9-review-r21/synth.md`）：
  - **E1**：xfail 錨點測試原寫 `pytest.raises(Exception, match=...)` **太寬**——①任何例外都算 xfail 過（連 fixture 自己壞掉）②`Task 9.2b` 落地時錯誤型別仍可被誤收。已收緊為 `AlignmentViolationError`（`momentum/core/contracts.py:933`，已存在）＋ match `e_x`。⇒ 9.2b 若用別型別或不帶 `event_id`，本測試**繼續紅**而非變 XPASS。**這正是主委在 brief assumed 自問的那條，該家判「是」並補出第二個理由。**
  - **E2🔴 「文件舊段落落後於新實作」第三次發作**（R19 兩次在 SPEC、本次在 TODO）：`Task 2.2` 仍寫單選／每事件一列／12 鍵，後續實作者依舊段會**回退已完成行為**。三處已標 SUPERSEDED 並保留原字面。**主委同型自查另補一處該家沒點名的**：§E 之 `SU-RESID-2` 描述的正是 B9B 剛解掉的東西 ⇒ 已標**已關閉（2026-09-14，批次 B9B）**。
- 🔴 **教訓（三次同形）**：凡改動契約面（簽章／預設值／鍵集／唯一性判準），須**全檔掃該契約的舊描述**並逐處標 superseded，不能只改當前 Task 段。
⑳**review-r22 完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r22/synth.md` ＝唯一權威）：r21 之 E1／E2 由原提出方 CLOSED；composer／grok 零 finding proceed；codex 三條新 P1 **全採納並修完**：
  - **F1**：`SU-RESID-2` 只能標「**部分關閉**」——producer／schema 面確由 B9B 關閉，但該殘留原文寫的是「複合鍵要連 `EventSplitPlan` 之**下游**一起改」，下游＝`Task 9.3` 九處消費面與 `Task 9.2b` 側別錨定，**皆未實作** ⇒ 只完成一半。TODO §E 與 SPEC §N 同名條目已改為部分關閉、理由類別回 `blocked-by`。🔴 **⑲ 那句「已關閉」是主委自己多寫的，本輪被打回。**
  - **F2**：`Task 2.3` 之 golden「只比 `event_id` 集合」未標 superseded——`Task 9.2a` 後行粒度已升為複合鍵，只比 `event_id` 會**吃掉多 feature TF 維度**（mutation `M-SU-D2-16` 正是在打這句）。已標 SUPERSEDED 指向 `Task 9.5`，並註明 B9B 刻意未動 golden、凍結腳本維持單一 feature TF，故該句**在單 TF 下仍成立**（跨批過渡，非現行缺陷）。
  - **F3🔴 「改了新段落、沒回頭標舊段落」第四次發作，且在 SPEC**：①`§P Task 9.1` 之「本延伸交付」bullet 仍含「於 `metadata.split_unify` 擴充回傳結構」，與**同一 Task** 已於 v18 改成「producer → summary **兩層**」的目標句互斥（v18 改了目標句與跨邊界句，唯獨漏這一句）；②§N 之 `SU-RESID-2` 仍寫「TODO 該列仍為 `needs-research`…須於 `Task 9.1` 動工前同步」，該同步早於 B9B 完成。兩處已改、字面保留供追溯。**SPEC 進 v19**，新 body sha256 `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`，**v18 三家戳記失效須重簽**。
  - 回歸 **706 passed、1 xfailed**；completeness／cluster-attribution／`spec_xref --synth` 皆 rc=0，`debt_clear` rc=0。
- 🔴 **本輪三條全部是主委在 brief 自標的疑慮（assumed ×2 ＋ 攻擊面 ×1）被逐一證實，且已連續第三輪如此（R18／R21／R22）** ⇒ 把沒把握的面寫進 brief 交出去攻，命中率極高，維持此做法。
- 🔴 **新增機制**：契約面改動之後，**下一輪 brief 必須明列「請掃 SPEC 與 TODO 的其他舊段」為必答**，不靠主委自己記得。
㉑**review-r23 完成（`handoffs/reconcile/20260911-splitunify-b9-review-r23/synth.md`）：composer／grok 零 finding proceed ＋ 對 v19 body APPROVED 並 append 戳記（provenance 已由主委 `register-output --kind stamp --family <fam>` 補記）；🔴 codex 以 `AGENTS.md` Rule 12 拒審整輪，主委具名駁回**：
  - **三項駁回依據**：①Rule 12 逐字管的是「**動工**」，本輪 `brief-kind: review`、產出段明文禁改碼與禁改 SPEC 正文，不是動工；②該讀法是**死鎖且由該家自己觸發**——body 由 `76006a76…` 變成 `1b0890e3…` 正是主委採納該家 r22 之 `CODEX-R22-P1-03` 並照其修法改 SPEC 所致，若「戳記失效即不得審查／重簽」成立，則「委員要求改 SPEC → 戳記必然失效 → 無人能重簽」成閉環；③**同型第二次**，且該家在 stamp-r2／stamp-r4 面對同一情境皆正常審並 APPROVED（戳記區兩行可查）。該家碼證第二半（「composer/grok provenance 仍 pending」）亦已因補記而失效。
  - 🔴 **修法不是口頭駁回**（紀律型不被接受）：`AGENTS.md:40` 與 `.cursorrules:27` 之 Rule 12 改為以 **`brief-kind` 封閉集合欄位**判適用範圍——**僅 `impl` 適用**，`review`／`consult`／`closure`／`stamp` 一律不適用，即使 `reconcile_stamps_check` rc=1 也須照常審。白名單由 `scripts/brief_conformance_check.sh:191` 機械驗證。
  - **兩家一致實質結論（主委採納）**：`SU-RESID-2` 阻擋者＝**兩項**（`Task 9.2b`＋`Task 9.3`），非四項；`Task 2.3` 之「單 TF 下仍成立」註記**不需**改條件式；其餘舊 Task 段掃描**無**新 B9B 互斥。
  - 🔴 **r22 三條不標 CLOSED**：章程 §B8 要求由**原提出方**重跑反例，codex 未回驗 ⇒ 留待 r24。
- 🔴 **新坑**：`cx_run` 把 **brief sha256 綁在開債記錄**上，**同輪重派若換 brief 會被拒**（逐字 `ERROR: brief_sha256 與開債記錄不符（換 brief 掛既有 round 已拒）`）⇒ 要把駁回依據送達該家只能**另開新輪**。
㉒**review-r24（單派 codex）完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r24/synth.md`）：
  - **Rule 12 爭議已關**：該家 (0a) 逐字接受以 `brief-kind` 封閉集合判適用範圍、(0b) 明示不需否證，r23 之 G1 駁回成立。
  - **r22 三條由原提出方全數 CLOSED** ⇒ 章程 §B8 至此滿足。
  - **兩條新 finding 全採納並修完**：**H1（P1）🔴 同型第五次，且證實 v19 只修一處、漏了同一決定散落的另外五處**——①`M-SU-D2-03` 應紅欄仍指已被 §V 移出當輪的兩條 metadata 斷言 ⇒ **空殼 mutation**；②`§P`「鎖定三層…不得由實作者自選」仍是祈使句；③`§P` 獨立回退判準「移除上述三層」；④§V `Task 9.1` 尾句「移除上述三層後…」；⑤§R 回退句「移除三層揭露即可」；⑥`SU-RESID-9A-UI` **自身**括號把 `metadata.split_unify` 列為「本延伸交付」。全改兩層、原字面刪節線保留；`M-SU-D2-03` 整列改標「殘留期間無應紅測試、`blocked-by`」（判準同 `C5-28`）。**H2（P2）**：TODO §E `SU-RESID-C5-TARGETS` 同段寫「19 列」又寫「20 列」，已改 19——`C5-25` 補錨這一個動作**第三度**打翻同一數字。**主委另補：v19 的沿革條目當時漏寫，本輪一併補上。**
  - **SPEC 進 v20**，新 body sha256 `c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05` ⇒ v19 三枚戳記全失效須重簽。回歸 **706 passed、1 xfailed**。
- 🔴 **本輪最值得記的程序事實**：r23 之固定必答第 3 條（契約面改動後強制掃 SPEC／TODO 其他舊段）**composer 與 grok 皆答「無」**，codex 於 r24 逐段掃出**六處** ⇒ **強制掃描機制有效，但只在受派方真的逐段執行時有效；「三家同答無」不足以當作「確實沒有」**（與「不得以三家零 finding 當停輪依據」同源）。
- 🔴 **坑**：委員交件 `VERDICT: blocked` 會使該家 `result_state=verdict_rejected`，**`debt_clear` 會擋**，須主委修檔後對該家補一次 `gate.sh register-output <task> <檔> --kind stamp --family <fam>` 才解鎖。
㉓**review-r25（三家）完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r25/synth.md`）：**r24 兩條由原提出方 CLOSED**（codex 並一併 CLOSED 其 r22 三條）；但**三家全 blocked、撞同一題 ⇒ 同型第六次**：
  - **J1（P1，三家獨立提出、命中同一組）**：v20 修了 metadata 層六處，仍有**兩處 live**——①`§P Task 9.1` 之 `:187` bullet 仍以**祈使句**要求「須定義 `discarded` 之 producer→metadata **資料流交接**」並規定「驗收須為 producer→summary→metadata **整鏈**測試」；②`docs/SPLITUNIFY_TODO.md` §E 之 `SU-RESID-9A-UI`（`:892`）仍寫「Phase 9A 交付至 producer 層（producer 回傳 → summary → `metadata.split_unify`）」——**該殘留自身**的定義就是把 metadata 延後，卻在同句列成已交付；**v20 修了 SPEC §N 同名條目、沒改 TODO 這一面**。兩處逐字採 grok 修法改寫、原字面刪節線保留。SPEC 進 **v21**，新 body sha256 `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`。回歸 **706 passed、1 xfailed**。
  - 🔴 **主委另做全檔窮舉掃描**（非委員要求）：對 `metadata.split_unify`／`三層`／`整鏈` 三 token 在兩檔逐行列出並逐行判定 ⇒ 除本輪兩處外其餘皆已帶刪節線或更正註；`TODO:410`（`Task 4.1` IC 路徑五鍵，屬 `D-002-C6`）與 `TODO:469` 判**非互斥**，與三家一致。
  - 🔴 **composer 誠實把自己 r23 的立場改判 STILL-OPEN**（它 r23 答「舊段無互斥」，r24／r25 連續被推翻）⇒ **r25 brief 收緊必答 3「只答『無』而不附逐段掃描命令與涵蓋範圍者視為未作答」是對的**，本輪三家皆附逐段表。
  - 三家一致：`M-SU-D2-03` 改標無應紅**不**影響 mutation 條數（40）與 `C5` register（29 列，無列指向它）；`SU-RESID-C5-TARGETS` 之 19／10／4／15／29 兩檔全一致。
- 🔴 **連續第四輪（R18／R21／R22／R25）主委在 brief 自標的疑慮被證實**——本輪是 assumed 第 1 條「TODO 那一面是否也有把 metadata 當本批交付的舊段」，三家全部證實為真。
㉔🏁 **review-r26（三家）完成＝三家零 finding、全 proceed、v21 三家 APPROVED**（`handoffs/reconcile/20260911-splitunify-b9-review-r26/synth.md`）：
  - **r25 之 J1 由三家原提出方各自 CLOSED**。`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **rc=0**（body `755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f`）——**v18 之後首次重新取得完整有效戳記**（v19／v20 皆在取得前就被新 finding 打掉）。
  - 🔴 **必答 3 之加強版奏效**：本輪明令「不得只重跑主委用過的三 token」，三家各自列詞表逐段掃——codex 用「三段／第三層／揭露層／disclosure／end-to-end／three layers／`build_split_unify_disclosure`／`ic_filter_orchestrator`」；composer 用「`context handoff`／`完整記帳`／`資料流交接`／`孤立欄位`／`手塞`／`exact-key.*discarded`」；grok 分四類（層數／鏈驗收／揭露／防假綠落點）。**三份詞表互不重疊、三家皆判 live 正文無新互斥** ⇒ 同型第七次**未**發作。
  - 三家一致：`§P Task 9.1` `:187` 整條刪節**未**失去防假綠告誡（兩層等價物仍在——§V `:258` 之 producer→summary 值相等 real-entry 斷言、TODO 之 `EventSamplePipeline.run` wiring 測試）；`M-SU-D2-01`／`02` 之應紅欄皆仍指向當輪 summary 層測試。**三家一致判可進 B9C、無 BLOCKING。**
㉕**stamp-r5（對 review-r26 收斂檔補戳記）完成**：三家 APPROVED（body `72cabe12…`、`reconcile_stamps_check` rc=0）⇒ 可作 B9C impl token 之 `--adversarial` 授權依據。grok 另實查 `gate.sh` 確認其對 `--adversarial` 只驗「Verdict ＋ 戳記」、不要求內容涵蓋施工面。
  - 🔴 **主委開工前自標之三處條文未明寫，三家給出完全一致裁決，且主委假設②被 SPEC 原文否證**：①空 `train_rows` **不得定義哨兵**，步驟 0 即 fail-closed；②`decision_at_ms` **不得**加入 `EVENT_KEY_COLUMNS`／不得改 `build_event_keys` merge——正解是讀 `manifest.table`（事件級、欄已存在）；③同 `event_id` 錨點不唯一 ⇒ 三段式**之前** `AlignmentViolationError`。
  - 🔴 **主委另查出 TODO 與 SPEC 對同一驗收項形狀不一致**（三家未被問到）：TODO 寫「xfail 於本 Task 解除」，SPEC §V `:270` 之 (3.2) 反例卻是「**直接構造 `assignments`**」。事件級錨定下原 fixture 結構上造不出異側 ⇒ 已依 SPEC 形狀遷移該測試之 fixture（**node id 一字未改**，它是 `Task 9.2a` 驗收第 6 條之逐字錨點），xfail 已解除。**此處置待 B9C 審碼輪裁定。**
㉖🔴 **`Task 9.2b`（批次 B9C）已實作完成**（impl token `20260911-SPLITUNIFY-impl-b9-claude`）。**逐條內容、回歸筆數與每條破壞驗之鑑別力紀錄，唯一權威＝B9C 審碼輪收斂檔**（本檔不複述數字）。VERIFY:20260913T201758Z-splitunify-b9c-task92b-regression
  - **`split_projection.py`**：新增可單獨呼叫之 `_assert_event_level_side_consistency`（SPEC §V 之 (3.2) 反例形狀要求有入口）；`_derive_single_symbol` 判側改事件級——錨點取自 `manifest.table["decision_at_ms"]`、錨點唯一性閘、界外閘（**不是**第四條分支）、三段式（`<= train_last_ms` ⇒ train／`>= test_start_ms` ⇒ test／之間 ⇒ purged）、答案窗 purge 按事件側一次決定並廣播、`feature_cutoff_ms` **完全退出** `split_label`；空 `train_rows` 由 `continue` 改 raise；新增「`test_start_ms <= train_last_ms` 即兩段時間重疊」fail-closed。
  - **`pipeline.py`**：`EventSamplePipeline.run` 於 `derive_*` **之前**呼叫 `validate_split_pair_integrity`（步驟 0）。🔴 `ts` 須顯式轉 datetime——`_coerce_timestamp_array` 把數值一律當**秒**，餵毫秒會 `OutOfBoundsDatetime`；且**不得帶 tz**，否則 `validate_split_integrity:657` 之 `np.timedelta64` 比較 `TypeError`。兩個坑都實際踩到。
  - **`freeze_splitunify_golden.py`**：fixture 新增 `bnd_shift`（cutoff 在 test 段、decision 在 train 段，兩值**刻意不等**）——沒有它 (G-4d)②③ 是空心通過；`_oracle_membership` 依 (G-4c) **逐行重寫**為 decision-anchored；新增版本化鍵 `g1_membership_v9`／`g3b_oracle_v9`；建 **不可變** `splitunify_golden.v8.json` ＋ `.v8.sha256`，`--write` 對其拒寫且校驗 sha。🔴 **換錨零位移已實證**：改 production 後 golden **逐位元組未變**（(G-4d)②），加入 `bnd_shift` 後它落在 **train**（9.2b 前會是 test）⇒ 差異在手推錨點上現形。
  - 🔴 **自證階段當場抓到主委自己的兩個洞（同型第三次，這次是主委自己抓到而非委員）**：`M-SU-D2-14` 與 `M-SU-D2-30a` 兩條破壞**第一次跑都是全綠**——新測試全掛在可單獨呼叫的 helper 上，把**呼叫點**刪掉照樣過；與 R18 之 `A1` 完全同型。已補三條**接線測試**（spy 斷言「有呼叫」＋「順序在 `derive` 之前」＋「`ts` 為 naive datetime64`」）與一條空 train 應紅測試。VERIFY:20260913T201758Z-splitunify-b9c-task92b-regression
㉗**review-r27（B9C 首輪審碼）完成：三家共 11 條，全數採納並修完**（`handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md` ＝唯一權威，本檔不複述逐條數字）。
  - **碼面六條**：①`run` 步驟 0 把多標的 Mapping 餵給單標的 validator 得**裸 `AttributeError`** ⇒ 改具名 fail-closed（主委另查明：多標的本來就到不了此入口，位置參數對不上，故不在此造第二份邏輯）；②答案窗 purge 取 `label_end_ms.max()` **靜默吞掉**事件級欄位不一致 ⇒ 改唯一性 fail-closed；③錨點唯一性分支被更早的重複閘搶先而**不可達** ⇒ 前移並補「純重複仍是裸 `ValueError`」成對測試；④golden `--write` 整檔覆寫會**靜默丟既有頂層鍵** ⇒ 加超集護欄；⑤v8 不可變基準可被「同步改寫檔案與旁檔」繞過 ⇒ 改三層（碼內外部錨＋旁檔＋內容）且**兩種模式都跑**；⑥**(G-4e) 第三份判準缺席**——只比投影與 oracle 兩份時同錯仍綠 ⇒ fixture 加**人手逐筆填**之 `expected_side`、`main()` 做三方相等。
  - **文件面三條**：⑦🔴 **同型第七次**——TODO `Task 2.2` 三處仍以 live 祈使句要求 cutoff 集合成員判側（grok 實跑：依舊文改回 per-cutoff ⇒ 錨定測試轉紅）⇒ 已標 SUPERSEDED；⑧`SU-RESID-2` 帳面未隨批次前進 ⇒ 兩檔同步為「只剩 `Task 9.3`」；⑨SPEC §P／§V／§G 與 `_derive_single_symbol` docstring **四處**仍以 9.2b 前碼態為「現況」⇒ 全標為快照並補現行描述。
  - **SPEC 進 v22**，新 body sha256 `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132` ⇒ v21 戳記失效須重簽。回歸六路 **728 passed、0 failed、0 xfailed**。
  - 🔴 **主委具名偏離 codex 修法一處（待 r28 覆核）**：該家要求 golden 主檔頂層鍵凍住 v8 值、只新增 v9 鍵；但 `main()` 是拿**現行投影結果**與主檔比對，主檔凍 v8 值會使比對**永遠紅**、不可實作 ⇒ 改採等效之「不得丟鍵」護欄，v8 錨點保全由第⑤條三層檢查承擔。
- 🔴 **三家對主委四條 assumed 之判定：A1／A3 成立、A2／A4 不成立——被推翻的兩條正是主委自己最沒把握的那兩條**（三道 `AlignmentViolationError` 之公開入口可達性、`label_end_ms.max()` 之靜默吞噬）⇒ 連續第五輪（R18／R21／R22／R25／R27）自標疑慮被證實或被具體否證，做法維持。
- 🔴 **新增機制（同型第七次後）**：`Task 9.3` 動工前之 register 重掃 receipt，須**一併**列出「本批改過的契約在 SPEC 與 TODO 的全部落點」，不再只掃 register。
- 🔴 **坑**：收斂檔之「附錄：findings 逐字保留」是 **byte-faithful** 區，任何全檔字串取代（例如為了過 `spec_xref` 而去反引號）都會打破 body-hash 而使 `completeness_check` 整批紅。去反引號只能**限定在群集／處置段**。
㉘**review-r28 完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md` ＝唯一權威）：**composer／grok 零 finding 並對 v22 APPROVED；codex 四條 P1 全採納並修完**——
  - **N1**：r27 之「頂層鍵超集」護欄只擋**丟鍵**、不擋**改值**（該家實跑把 `g4_per_symbol_n` 改 `999` ⇒ `--write` 直接接受）⇒ 改逐值閘，要改須 `--accept-value-changes` **逐一具名**。
  - **N2**：外部錨被 r27 寫成 **helper 常數**，而 SPEC §V 早在 v13 之 O2 定死「錨在已提交文件、helper 只讀」⇒ 錨點移入 §V 逐字行、helper 只讀；v8 與旁檔改 `O_CREAT|O_EXCL` **write-once**。
  - **N3**：r27 之 (G-4e) 只人手填**側別**，**時刻**仍與投影共因 ⇒ 該家把 `decision_at_ms` 整批 **+1 毫秒**、側別不變，golden 仍過；已加第二欄人手判準 `expected_decision_at_ms`（由 fixture 常數逐筆手算），三方側別相等**之前**先做逐筆時刻對帳。
  - **N4🔴 同型第八次**：TODO 邊界②仍為 live「界外 ⇒ purged」，與 9.2b 之「界外一律 raise」互斥 ⇒ 逐字採該家修法改寫。
  - **SPEC 進 v23**，body sha256 `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d`。回歸六路 **732 passed、0 failed、0 xfailed**。四個探針主委皆實跑複驗會擋。
- 🔴 **本輪最重要的程序教訓**：主委在 r27 對兩處具名偏離委員修法時自稱「**等效**」，本輪**兩處都被實跑探針證明不等效**（N1、N3）⇒ **自稱等效不算數；偏離委員修法一律須由下一輪覆核**。本輪 N1 又有一處偏離（以「顯式具名」取代「一律禁止改值」，理由是後者會讓正當重凍不可能），已具名交 **r29 覆核**，不得再自我認定。
㊙**review-r29 完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r29/synth.md` ＝唯一權威）：composer／grok 零 finding 並對 v23 APPROVED；codex 五條 P1，**其中四條把主委 r28 自標的四條 assumed 全部否證**：
  - **O1**：`--accept-value-changes` 只驗**鍵名** ⇒ 一旦具名該鍵**任意**新值都能寫入（實跑把 13 改成 999、rc=0）。已改為授權須帶 `<key>=<old8>:<new8>`。
  - **O2**：錨點 regex 接受 SPEC **任意位置**，在 `HISTORY` 塞一行再同步換 v8 與旁檔即可繞過 ⇒ **可實作的半已修**（收窄到 §V）；**未閉合的半**需受保護簽章或不可變 ancestor attestation（外部信任根）⇒ 依使用者兩項裁定歸具名殘留 **`SU-RESID-V8-ATTEST`**（`user-ruling`）。
  - **O3**：人手錨點時刻寫成 `BASE + n * H1`，與 fixture 實際值**共用同兩個常數** ⇒ 平移 `BASE` 17 毫秒兩邊一起動、對帳照樣相等。已改 13 筆**不可變字面**。
  - **O4**：write-once 之**首次建立從未接進** `main()`（「首建成功」那一半沒有可執行路徑），且逐一 `O_EXCL` 會留半套狀態 ⇒ 新增 `--init-v8` 分支、先驗兩檔皆不存在、失敗回收。
  - **O5🔴 同型第九次**：§V `:270` 之註仍寫「fixture 全部事件 `decision == cutoff`、本斷言空心通過」（`bnd_shift` 補入後已過期）；TODO `Task 9.2a` **三處**仍要求該 node 輸出 `1 xfailed`（現實為 `1 passed`）。兩處皆改。
  - **SPEC 進 v24**，body sha256 `bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c`。回歸六路 **736 passed、0 failed、0 xfailed**；四個探針主委皆實跑複驗會擋。
- 🔴 **本輪之程序定論（最重要）**：主委在 r27／r28 兩輪共三處自稱「偏離委員修法但等效」，**三處全被實跑探針否證** ⇒ 本輪 O1／O3 改為**逐字採委員修法、不再自創形狀**；「等效」自此不得由主委自我認定。
- 🔴 **具名殘留 `SU-RESID-V8-ATTEST`（不得讀作已解決）**：v8 錨點只防意外與單點竄改，**不防蓄意的整批同 commit 替換**；該論證的信任根實際是 **code review 與 git 歷史**。觸發條件：專案導入 commit 簽章或受保護分支。
㉚**review-r30 完成**（`handoffs/reconcile/20260911-splitunify-b9-review-r30/synth.md`）：grok 零 finding 並對 v24 APPROVED；codex 兩條 P1 ＋ composer 一條 P2，**全數採納修完**；**r29 五條中四條 CLOSED**，餘一條之「同 commit 改四檔」那半維持殘留且該家明示**非 blocking**。
  - **P1**：🔴 **主委 r29 之 assumed「不可變字面已消除共因」被實跑否證**——把 `BASE` **與**字面**同步**平移，兩欄仍相等（那些字面當初是用同一組常數算出來再貼的）⇒ 已加**第三份獨立副本**於測試檔；主委實跑複驗**完整攻擊路徑**（連 golden 凍結值一起改）⇒ 轉紅並指名。
  - **P2🔴 同型第十次**：§P `Task 9.2` 六個 bullet 仍為 **live 舊碼態**（必傳、`str()`、四參數閘、每事件恰一列），該家實跑證明照舊段做會讓兩條 wiring 測試轉紅 ⇒ 已標 SUPERSEDED。
  - **P3／P4**：`--help` 舊語法已改；§V `:265`「fixture 常數逐筆手算」已標 v25 更正——🔴 **同型第十一次，且是主委 v23 寫的字面、v24 改了做法卻沒回頭同步自己的句子**。
  - **SPEC 進 v25**，body sha256 `29149ae8bd8bbdd77b84dc1d979f2ac4c1cb8e37f2feee8416f93fd3fb0b7b71`。回歸六路 **737 passed、0 failed、0 xfailed**；`GOLDEN OK`。
- 🔴 **`SU-RESID-V8-ATTEST` 之 `user-ruling` 歸類經該家獨立查證成立**（非主委自認）：`run_with_receipt.py:4-5` 明載 receipt 與 audit 同一可寫主體、非防惡意偽造；`verify_audit_chain.py:72-74` 純報告永遠 rc=0；`git config --get commit.gpgsign` 無輸出 ⇒ 既有倉內層都不能成獨立信任根。
- 🔴 **`Task 9.3` 動工前置之重掃分析已做完（唯讀）**：29 列逐列查證、**分類零變動**；`Task 9.3` 實際負責 **15 列**，其中僅 **3 列要改碼**（`C5-24` `pattern_bridge`、`C5-25` `ic_feed` 餵入端、`C5-29` `tables.py:372`）；殘留 `SU-RESID-C5-TARGETS` 兩條升級觸發**皆未成立**。實跑碼證：兩處在複合鍵下皆**大聲報錯**（`truth value of a Series is ambiguous`／`cannot reindex on an axis with duplicate labels`），不是靜默取錯值。
- 🔴 **重掃另查出兩個真問題（待 B9D 審碼輪）**：①**四處 register 行號語意失準**（`C5-19`／`C5-21`／`C5-26`／`C5-27`）——全都**通過**「行號 ≤ 總行數」那道機械檢查卻指向註解，**那是弱閘**；實際位置 `:360`／`:808`／`pipeline.py:825`／`:811`。②**驗收第 1 點指向不存在的落點**：要求 `COMMIT:` 等於 audit.log 中該 impl task-id 之 round-start HEAD，但 `impl_token_issued` 事件 schema **根本沒有 HEAD 欄**。兩條皆不自行認定替代讀法，列為 B9D brief 之 assumed。
㉛**review-r31：三家全 `blocked`、10 條 findings**（codex 4×P1＋1×P2、composer 1×P1＋2×P2、grok 2×P1）。r30 之 `CODEX-R30-P1-02`／`P2-03` 已 CLOSED。四條 P1 主軸：
  - **「第三份獨立副本」不成立**（codex P1-01）：三份值仍是同一批手填字面，該家回報實跑三份同步改錯即綠。🔴 **這是主委第四次宣稱「等效」被實跑否證**。處置＝判為與 `SU-RESID-V8-ATTEST` **同一不可閉合類**，**併入該殘留**而非再加第四層副本；此判斷以 assumed 交下一輪，不自我認定。
  - **SPEC C4 (4.2) 與 C5 (5.2) 仍 live 舊契約**（codex P1-02 ＋ composer P2-01）：C4 仍寫單選且靜默丟列；`(5.2)`（SPEC `:76`）仍寫 `merge validate="1:1"` 與過期落點 `:291-303`，現行為 `many_to_one`。🔴 **同型第十二次**。
  - **四處 register `path:line` 語意失準**（codex P1-03 ＝ grok P1-02 ＝ composer P2-02，**三家撞題**）：`C5-19`／`C5-21`／`C5-26`／`C5-27` 全通過「行號 ≤ 總行數」弱閘卻指向註解。grok 明判**不是** `SU-RESID-C5-TARGETS` 之升級觸發。
  - **`Task 9.3` 驗收第 1 點不可執行**（codex P1-04 ＝ composer P1-01 ＝ grok P1-01，**三家撞題**）：`impl_token_issued`／`committee_dispatch`／`ticket_commit` schema 皆無 round-start HEAD 欄。修法＝發 token 時記 `round_start_head`，receipt `COMMIT` 須精確等於該欄。
  - **codex P2-05（TODO 漂移，主委自產）**：`docs/SPLITUNIFY_TODO.md:68`／`:522`／`:618`／`:851` 四處過期。
  - **十條全數處置完畢，SPEC 進 v26**，body sha256 `565505c6877a789e10cc9dc0c8aa90ac5db05719b4ff9127aa192055a229c3ba` ⇒ v25 戳記失效須重簽。六路回歸 **737 passed、0 failed、0 xfailed**；`GOLDEN OK`；`test_verdictgate_p3.py` **47 passed**（新必填欄之替身已同步）。
  - 🔴 **委員給的「statement/AST overlap」修法照做後實跑量測，只殺掉四處中的兩處**——純註解的兩處 FAIL，但指向「真實但錯誤的碼」的三處照樣 OK ⇒ 主委**具名加強**為合取判準（同一行須同時是可執行 statement 且逐字含新增之**錨 token**）。實跑 10 列全 `ANCHOR_OK`、五處舊落點全 `ANCHOR_FAIL`。🔴 **該閘一上線就另咬出委員沒提的兩處同型漂移**（`C5-23`→`:110-111`、`C5-25` 呼叫端→`pipeline.py:409-411`）⇒ 本輪實修**六處**，不是四處。此加強屬具名偏離，交 r32 覆核。
  - 🔴 **`round_start_head` 已成 `impl_token_issued` 之必填欄**（`scripts/gate.sh` 取不到或非 40-hex 即**拒發 token**）。**副作用**：任何自行組 `audit_append.sh --event impl_token_issued` 的地方都必須帶這一欄。
㉜**review-r32：composer／grok 零 finding 並 proceed（r31 五條全 CLOSED）；codex 一條 P1**。
  - **codex P1 打的正是主委在 r31 自己加的那道錨點閘**：v26 用「行**範圍** ＋ 單一 token **子字串**」，該家實跑打穿——`split_projection.py:341`（`raise` 的**訊息字串**裡有 `feature_timeframe`）與 `:566` 都命中；且該閘「只在驗收當下跑一次、沒有可重跑的 persisted checker」。🔴 **同一道閘連續第三代被打穿**（v15 行號≤總行數 → R31 委員的 AST overlap → v26 主委的範圍＋子字串）。
  - 🔴 **教訓（主委自產）**：主委當輪**已量測過委員原修法只殺四處中的兩處**，卻**沒有同樣去量測自己的加強版會不會也留洞**——自證只做了一半。凡自創判準，須用**同一組 must-fail 樣本**回測自己的版本。
  - **修法逐字採 codex**：錨點改**單一精確行**；`.py` 用 `tokenize` 取該行 token 串、register 所載 token 序列須依序出現且**恰好一次**（字串 token 含引號逐字比對）＋AST 確認非純字串常數 statement；`.tsx` 精確 literal 且恰好一次；**0 次或多次皆拒**。落地＝**`scripts/register_anchor_check.py`**（register 新增機器可讀 `ANCHOR <path>:<line> TOKENS …` 子句，16 錨點涵蓋 10 列）。
  - **「沒有 persisted recheck」那半已關**：兩條新測試進 `tests/momentum/Analysis/test_splitunify_contract.py`（該檔在六路回歸內）⇒ register 行號日後再漂、或閘被放寬回子字串，**當場轉紅**。must-fail 清單逐字＝`:341`／`:566`／`:556`／`pipeline.py:760`。破壞性自證兩案皆轉紅。
  - **三條 assumed 全數成立**（codex 逐條複跑）：`SU-RESID-V8-ATTEST` 併入面 b 為誠實登記；`round_start_head` 實跑 `MATCH=1`、空倉 `rev-parse` rc=128 故拒發 token 為預期、production emitter 僅 `scripts/gate.sh` 一處；C4／C5 **無第十三處** live 互斥。
  - **SPEC 進 v27**，body sha256 `5dc53606d1fe4679861e1ccaf9919e6fbb274871f1ac87d2a69adae49f24b7b1` ⇒ v26 戳記失效須重簽。六路回歸 **739 passed、0 failed、0 xfailed**（+2＝新錨點測試）；`GOLDEN OK`。
㉝**review-r33：composer／grok 連兩輪零 finding 並 proceed；codex 三條 P1＋一條 P2**。
  - 🔴 **三條 P1 逐一對應主委在 r33 brief 自標之 assumed 1 的三個「我沒查」子項**——①token 比對是**可跳 token 的子序列** ⇒ `columns = ["timeframe"]; emit("feature_timeframe")` 這種**語義替身**也綠；②`_ordered_subsequence_count` 貪婪不重疊計數**漏算重疊命中**（`a b a b a` 找 `a b a` 應 2 回 1）⇒「恰好一次」不成立；③`.tsx` 只比指定行、**不驗檔內唯一性** ⇒ 同 literal 之 decoy 行可冒充。
  - 🔴 **這道閘連續第四代被打穿**（v15 行號≤總行數 → R31 委員 AST overlap → v26 範圍＋子字串 → v27 單行＋子序列），四代都曾被當成已閉合。
  - **逐字採三條修法**：`.py` 改**正規化完整 token 序列逐一相等** ＋ 該序列**整檔恰好一行** ＋ 保留 AST statement 閘，`_ordered_subsequence_count` **整個移除**；`.tsx` 改**正規化整行 sha256 相等** ＋ 整檔恰好一次。16 個 ANCHOR 全改寫為完整序列並實跑通過；四個反例全 `ANCHOR_FAIL` 並逐條進 must-fail 回歸。
  - **另補反向測試** `test_d002_register_anchor_gate_accepts_the_real_lines`（真實落點必須通過，否則 must-fail 三條可靠「閘永遠回 False」全過）＋ checker 檔缺席即 assert 失敗。
  - **SPEC 進 v28**，body sha256 `5b73e5fa65007112df5c407761b7477dfc11046b41c581b7cf645e33c49c82a4` ⇒ v27 戳記失效須重簽。六路回歸 **741 passed、0 failed、0 xfailed**（+2＝R33 decoy 與反向測試）；`GOLDEN OK`；錨點閘 16/16 rc=0。
  - 🔴 **程序定論（兩條，方向相反）**：①「把沒把握的面逐條寫進 brief 交出去攻」**第六輪被證實有效**（R18／R21／R22／R25／R27／R33）。②**但主委自創判準時的自證深度不足**——v27 那版只回測「上一代的 must-fail 樣本」，沒針對**新判準自身的結構選擇**（子序列、計數方式、檔內唯一性）各構造反例。⇒ 新規則：**凡自創判準，須對該判準自身的每一個結構選擇各構造一個反例**。
㉞**review-r34：composer 連三輪零 finding 並 proceed、grok 一條 P2 並 proceed；codex 四條 P1**。
  - 🔴 **錨點閘連續第五代被打穿**（v15 → R31 委員 AST overlap → v26 範圍＋子字串 → v27 單行＋子序列 → v28 整行＋單檔唯一）。四條：①**跨行 token**（多行字串）中間行拿到整個 STRING token ＋ `.tsx` **只驗單檔** ⇒ 整行搬到另一個檔即看不出；②`REPO_ROOT / <絕對路徑>` **丟掉前綴** ⇒ 錨可指 repo 外任何可讀檔；③`len(anchors) >= 16` 不保證逐列完備（剝掉 `C5-14` 再從 `C5-13` 複製補回總數即假綠——**codex 與 grok 兩家撞題**）；④**錨點涵蓋不足**：16 個逐點有效卻漏綁五個 seam，改壞它們閘不變紅。
  - **逐字採四條修法**：`.py` 只收**起訖都在該行**的 token、被跨行 token 覆蓋即 fail-closed；`.tsx` 唯一性擴到**全 repo**；新增 `_resolve_in_repo` 路徑守衛（拒絕絕對路徑與 `..`，`resolve()` 後須在 repo 內）；contract 測改**逐列精確計數**；補**七個**錨點（16 → **22**）。
  - 🔴 **r33 定下的新規則本輪已照做且有效**：四個結構選擇各跑一個破壞性自證、全數轉紅；補錨時另由閘自己抓出 `split_projection.py:812` 與 `:915` token 序列相同（改用 `:811`，此偏離具名交 r35）。**但它仍不足以事先發現「涵蓋不足」**——那不是判準自身的形狀問題 ⇒ 必答 4 之「判涵蓋充分性而非只判指對」保留為固定必答。
  - **SPEC 進 v29**，body sha256 `d0d9006985ba8f4152bb5489ea13a30bede64bcb7b69929effbcf0b75f90dca5` ⇒ v28 戳記失效須重簽。六路回歸 **741 passed、0 failed、0 xfailed**；`GOLDEN OK`；錨點閘 **22/22** rc=0。
  - 🔴 **又踩了一次 HANDOFF 已記的坑**：用腳本全檔取代反引號 token，連**byte-faithful 附錄**一起改到，`completeness_check` 會紅。已只還原附錄三處。**取代一律只限群集區（附錄標頭之前）**。
㉟**review-r35：🎉 三家全數 `proceed`，且三家皆對 v29 蓋 `APPROVED`——自 v21 以來首次乾淨三家戳記**。codex 之 r34 四條全 `CLOSED`、grok 之 r34 一條 `CLOSED`。
  - **只剩兩條 P2，兩家皆明示非 blocking，均已即修不留殘留**：①`CODEX-R35-P2-01` 錨點閘遇 malformed／非 UTF-8 標的檔會**整支 crash 而非乾淨 `ANCHOR_FAIL`** ⇒ 載入邊界統一捕捉六種例外，三種壞檔實跑皆乾淨轉紅並進六路回歸；②`GROK-R35-P2-01` R34 已把 `.tsx` 唯一性擴到全 repo，但 SPEC `C5-28` 腳註與 checker 註解**三處仍寫「整檔恰好一次」** ⇒ 四處已改。
  - 🔴 **②是「改 A 沒同步 B」同型第十三次，且又是主委上一輪改了行為卻沒回頭同步自己的敘述**（與 v25 那次完全同型）。
  - 🔴 **值得記的轉折**：兩條 P2 都不是「閘被繞過」，而是**閘的邊界行為**與**閘的自我描述**。前五代打的是正確性，第六代開始打的是**可維護性**——通常代表核心判準已經穩了。
  - **SPEC 進 v30**，body sha256 `e0cff27f6b4695d384283af146e8521b332bec9df4d20bafe96c3d7bcb3a6e76` ⇒ v29 之三家戳記失效，須以 **stamp 輪**重簽（非全審輪；兩條 P2 皆為委員自己要求之修補）。六路回歸 **742 passed、0 failed、0 xfailed**；`GOLDEN OK`；錨點閘 22/22 rc=0。
  - 🔴 **stamp-r6 要同時蓋兩份**：`docs/SPLITUNIFY_SPEC.D-002.md`（v30 body 上列）**與** `handoffs/reconcile/20260911-splitunify-b9-review-r35/synth.md`（body `acf0b77ca2f05cab8481c82d7aa894f8219e0ff509212c3ab187d3a392f4655c`）——後者是 B9D impl token 之 `--adversarial` 標的，`gate.sh` 機器強制要求它已獲全數戳記。
㊱**stamp-r6：composer／grok 零 finding 並蓋章；codex 三條 P1 並 REJECTED——其中一條正是主委在 brief 自標之「本輪唯一真正的決策點」**。
  - 🔴 **`CODEX-R6-P1-01`：`review-r35` 收斂檔不足以當 `Task 9.3` 之 impl 授權依據**——它那三條 finding **全是關於錨點閘**，與施工語意（`C5-24`／`C5-25`／`C5-29`）無逐條對應。該家碼證可執行：**讓任一 consumer 不去重，錨點閘仍回 22/22** ⇒ 它證明的是「驗收機制可用」，不是「施工設計已審過」。
  - 🔴 **三家分歧，依 2026-09-11 裁定「看碼證不數人頭、不決採較嚴版」取 codex**。另兩家（尤其 grok 逐字寫「gate 不要求施工面逐條對應」）講的是**閘的最低門檻**，codex 講的是**該不該審**——不是同一命題。⇒ **另開 `Task 9.3` 設計 consult 輪**，`--adversarial` 改指其新 synth。
  - **`CODEX-R6-P1-02`**：邊界②只寫「fail-closed raise」**未釘死例外型別** ⇒ 已釘死 `AlignmentViolationError`＋訊息含 `event_id`＋測試禁以 `Exception`／`ValueError` 寬比（後者是父類，寬比會放過契約漂移）。TODO 與 §V 同步。
  - **`CODEX-R6-P1-03`**：該家實跑證明**去重與否會改變** `event_manifest_hash` ⇒ 補「既有單 TF 且 ID 唯一輸入之雜湊必須逐字不變、只比對不得自動 `--write`、digest 一變即停止並轉 `Task 9.5`」，並補 `(丙)` 列分類變動之 `TARGETS` 補錄流程。
  - **(4a) 例外捕捉範圍**：三家一致判不形成假綠（結果仍為 `ANCHOR_FAIL`），不開 finding。
  - **SPEC 進 v31**，body sha256 `32cb622044851905e426b32a6276a3467d95efbca2315c617ba6d5d97323ff82`。六路回歸 **742 passed、0 failed、0 xfailed**；錨點閘 22/22 rc=0。
  - 🔴 **程序定論**：主委把這個問題寫成 brief 裡唯一的決策點交出去攻，**結果正是它被否證**——若自行認定「三家都 proceed 就夠」，B9D 會在**沒有任何一輪審過施工設計**的情況下開工。這是主委自標 assumed 被證實的**第七輪**。
㊲🔴 **方向反轉：`consult-r4`＋`consult-r5` 三家一致——切分歸屬表退回事件級（起因＝使用者提出之設計質疑）**
  - 使用者逐字問：「屬於 E1 這時間點上的任何特徵，本來都在同一列上，所以就歸於同一個 train 或 test，這會有什麼切分問題？」主委查證後認為成立但**不自行拍板**，交兩輪 consult。
  - **r4 三家一致**：`assignments`／`purged` **不需要** `feature_timeframe` 欄——側別由事件級判一次後廣播，該欄不承載判定資訊；三家各自窮盡掃描確認**無任何消費者**。
  - 🔴 **codex 回查出主委漏讀之關鍵**：**R1 規格輪本就寫明**「內部投影可用複合鍵；對外之 `EventSplitPlan` 維持事件級」⇒ `Task 9.2a` 外推是**實作做過頭**，本次是把實作拉回原規格。三家判現行為**過度工程**。
  - **r5 三家獨立撞同一題**：只改組列不改計數，`tier_min_test_events` **門檻仍可被 1 事件×N TF 膨脹繞過**＝**門檻失效** ⇒ 組列與計數**必須同一次改完**。
  - 🔴 **`CODEX-R5-P1-01` 否證主委 assumed A**：必須有**具名的 `event_id` 聚合 seam 並逐欄驗值**，**明禁** `drop_duplicates`／`set`（會靜默吞掉衝突）。
  - **已改完（文件面）**：register 六列 `C5-20`／`21`／`22`／`23`／`24`／`29` 由乙／丙**改判甲**；`M-SU-D2-05`／`35`／`36`／`37`／`40` **撤下**（原字面逐字保留）；`C5-25`／`M-SU-D2-38` **保留不撤**；§V `Task 9.2a` 斷言反轉為三條；(0.4) 新增**適用層限制**；`SU-RESID-2` 改寫「未關閉的那一半」之定義；`Task 9.3` 全面改寫為退回工並貼入逐落點清單。
  - 🔴 **`SU-RESID-C5-TARGETS` 觸發 2 成立**（`C5-20` 分類改動且有實質落點）⇒ 同次補 `TARGETS`；觸發 1 實跑仍 15，未觸發。
  - 🔴 **具名缺口（主委不自行補）**：五條 mutation 撤下後，退回**自身**的可壞面（輸出多列／聚合靜默吞噬／計數被膨脹）**無 mutation 覆蓋**，列為下一輪 review 必答。
  - 🔴 **兩個自產錯誤（同輪內兩次）**：撤下腳本用 `split(" | ", 2)[2]` 把**第二欄原字面整欄吃掉**，而我同一句才剛寫「原字面保留供追溯」——由 `spec_xref` 抓到；改正後仍再犯一次同型（少算一欄），第二次才修對。⇒ **凡「保留原字面」之批次改寫，必須從 git HEAD 取原列、只去前綴，不得用欄位切割。**
  - **SPEC 進 v32**，body sha256 `6e2c8c82abdd82621a9eeb1cda31c5129074ec109e6611596d831352016f65f8`。
㊳**review-r36：三家全 blocked、17 條——三家撞同一題，主委 v32 大改後大量 live 舊契約沒同步（同型第十四次）**。
  - 🔴 **這次是主委在一次大改中大規模自產**：做了方向反轉，卻只改 register 與少數幾處。十餘處未同步：SPEC `(5.1)`–`(5.5)`、§P `Task 9.2a`／`9.3`、§V `Task 9.2` 列數式、§V purge 面（與同檔 `Task 9.2a` **直接互斥**）、§G `(G-3)` 擴維、`M-SU-D2-12`／`16` 破壞方向；TODO `Task 9.2a` 要點 1、`Task 9.3` 邊界 reducer、§E `SU-RESID-2`。全部已逐處標作廢並寫出現行契約。
  - 🔴 **兩條「寫了要做卻沒說怎麼做」**：①主委只寫「具名 seam」**卻沒給名**（grok 逐字：實作者可用 inline `drop_duplicates` 自稱 seam）；②`n_event_tf_rows_purged` 取數方式沒給。**逐字採 codex 之簽名** `_aggregate_event_level_split_rows(event_keys, event_state) -> tuple[list[dict], list[dict]]` **與公式** `n_event_tf_rows_purged = int(event_keys["event_id"].isin(purged_event_ids).sum())`（單／多標的共用）。
  - **主委刻意留白的 mutation 缺口由委員填上**：`M-SU-D2-41`（output multiplicity）／`42`（reducer 吞 conflict）／`43`（計數被 TF 列數膨脹）／`44`（`n_event_tf_rows_purged` 改回 `len(purged)`），條數 40 → **44**。**這個「不自創、留給委員」的做法有效**。
  - **Tier 0 表補三個漏掉的多標的落點**（`:899-901`／`:914-916`／`:917-932`）——主委原表只覆蓋單標的。
  - 🔴 **新規則（自本輪起）**：凡**方向反轉**型修訂，**必須在同一次改動內用自立詞表把舊方向的祈使句全檔掃過一遍**，掃描結果附在該次修訂中，**不得留到下一輪由委員代掃**。
  - 🔴 **主委已照做並自查補漏 8 處（委員沒點名的）**：`(3.2)` 落點具名化、§P `Task 9.3` `pattern_bridge`、§P `Task 9.5` 之 (G-3) 擴維；TODO 記帳守恆式 `len(assignments)+len(purged)==len(event_keys)` **退回後不成立**、`Task 9.5` 複合鍵集合比對、freeze fixture 擴維之界定、`Task 9.2a` 標題與覆蓋風險。
  - **SPEC 進 v33**，body sha256 `d1c8f2d81a2777cb2d78841067ef186ee9e2dee19117408cf16874219a6b8f3f`。六路回歸 **742 passed**；錨點閘 22/22。
㊴**review-r37：三家全 blocked、13 條——主委同步不完整之第三輪連續發作，已全修完並進 v34**。
  - **三家撞題**：`(5.2)` **整段漏列**（v33 表列了 `(5.1)`／`(5.3)`／`(5.4)` 卻漏了講 producer 本體的那一節）；`(5.3)` **同一句內自相矛盾**（前半寫改判甲類、尾句仍寫丙類真缺陷）；§P／TODO `Task 9.4` 兩處仍要求改複合鍵映射；`(5.5)` 仍寫「後者覆蓋前者」。
  - 🔴 **最能造成假綠的一條（`GROK-R37-P1-04`）**：v33 新增了 `M-SU-D2-41`..`44`，**卻沒回填 register `C5-20`／`C5-21` 之 mutation 欄**——該欄仍寫「尚無 mutation 覆蓋」，驗收可據此宣稱「無應紅」而放行。已回填。
  - 🔴 **主委四條 assumed 全數被否證**，含 **brief 自身把 body hash 寫成上一輪舊值**（取代腳本只涵蓋完整 64-hex，**截斷形沒被取代**）。⇒ 日後 brief 之 hash 須以**單一變數**填入、不得用字串取代。
  - **`CODEX-R37-P1-04`**：v33 只給 seam **簽名**，沒說定義處／呼叫面／多標的 `event_state` 如何合併 ⇒ 已補四欄規定，**明禁**先合併各 symbol 之 `event_state` 再呼叫（會遮蔽跨 symbol 鍵碰撞），並要求串接後**再驗一次**全域 `event_id` 唯一。
  - **主委以委員詞表自掃另補三處**（委員未點名）：`(6.1)` 未說明退回後三量之**來源層不同**、`Task 9.4` 門檻路徑行號為退回前值、`M-SU-D2-39` 與新增 `43` **破壞面重疊**（一 defect 兩 ID）⇒ 已劃分工。
  - **SPEC 進 v34**，body sha256 `c8a37cbcaecb5fccf8e3d9dfd41a2e177a8b78d42b5c9f2fdce5f2c073e870d3`。
  - 🔴 **程序定論（連續第三輪同型，做法已改）**：主委「自己掃一遍再交」三輪都沒掃乾淨，殘留集中在**同一句前後矛盾／整節漏列／新增物沒回填舊索引**三型 ⇒ **方向反轉型修訂改為：先由審查方產出完整落點清單，主委照單改，再逐條核對**；主委自掃降為補充。

🔴 **死結已修（2026-09-14，使用者核可後施作）**
  - **病因**：VERDICTGATE B2／B3（**2026-09-11**）把閘加到 `debt_clear` 的**銷帳路徑**上（family `result_state` 須 `success`）。B3 當時**已實戰撞到**（commit `8cbd9539` 訊息逐字：「閘實戰首次拒收委員裁決行後清債被鎖」），卻**只補了 `verdict_rejected` 一支**；`format-failed`／`failed` 照樣被擋。⇒ 銷帳被鎖 ＋ 同輪重派被「有 OPEN 債即拒發 token」擋住 ＝ **完全死結**，只能請使用者手動跑 `cx_run`。這違反 2026-07-25 拍板之原始原則逐字「**清帳不被擋故非死鎖**」。
  - **修法**：三支統一走同一出口（其後有同 round 之 `committee_output`），並**按狀態加嚴**——`format-failed`／`failed` 另須該檔 `completeness_check --single` rc=0；`failed`（CLI 非零退出、無從得知是否跑完）再加「產出檔須帶 `VERDICT:` 與 `STATUS: DONE`」（🔴 **此加嚴為主委自訂、委員未給，具名交下一輪覆核**）。
  - **測試六條**（`tests/governance/test_debt_clear.py`）：三條擋、兩條放行（反向可證偽，防「永遠擋」作弊）、一條**釘住 `result_state` 枚舉**——日後新增第五個失敗狀態必須明確決定其出口歸屬，否則當場轉紅。
  - **破壞性自證兩次**：①拿掉兩道加嚴 ⇒ 三條轉紅 ✅；②放寬成 `!= "success"` ⇒ **五條全綠**，起初判為測試有洞，實查後發現 `result_state` 是 **registry 封閉枚舉**（寫入端 fail-closed），兩種寫法語意等價、**不是洞** ⇒ 改為釘枚舉本身。
  - **實效**：r37 之債已用修好的路徑清掉（`家族 grok failed 之後已重新 register-output 且單檔格式檢查 rc=0 ⇒ 視為已交件`），**未再動用使用者 terminal**。
  - **通則入 `docs/SCAR_LEDGER.md`**：🔴 **凡「解除既有阻塞」的路徑，本身不得再被同一族的閘擋住**——那不是防護，是死結。
- **下一步**：`review-r38`（依新做法**先請審查方出完整落點清單**）→ 領 impl token 執行退回。

## 現況
- **b9 SPEC（`docs/SPLITUNIFY_SPEC.D-002.md`）＝v31，body sha256 `32cb622044851905e426b32a6276a3467d95efbca2315c617ba6d5d97323ff82`，🔴 現為「待重簽」（v29 曾取得三家 APPROVED；v30 因 codex 三條 P1 而 REJECTED）**。
- **consult-r2 之四步裁定**（`.../20260911-splitunify-b9-consult-r2/synth.md` ＝唯一權威）：①REVERT **已做** ②補 TODO Task 9.1–9.5 **已做** ③派 stamp 輪 **已做**（stamp-r1..r4）④領 impl token 後才動生產碼 **已做**（B9A／B9B 各憑 token）。
- **Phase 9 依賴序（四方一致）**：`9.1 → 9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5`；`9.2`／`9.2a` 不得拆批；`9.5` 必須最後。
- 🔴 **批次狀態之唯一權威＝`docs/SPLITUNIFY_TODO.md` §B 之「狀態」欄**（2026-09-14 使用者質問「你為何又跳過 TODO」後定）。**出生事故**：主委實作完 B9A／B9B／B9C 三批，卻**一次都沒回去標 TODO**——狀態只記在本檔與白話看板，於是同一件事有**三份**而 TODO 是過期的那一份；**這就是委員已抓九次的同一個病**，只是漏的是 TODO 自己的進度、犯的人是主委。⇒ **本檔與 `白話說明/` 一律不再自寫批次狀態清單**，只指向 §B；每批收尾固定動作新增一項：**回去標 TODO §B 與該 Task 標題**。
- 🔴 **主委具名不採納委員原文兩處**（理由見 synth）：grok `Task 9.4` 之**無路徑** `pytest -k`（會收全套、小時級）；composer `Task 9.2b` 之 `bash scripts/freeze_splitunify_golden.py`（檔是 `.py`，且 golden 重凍屬 `9.5`）。
- 🔴 **「雙家族」字面已更正為指標**（`CLAUDE.md:30`、ORCH `:41`／`:195`）——唯一權威＝ORCH §1 現行分工行＋`scripts/governance_roles.json`，現行＝**三家全員**。CLAUDE.md 自己已明令「本檔不得自寫家數」，這是同型漂移第二次。
- 🔴 **DOCROT 成效量測點的編號要對**：b9 之 `review-r1`..`r12` 全是**規格**審查輪（DOCROT 上線前），`doc_friction_ratio` 要量的是**上線後**的前兩輪 review ⇒ 實際落在 **`review-r13`／`review-r14`**（Task 9.1 實作後的審碼輪）。兩輪皆須 ≤0.30 且每輪 ≤20 條；不達＝DOCROT 失敗，回報使用者重議，**禁順手開新 epic**。

## 待辦分流
- **待使用者**（看板偏好，非技術）：`白話說明/` 22 份是否整理、怎麼併（GAP-3 佔 8 份、5404 行）。
- **下一步（技術，不問使用者）**：修 r31 十條 → SPEC v26 → `review-r32` 閉合再驗證＋重簽 → 收斂＋`debt_clear` → 進 `Task 9.3`（B9D）。

- 🔴 **新發現的系統性缺口（具名殘留，`blocked-by`，**未**開新 epic）**：`docs/` 底下帶 `RECONCILE-STAMP` 的檔**沒有任何一份**能通過 `reconcile_stamps_check`——`gate.sh register-output` 原只收 `handoffs/`，而 provenance 要求審計中有指向被戳記檔**自身**的事件。本輪只把 `docs/SPLITUNIFY_SPEC.D-002.md` 加進既有封閉白名單 `scripts/stampable_artifacts.txt`（該檔正是為此型缺口而建）；`GAP3_EVENT_UX_SPEC.D-001.md`、`GAP3_EVENT_UX_TODO.D-001`..`D-006` **未一併加入**，因其戳記是否對應現行 body hash 未經查證，盲加＝把未驗證的背書寫成既成事實。另 `handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md`（D-001 定案檔）之戳記 hash 與 HEAD body hash **不符**（戳記 `9e1ef3d1` vs 實際 `e3f2847d`），亦即「D-001 三家戳記定案」目前機械上是紅的。

## 坑
- 🔴 **SPEC 戳記要能過 provenance，需 `gate.sh register-output <task> <SPEC路徑> --kind stamp --family <fam>` 逐家各跑一次**（`--kind stamp` 才會跳過 verdict parser；檔名無 `-<family>.md` 尾碼時 family 必須顯式給）。且該 SPEC 路徑須先列入 `scripts/stampable_artifacts.txt`。
- 🔴 **委員裁決塊不合契約時，出路是 `debt_clear.sh:394` 的設計路徑：主委修檔後 `register-output`**，不是重派。本輪 codex 寫 `CLOSED: 2026-09-13`（日期而非 finding ID）被 `verdict_parse` 拒收 ⇒ 主委只改那一行為空值並於檔內註明，其餘一字未動，再 register-output 即解鎖。
- **同輪重派仍須使用者 terminal**（gate 見本輪 OPEN 債即拒發 token）。命令形式：`ROUND_ID=<id> bash scripts/cx_run.sh <family> <brief> <out>`；主控端再 `register-output` → 移走舊收斂目錄後 `reconcile_build` 重建 → `debt_clear`。**永遠不要 kill 執行中的 `committee_run`**。
- **session 名不得重複**（fail-closed）：`20260911-splitunify-b9-consult-r1` 早在 2026-09-12 用過，本輪只好用 `-r2`。派前先 `bash scripts/debt_ledger.sh --list | grep <session>`。
- **SPEC 戳記輪的 brief-kind 要用 `closure` 不是 `stamp`**：`brief_conformance_check.sh:425` 要求 `stamp-target` 須 `handoffs/` 前綴，而 SPEC 在 `docs/`。既有作法見 `handoffs/20260912-SPLITUNIFY-D001-STAMP-BRIEF.md`。
- **synth 處置欄的反引號 token 必須逐字出現在標的檔**（`spec_xref_check --synth`），否則寫檔 hook 擋；`延後→Task N.N` 之說明**不得有巢狀全形括號**，且目標 Task 須已存在於 `--todo`。
- `committee_run` 的 harness exit code 不可信：本輪 `committee_rc=0` 但 harness 報 failed（尾端 `tail /tmp/*.log` 因沙箱重導而找不到檔）。**讀 `committee_rc=` 那行**。
- 🔴 `pytest` 一律逐檔明列路徑；`-k` 只過濾執行、**不減少收集**，無路徑即從 rootdir 收全套。
- 🔴 `reconcile_build.sh` 一律帶 `--mode review`；`debt_clear` 用 `--round-id <id> --session <name> --lock <sources.lock>`（不吃位置參數）。
- 🔴 **第三個既有紅（2026-09-14 實測，非本輪改壞；以 `git show HEAD:scripts/debt_clear.sh` 對照確認同樣紅）**：`tests/governance/test_debt_emit.py` 之 **7 條 `test_b3_*`** ——隔離 repo 之依賴複製清單缺 `scripts/prev_review_resolve.sh`（`committee_run` 開輪前置會呼叫它）⇒ `No such file or directory`。與既有那條「缺 `quant_standard_check.sh`／`ticket_batch_check.sh`」**同型同因**。
- 🔴 **兩個與本批無關的既有紅**（2026-09-14 實測，**不是本輪改壞的**）：①`tests/governance/test_gate_deny_fields.py::test_01_corpus_a_covers_decision_branches` — 它斷言 `scripts/gate_check.sh` 內有錨點字面 `INPUT="$(cat)"`，但該檔現行為 `INPUT="$(python3 -c …`（該檔本輪未被改動，`git status` 乾淨）⇒ 錨點漂移型假紅。②`scripts/obligation_block_check.sh` 對 `docs/SPLITUNIFY_SPEC.D-002.md` **結構性 rc=1**：其 R5 規則要求「帶裁決編號之行只准在 HISTORY 專區內」，而本檔每個 SUPERSEDED 註記都逐字引用造成它的 finding ID（HEAD 基準即 35 行，v26 後 40 行）。**義務區塊內為零違規**（那是另一條規則，本輪一度違反已修）。
- 🔴 治理測試既有紅基準（2026-09-13 實測）：19 個涉及 `brief_conformance_check` 的檔為 **30 failed／523 passed／3 skipped**；乾淨 HEAD worktree 為 **35 failed／512 passed**。根因＝隔離 repo 依賴複製清單缺 `scripts/quant_standard_check.sh`／`ticket_batch_check.sh`。`test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` 會**掛住**，跑治理回歸須排除。
- 🔴 改 SPEC／TODO 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次；grep **不得加排除條件**。
- 🔴 **不再擴建治理工具**（2026-09-12 定）；同型缺陷降級為具名殘留。
