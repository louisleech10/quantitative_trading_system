# GAP-3 事件型 SPEC R2 閉合驗證＋殘餘 sweep — codex；target: `docs/GAP3_EVENT_SPEC.md` @ `21135434`; sha256=`9f63e290e89a1dde96b44c217866d01d0113b0dc47f19b5acd0a7e356459f5bf`; R1 findings=8; R1 synth=15/15、X1–X13。
RECHECKS: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0；`git show 21135434:docs/GAP3_EVENT_SPEC.md | shasum -a 256` 與工作樹 hash 相同。
## R1 findings 閉合表
CODEX-R1-P0-01 NOT-CLOSED（offset form 已定；entry_at/price 映射仍缺）→ CODEX-R2-P1-01；證據：D1/D2/B2.1 probe。
CODEX-R1-P1-02 CLOSED；證據：`rg -n 'label_value|missing_label_value|不重算' docs/GAP3_EVENT_SPEC.md` → D1-3/B2.3 一致且缺值固定 unavailable。
CODEX-R1-P1-03 NOT-CLOSED → CODEX-R2-P1-02、03；證據：`sed -n '121,125p;179,185p'` 仍無實際門檻公式且 schema 僅 a/b/c。
CODEX-R1-P1-04 CLOSED；證據：`sed -n '121,129p'` → T8/T9/T10 條件必填、availability、不得以 meta 補洞。
CODEX-R1-P1-05 CLOSED；證據：`sed -n '201,203p;205,254p;299,304p'` → B2/B4.1 必需輸入及 macro/micro/cluster/degraded/LOSO 共通約束。
CODEX-R1-P1-06 CLOSED；證據：`sed -n '190,199p'` → B1.6、as-of、manifest hash、warmup/NaN、因果 golden 均有 task/驗證。
CODEX-R1-P1-07 NOT-CLOSED → CODEX-R2-P1-04、05；證據：`sed -n '356,370p'` → M1–M12 仍以 TODO 展開 receipt，M8 CI 還是類公式。
CODEX-R1-P1-08 CLOSED（循環 scope 已拆除）；另見新 CODEX-R2-P1-06 的 B1.0/B3.2 validator 矛盾。
## X1–X13 寫回忠實性／新錯誤
X1/X2/X3/X4/X5/X6/X7/X8/X9/X10/X11/X12/X13 的處置文字均有寫回；X1/X4/X8/X13 分別留下 entry 映射、classifier schema/threshold、mutation receipt、control-kind scope 缺口，非 synth 掉項。
## CODEX-R2-P1-01
**斷言**: R1 P0-01 只閉合了 t₀−k 的 offset representation；`entry_at` 與五種 `entry_price_semantic` 到實際 bar/price 的唯一映射仍未成為可驗收契約，故 B2.1 的 `entry` 仍可由 agent 自行解讀。 **碼證**: `rg -n 'entry_at|entry_price_semantic|next_open|decision_bar_' docs/GAP3_EVENT_SPEC.md` → D1-1 有值集、D2-1 有 `entry_at` invariant，但 D2-4 receipt 不含 `entry_at`/entry price，B2.1 僅寫「entry 依契約語意」；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS, rc=0（只證錨點）。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：補齊每個 semantic 的 bar identity/open-close price、`entry_at` 推導與 receipt oracle，並納入 k=0/k>0/next-open 邊界。
## CODEX-R2-P1-02
**斷言**: R1 P1-03 未閉合：AR-2 仍沒有 direction-aware signed-return 的精確公式、答案窗聚合、a/b/c 門檻的實際單位/預設值與 contract schema；實作者仍須發明分類規則。 **碼證**: `sed -n '121,125p;179,185p' docs/GAP3_EVENT_SPEC.md` → 僅見「門檻/單位/預設值」占位與 a「不續漲」/b「震盪」/c「反向」，沒有數值或公式；驗證只要求 exact boundary，未給 boundary oracle。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：在唯一 JSON SoT 寫死公式、單位、預設、window aggregation、所有 boundary/conflict fixtures，否則 B1.5/B2.2 不可重現。
## CODEX-R2-P1-03
**斷言**: X4 導入的 `unclassifiable` 沒有納入 `counterexample_kind` 的契約值集或獨立 derived/output 欄；schema 只列 a/b/c，但分類器與分層報表又會產生並消費 `unclassifiable`，可導致 validator reject、遺失或誤納分母。 **碼證**: `rg -n -C 2 'counterexample_kind|unclassifiable' docs/GAP3_EVENT_SPEC.md` → line 123 為 `(a/b/c)`，lines 183–185 產生 `unclassifiable`，line 42/220 仍以 `counterexample_kind` 分層；無 output schema/closed-set 定義。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：明確將 `unclassifiable` 放入契約或另立 derived classifier result，並固定 validator、分母與持久化欄位語意。
## CODEX-R2-P1-04
**斷言**: R1 P1-07 的 mutation contract 仍未逐條可執行：M1–M12 沒有各自的 command、fixture/input digest、baseline receipt 與 exact expected output；「TODO 展開」不能作為本輪 SPEC 的可證偽 gate。 **碼證**: `sed -n '356,370p' docs/GAP3_EVENT_SPEC.md` → line 358 將 digest/逐條命令延後 TODO；M3/M7/M9–M12 沒有明確 baseline/fixture digest/命令，僅寫紅或 `rc!=0`。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：每個 M 項補可執行命令、真實/固定 fixture digest、baseline output、mutation diff、expected rc/output；再由 TODO 逐字展開。
## CODEX-R2-P1-05
**斷言**: M8 的 `|stat| < z/sqrt(n_test)`「類」CI 式不能作為 AUC、PR-AUC、conditional IC 的共同 chance-level oracle，且不是 exact 判定；它可能把壞 oracle 判綠或把正確結果判紅。 **碼證**: `sed -n '172,174p;358,370p' docs/GAP3_EVENT_SPEC.md` → B1.4/§V 對全統計套同一近似式，文字明寫「類」且未以 AUC=0.5、PR-AUC=prevalence、IC=0 的 metric-specific null/variance 定義；`template_check` 仍只回 PASS。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：按 statistic_kind 固定 null、seed、class/prevalence-aware CI 或 permutation quantile，並寫 exact pass/fail oracle。
## CODEX-R2-P1-06
**斷言**: X13 的 scope 拆分留下 validator 矛盾：B1.0 宣告 v1 只實作 `user_labeled_*`，但 B3.2 在同一 v1 SPEC 啟用 `platform_same_trigger_rule` 並要求產出直接通過 B1.0 validator；B3.2 可能被自身 validator 拒絕。 **碼證**: `rg -n -C 2 'control_kind|platform_same_trigger_rule|v1.*user_labeled|validator' docs/GAP3_EVENT_SPEC.md` → lines 122、277–278 同時出現兩條要求，沒有 validator mode/version boundary 或 accepted-value exception。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：明確把 platform_same_trigger_rule 納入 B1.0 accepted schema，或將 B3.2 產出 validator profile 與 v1 import profile 分開並加整合 oracle。
## Verdict：需修補後才能進三家 RECONCILE-STAMP＋使用者白話閘
六個 P1/MAJOR 缺口仍可直接由 SPEC probe 證偽；無 P0，但未修前不能宣稱 R2 閉合或派 TODO/implementation token。
ASSUMPTIONS_VERIFIED: target commit/hash；R1 8 findings 逐條重跑；X1–X13 逐段對照；template_check PASS rc=0。 TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0；sed/rg probes → 上述行號與輸出。
FAILURES_SEEN: six unresolved SPEC findings, no command/test failure. SCOPE_CHANGES: no code/SPEC edits; only requested review artifact created. NUMERIC_OR_SCHEMA_IMPACT: no runtime change; findings require contract/schema/test-oracle clarification. HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r2-codex.md`.
STATUS: DONE
