# Reconcile — 20260911-splitunify-b9-review-r29

**來源** 20260911-splitunify-b9-review-r29-codex.md, 20260911-splitunify-b9-review-r29-composer.md, 20260911-splitunify-b9-review-r29-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **O1 授權只驗鍵名 ⇒ 具名後任意改值**——「assumed1不成立；`--accep」 | P1 | CODEX-R29-P1-01 | 採納（🔴 **主委第三次宣稱「偏離委員修法但等效」，第三次被實跑否證**——該家具名後把 13 改成 999、rc=0。已逐字採其修法之可實作形式：授權須帶 `<key>=<old8>:<new8>`，digest 取該值 canonical JSON 之 sha256 前 8 碼 ⇒ 要授權就必須**先看過兩個值**並貼進命令列，CLI 自己編不出來；digest 不符、或列了未實際改變的鍵，皆拒。主委實跑複驗：只給鍵名 ⇒ rc=1 並指名格式不合） |
| **O2 錨點 regex 接受 SPEC 任意位置 ⇒ 非獨立信任根**——「assumed3不成立；helper改讀」 | P1 | CODEX-R29-P1-02 | 部分採納（**可實作的半已修**：錨點掃描收窄到 §V 區段，明文排除 HISTORY-BEGIN..END 與沿革節；主委實跑複驗該家探針——把新錨塞進 `HISTORY` 並同步換 v8 與旁檔 ⇒ rc=1 並指名 ANCHOR MISSING。🔴 **未閉合的半具名為殘留 `SU-RESID-V8-ATTEST`（`user-ruling`）**：該家自己也寫明「真正同 commit 防護另加受保護簽章／不可變 ancestor attestation」——那是**外部信任根**，屬新建治理工具，與 2026-09-12 使用者裁定「不再擴建治理工具」相斥；且繞過成本（改四個檔寫進同一 commit）低於合規成本（導入並維護簽章鏈），依「繞過成本 ≥ 合規成本即收」歸蓄意等價。殘留已帶可執行觸發條件與 owner，**誠實邊界寫明**：關閉前該論證的信任根實際是 code review 與 git 歷史） |
| **O3 人手時刻仍由 BASE／H1 推導 ⇒ 共因未除**——「assumed2不成立；`expecte」 | P1 | CODEX-R29-P1-03 | 採納（🔴 **主委 r28 之 assumed 又一條被否證**——該家把 `BASE` 平移 17 毫秒，人手值與實際值**一起移動**、對帳照樣相等。已逐字採其修法：13 筆人手時刻改為**不可變字面**，不由 `BASE`／`H1` 推導。主委實跑複驗：平移 17 毫秒 ⇒ 逐筆對帳轉紅並指名事件） |
| **O4 write-once 首建未接進 main 且非交易式**——「write-once首次建立未接到`ma」 | P1 | CODEX-R29-P1-04 | 採納（r28 只提供 helper，`main()` 在 v8 缺席時一律 rc=1 ⇒「首建成功」這一半**從來沒有可執行路徑**；且逐一 `O_EXCL` 在旁檔先存在時會留**半套狀態**。已加 --init-v8 分支接進 `main()`、先驗兩檔皆不存在、建立失敗則回收已建者。主委實跑複驗：移走兩檔後 --init-v8 **成功建立**並印出「請把 sha256 寫入 SPEC §V 錨點行」，隨後正確因 digest 與 SPEC 錨不符而 fail-closed） |
| **O5 第九個同步缺口（同型第九次）**——「assumed4不成立；第九個同步缺口仍」 | P1 | CODEX-R29-P1-05 | 採納（①SPEC §V `:270` 之註仍寫「現行 fixture **全部事件**皆 `decision == cutoff`，故為空心通過」——`bnd_shift` 補入後已過期，該家實跑得 equal=12、non-equal=`['bnd_shift']`；②TODO `Task 9.2a` **三處**仍要求該 node 輸出 1 xfailed，而 9.2b 落地後實跑為 1 passed。兩處皆已改，舊字面刪節保留。🔴 **同型第九次**——前八次見 v19–v23 沿革） |
| **O6 composer 零 findings、v23 APPROVED**——「本輪逐項核對後無finding；N1–N」 | P3 | COMPOSER-R29-P3-00 | 採納（判 proceed） |
| **O7 grok 零 findings、v23 APPROVED**——「本輪逐項核對後無finding——本家r」 | P3 | GROK-R29-P3-00 | 採納（判 proceed） |

### 本輪裁定

1. **composer 與 grok 零 finding 並對 v23 APPROVED；codex 五條 P1 全數採納**（O2 為部分採納，未閉合半具名為殘留）。**r28 四條由原提出方全數 CLOSED。**
2. 🔴 **主委 r28 自標之四條 assumed，本輪被否證四條**（全中）。加計 r28 那次，**主委在 r27／r28 兩輪自稱「偏離委員修法但等效」共三處，三處全被實跑探針否證** ⇒ **「等效」不得再由主委自我認定；偏離一律逐條交下一輪判**。本輪 O1／O3 皆改為**逐字採該家修法**，不再自創形狀。
3. 🔴 **O2 是本票第一次以「停在無法收斂處」裁定收束的攻擊面**：該家自己指出剩下那半需要外部信任根；依 2026-09-12「不再擴建治理工具」與 2026-09-11「繞過成本 ≥ 合規成本即收」兩項使用者裁定，歸具名殘留 `SU-RESID-V8-ATTEST`、標 `user-ruling`，**不得讀作已關閉**。
4. **SPEC 進 v24**，新 body sha256 為 bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c ⇒ v23 戳記失效須重簽。回歸六路 **736 passed、0 failed、0 xfailed**；四個探針主委皆實跑複驗會擋。
5. 🔴 **同型第九次（O5）**：連續九輪皆有「契約改了、舊段沒同步」。⇒ **`Task 9.3` 動工前置再加一條**：register 重掃 receipt 除列出全部落點外，須**逐段附上該段是否與現行契約一致之判定**，不得只列行號。
6. **下一步**：派 `review-r30` 做 O1–O5 閉合再驗證 ＋ 對 v24 新 body 三家重簽；齊備後進 `Task 9.3`（批次 **B9D**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R29-P1-01
**斷言**: assumed 1 不成立；`--accept-value-changes` 只驗 key 名，任意既有值仍可被明確旗標改寫。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902
**碼證**: 無旗標 temp probe rc=1 且值不變；具名旗標 rc=0、`g4_per_symbol_n {'ETHUSDT': 13} -> {'ETHUSDT': 999}`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:616
MUTATION: temp-copy main golden，改 `actual["g4_per_symbol_n"]` 為 `{"ETHUSDT":999}`，執行 `main(["--write","--accept-value-changes","g4_per_symbol_n"])`；修法/可行性：改用 review-bound、不可由 CLI 自行新增的 exact old/new digest changeset，現有 `_changed` 可在 `write_text` 前逐項比對，並保留合法重凍的明示 changeset。
## CODEX-R29-P1-02
**斷言**: assumed 3 不成立；helper 改讀 SPEC 雖移除第二份常數，但 regex 接受 SPEC 任意位置且 SPEC 可與 v8/sidecar 同一變更同步替換，故並非獨立信任根。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902
**碼證**: 原 v8 不變、SPEC 不變時 rc=1；temp SPEC 只在 HISTORY 放新 anchor、同步新 v8+sidecar 時 rc=0；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:435
MUTATION: temp SPEC 的 HISTORY 寫入新 `V8_BASELINE_SHA256` 並同步替換 v8/sidecar，執行 `_assert_v8_baseline_intact()` 得 `N2_SAME_COMMIT_REPLACED_SPEC_RC 0`；修法/可行性：parser 限定 §V 範圍並拒絕外部 literal，真正同 commit 防護另加受保護簽章/不可變 ancestor attestation；anchor 讀取集中於 `_read_v8_anchor_from_spec`，一次修訂可加兩層測試。
## CODEX-R29-P1-03
**斷言**: assumed 2 不成立；`expected_decision_at_ms` 與實際 decision 共同由 `BASE`/`H1` 生成，整批共因位移仍會兩欄相等。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; tests/momentum/Analysis/test_splitunify_golden.py#21e737d7f23e
**碼證**: `BASE += 17` 後仍 `N3_BASE_SHIFT_AFTER_EQUAL True`、13 rows、delta `[17]`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:145
MUTATION: 將 `m.BASE` 平移 17ms，重建 index/plans/keys，觀察 `before_equal=True`、`after_equal=True`；修法/可行性：將 hand timestamps 改為不依賴 BASE/H1 的逐筆 immutable literals，現有 dict 對帳不變，該 mutation 即可轉紅。
## CODEX-R29-P1-04
**斷言**: write-once 首次建立未接到 `main`，且兩檔逐一 `O_EXCL` 會留下半套狀態；v8 缺失時 `--write` 直接 fail，不符合 TODO 9.5 首建成功邊界。**來源摘要**: scripts/freeze_splitunify_golden.py#c8c5a46f6804; docs/SPLITUNIFY_TODO.md#df8037f51f4a
**碼證**: clean helper first-create rc=0/pair=True，但 `main --write` 缺 v8 得 rc=1、`V8_CREATED False`；sidecar 預存時 helper rc=1 且 `V8_EXISTS True`；CODE-ANCHOR: scripts/freeze_splitunify_golden.py:522
MUTATION: temp golden 移除 v8/sidecar 後執行 `venv/bin/python scripts/freeze_splitunify_golden.py --write`，再以預存 sidecar 呼叫 `create_v8_baseline_write_once`；修法/可行性：在完整性 gate 前接明確 init-v8 分支，先驗兩檔皆不存在並以交易式 pair create/失敗回收，補 clean、partial、main-missing 三測試。
## CODEX-R29-P1-05
**斷言**: assumed 4 不成立；第九個同步缺口仍在：SPEC §V:270 說 fixture 全部 decision=cutoff，但現況有 `bnd_shift`；TODO 9.2a:570/574/590 仍要求已完成 B9C 的 node `xfailed`。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1d21d7384902; docs/SPLITUNIFY_TODO.md#df8037f51f4a; scripts/freeze_splitunify_golden.py#c8c5a46f6804
**碼證**: fixture probe 得 equal count 12、non-equal `['bnd_shift']`；TODO node 實跑 `1 passed` 而非要求的 `1 xfailed`；CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:270
MUTATION: 執行 `venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`，觀察 `1 passed`；修法/可行性：SPEC 改寫為 12 equal + `bnd_shift` non-equal 的 active assertion，TODO 改為 B9C 完成後常規 `1 passed`，一次文件修訂可閉合。
VERDICT: blocked
BLOCKED-BY: CODEX-R29-P1-01,CODEX-R29-P1-02,CODEX-R29-P1-03,CODEX-R29-P1-04,CODEX-R29-P1-05
CLOSED: CODEX-R28-P1-01,CODEX-R28-P1-02,CODEX-R28-P1-03,CODEX-R28-P1-04
ASSUMPTIONS_VERIFIED: r28 四條原反例均 CLOSED（無旗標值閘 rc=1；anchor/檔案篡改 rc=1；+1ms gate 會列出 mismatch；TODO:273 現為 decision 越界 raise）；r29 assumed 1/2/3/4 均不成立；自立詞表 scan 逐段結論：SPEC C3/§G/§P/§V/§N 與 current contract 一致，§V:270 是唯一 stale contradiction；TODO §0/§B/Task1–2.3/3–4/9.1/9.2/9.2b–9.5/§D/§E 皆一致，Task9.2a:563–590 為唯一 stale xfail contradiction。
TESTS_RUN: `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`, rc=0；focused pytest golden+derive → 126 passed；r28 targeted → 4 passed；required node → 1 passed；doc_format SPEC/TODO rc=0、todo_spec_crosscheck rc=0、spec_v_task_ref rc=0；body hash after stamp → `52efba2e...`, rc=0；r29 temp probe outputs as above。
FAILURES_SEEN: 不存在的 `scripts/spec_todo_precheck.sh` → rc=127；首版 temp harness 僅因 `/tmp` 路徑 `relative_to(REPO)` traceback，repo 未變更，修正後 probes 完成；stamp checker rc=1 僅因本 task 尚待 register-output provenance，非產品測試 failure。
SCOPE_CHANGES: 僅新增本交件檔及在 SPEC `## 戳記` 末尾 append codex r29 stamp；未改程式、SPEC 正文、TODO、根 HANDOFF 或 data_cache；本輪 `/tmp/r29-*` workdirs 已由 TemporaryDirectory 自動清空，保留 `/tmp/claude-501`；既有 shared logs/sessions 未刪除。
NUMERIC_OR_SCHEMA_IMPACT: 本輪 review 未修改 runtime、golden、數值或 wire schema；提出的修法不代表已落地輸出變更。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r29-codex.md
STATUS: DONE
## COMPOSER-R29-P3-00

**斷言**: 本輪逐項核對後無 finding；N1–N4 閉合探针全 CLOSED，v23 body 可重簽。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d` rc=0；`pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → **140 passed** rc=0；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK` rc=0；四探针 `python scratchpad/r29_composer_probes.py all` → PROBE1-4 皆 rc=1、N1 全鍵繞法 rc=1；換詞表 awk+grep（必答 4）無第九處 live 互斥。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#52efba2e077a; handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md#ddcd66f3

doc-literal-only；信心度=High。assumed ① 與 codex 字面不等價但機械閘可證；②③ 殘餘共因／同 commit 攻擊面已碼內具名，不升級為 P1。

---

## GROK-R29-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 r28 為零 finding sentinel 無反例可重跑；N1–N4 四探針皆轉紅如預期；assumed ①字面不等效但 `_stale_allow` 否證全鍵繞法、②③ 殘餘共因／同 commit 面已具名且非靜默放行、④ 自立詞表無第九處 live 互斥；v23 body 可重簽；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `52efba2e077a973d6facb3264bf0daf83c8b36542dcb36097d5145a64c03595d`；`doc_format_precheck` SPEC／TODO → rc=0／0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py` → **140 passed**；`venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；N1 未具名改值 refuse＝True、全鍵 allowlist stale refuse＝True；N2 缺錨 rc=1、write-once 再建 rc=1；N3 +1ms mismatch＝13、`BASE` 移位 G-4e 綠但主檔 MISMATCH keys＝5；詞表 `grep` live 互斥＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R29-BRIEF.md#3788979f5e94; docs/SPLITUNIFY_SPEC.D-002.md#52efba2e077a; docs/SPLITUNIFY_TODO.md#df8037f51f4a; scripts/freeze_splitunify_golden.py#c8c5a46f6804; handoffs/reconcile/20260911-splitunify-b9-review-r28/synth.md#ef36f3052935

---

