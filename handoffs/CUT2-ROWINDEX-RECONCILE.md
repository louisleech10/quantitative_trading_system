# CUT2 row_index attach — 三方數據正確性簽核 Reconcile

> task-id: cut2-rowindex-signoff　|　reconcile 作者: Claude　|　日期: 2026-07-07
> 對象改動: `momentum/FeatureEngineering/feature_library.py` (`_attach_row_index`) + 測試 + SPEC/TODO

## 三方 Verdict(各自獨立實跑,產出檔 + harness task log 佐證)

| 家族 | Verdict | 產出檔 | harness task |
|------|---------|--------|--------------|
| Claude(實作+自驗) | PASS | 本檔 + 13 passed VERIFY:20260706T165905Z-cut2-rowindex-regression | — |
| Codex(adversarial) | PASS | `handoffs/CUT2-ROWINDEX-REVIEW-codex.md` | be2e6uc7j |
| Composer(資料正確性) | PASS | `handoffs/CUT2-ROWINDEX-REVIEW-composer.md` | b13by0la3 |

**三方一致 PASS,零 BLOCKING finding。** 兩位委員各自在真實 `data_cache/features/` 上獨立重現 G-1(值守恆)/G-2(時間軸 byte-equal)。Codex 另以**語義時間 oracle**(DayOfWeek/HourOfDay/IsWeekend 特徵 vs 貼回的 index,9 個 run 0 mismatch)交叉驗證列序無錯位——比我原本的抽樣值守恆更強的獵漏。

## Finding 逐項處置(所有 NON-BLOCKING)

| ID | 摘要 | 處置 |
|----|------|------|
| ADV-CODEX-1 / ADV-COMPOSER-1 | attach 窄且值守恆,列序未被證偽 | 確認,無需動作 |
| ADV-CODEX-2 | 語義 oracle 0 mismatch 交叉驗證列序 | 確認,強化信心,無需動作 |
| ADV-CODEX-3 / ADV-COMPOSER-3 | 中毒 ingest cache 無自動 invalidation | **本環境已清乾淨(掃描 0 poison)**;cache 版本化/失效屬運維硬化,**登記 follow-up epic**,不阻本刀 |
| ADV-CODEX-4 / ADV-COMPOSER-4 | retarget 測試偏離 SPEC §G-3 字面「completed」 | **已修**:更新 SPEC §G-3 + TODO 對齊 retarget(斷言在失敗邊界);三方確認對本 finding 忠實、未放寬既有斷言 |
| ADV-CODEX-5 / ADV-COMPOSER-5 | 1d 頻率地圖缺口 | **同意 deferred**:無真實 1d run 可驗,盲加違「實測>假設」;1d IC 會 fail-closed raise 非 silent 洩漏。SPEC §N 已登記 |
| ADV-CODEX-6 | `tests/golden/l65/test_inventory.txt` 被 scoped pytest 收集 clobber(conftest.py:108 自動重寫) | **已修**:`git checkout` 還原該 golden(非本刀改動,是 scoped 測試收集副作用) |

## Follow-up 登記(不阻本刀)
- IC ingest cache 版本化/timestamp 校驗(防殘留中毒 h5 被 exists-gate 重用)。
- `tests/conftest.py:108` scoped pytest 收集會 clobber L6.5 golden inventory——測試基建 smell,另議。
- 1d `EXPECTED_FREQ_BY_TIMEFRAME` 補值(需真實 1d 已物化 run)。
- full-analyze(218k 特徵>17min)完成驗收 → 「79 合成 IC 測試換真實資料」epic(慢測 mark)。

## RECONCILE-STAMP 說明
三方零 BLOCKING、各自獨立 PASS(佐證:兩委員輸出檔 + harness task log be2e6uc7j / b13by0la3 + gate audit)。
初次審查派工誤設 `--risk high` → 觸發 `--adversarial` 前置 → 因審查輸出檔當下未存在而 `waived`,連帶跳過 `committee_dispatch` 登記(我的流程錯,非制度捷徑)。**已改用正確模式補走機器戳記回合**:以 `dispatch.sh --task-id`(emit committee_dispatch)重派 Codex、Composer 對本 reconcile append `RECONCILE-STAMP`,序列化寫入(codex→composer,防同檔並發)。委員 stamp 語義=已審 Claude 的實作腿 + 本 reconcile,忠實無漏。

## 戳記
（Codex、Composer 依序 append 於下方;body-hash 範圍=本行以上。）
RECONCILE-STAMP: codex APPROVED 2026-07-07 sha256:22153e820bf0a70a25885ef554cf7968e43a87348e842e80fa3fc0367c4d36b5 task:cut2-rowindex-signoff
RECONCILE-STAMP: composer APPROVED 2026-07-07 sha256:22153e820bf0a70a25885ef554cf7968e43a87348e842e80fa3fc0367c4d36b5 task:cut2-rowindex-signoff
