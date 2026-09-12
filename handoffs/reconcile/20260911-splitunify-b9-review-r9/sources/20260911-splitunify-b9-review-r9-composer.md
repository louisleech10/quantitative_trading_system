# SPLITUNIFY D-002 閉合輪 R9 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R9  
family: composer  
findings-round: R9  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第九次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R8 十四條歸八群 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md` |
| brief fact-verified: `_oracle_membership` docstring 逐字「無因果關係／不 import 投影」 | **fact-verified** | `sed -n '133,138p' scripts/freeze_splitunify_golden.py` |
| brief fact-verified: §N 已新增 `SU-RESID-9A-UI`（grep-c=3） | **fact-verified** | `grep -c 'SU-RESID-9A-UI' docs/SPLITUNIFY_SPEC.D-002.md` → 3 |
| brief fact-verified: 第九次修訂 obligation／format rc=0 | **fact-verified** | `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0 |
| brief assumed: (G-4c) 同步改寫 oracle 與 allowlist **等效** | **assumption，本輪否證** | 見必答 2／R9-P1-01：兩邊同錯 G-3b 仍綠 |
| brief assumed: 步驟 0 前置條件**窮盡**重疊 | **assumption，部分否證** | Task 9.2b 規則已寫步驟 0，但 §V 無 early/late 斷言（R9-P2-04） |
| brief assumed: `SU-RESID-9A-UI` 觸發條件可機械判定 | **assumption，本輪否證** | 無腳本／gate 檢查 `api/` 新 `run()` 呼叫點（R9-P2-03） |
| brief assumed: K2 四處同批改完 | **assumption，部分否證** | L137 目標句仍寫「終端使用者看得到」（R9-P2-02） |

## 必答 1–5（成對立場）

**1. 本家 R8 finding 是否閉合**

| ID | R8 斷言 | 第九次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R8-P1-01 | G-4a 不可機械歸因 | (G-4c) 同步改寫 oracle + (G-4d) 三附帶 | **未閉** | G-4c 不擋 correlated error；G-4d②③未進 §V（R9-P1-01／P1-02）；L127 仍與 G-4a 互斥（R9-P1-03） |
| COMPOSER-R8-P1-02 | 9A 終端零揭露／metadata 不可達 | L142–149 殘留 + §N；L142 刪 9A 完成條件 | **部分閉** | L142 已改；L137 目標句未改（R9-P2-02）；L149 又把第三層決策推遲（R9-P1-04） |
| COMPOSER-R8-P1-03 | §N 未登記 + blocked-by 須指名票 | §N `SU-RESID-9A-UI`；K3 駁回票號前提 | **登記已閉；類別仍爭議** | `grep -c SU-RESID-9A-UI`＝3；類別依據見必答 3／R9-P2-01 |
| COMPOSER-R8-P2-01 | 七反向 mutation 無具名測試 | §V L225 指名七檔 + 「測試存在前不得宣稱已閉」 | **規格已改、測試未閉** | `rg '誤改為複合鍵' tests/` → 0；誠實邊界已寫，實作面仍空 |
| COMPOSER-R8-P2-02 | C6 (6.2) 與 Task 9.4 baseline 互斥 | L92 v9 更正為事件級物化下 n_test＝樣本數＝事件數 | **CLOSED** | `sed -n '92p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R8-P2-03 | M-SU-D2-02／03 與殘留互斥 | mutation L232–233 改指 summary／metadata | **CLOSED** | 對讀 mutation 表 L232–233 與 §V L218 |

**2. 攻 (G-4c)：同步改寫 oracle 是否真能取代 allowlist？**

**立場**：**不能等效**。G-3b 只驗「投影 vs 第二份實作」是否一致；Task 9.2b 要求「同步」改寫 oracle 時，**同一類 off-by-one／漏寫步驟 0** 會在兩邊同時出現，G-3b 仍綠，而合法換錨與實作寫錯在輸出上同型。

**具體構造（碼證）**：`index_ms=[100,200,300,400]`、`train_last_ms=200`、`test_start_ms=300`；事件 `e` 滿足 `decision_at_ms=feature_cutoff_ms=200`（**非** `decision!=cutoff` 邊界 fixture，故 G-4d③ 測不到）。若投影與 oracle **同步**把 `decision_at_ms <= train_last_ms` 誤寫成 `<`：

```
venv/bin/python probe → bug=True proj=purged oracle=purged g3b_pass=True correct=train
```

（完整腳本存 `/tmp/composer-r9-g4c-probe.txt`；邏輯：`freeze_splitunify_golden.py:346-350` 只做集合相等，不比對 cutoff-anchor 平行鍵或 allowlist。）

**與 allowlist 差異**：allowlist／cutoff 平行鍵從 fixture **獨立算出**允許 diff 集合；G-4c 把第二份實作綁在同一 human/agent 改動批次，無法否證「兩邊都改錯成同一個錯」。

**修法（可行）**：保留 G-4c 作為 regression，**另加** (a) 重凍前腳本雙跑 cutoff vs decision 判側，產出 `allowed_side_diff_events.json`，重凍後 `actual_diff` 須集合全等；或 (b) 保留 `g1_membership_cutoff_anchor` 平行鍵一 Phase。G-4d② 須在 §V 寫成對 `decision==cutoff` 事件與 v8 舊鍵逐值比對，不能只有 §G 散文。

**3. 攻 K3 駁回：`BRIEF_REVIEW_TEMPLATE` 是否適用於 SPEC §N？**

**立場**：**不適用**；主委引錯權威。

**碼證**：`templates/BRIEF_REVIEW_TEMPLATE.md:71` 的 `reason_code` 閉集服務的是 brief 內 **`unverified-未查` 六欄表**（同檔 L62–72），不是 SPEC §N。SPEC 殘留的 canonical 規則在 `templates/SPEC_TEMPLATE.md:108-109`：「值**只允許三種**」且 `blocked-by:` 後須接 **`<具體依賴（檔/層/前置票）>`**——不是「現行架構」四字。`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:47-48` 對 §N 殘留同要求三值且理由須成立。

**R-BRIEF-1 不可類推**：同檔 L171 雖寫 `blocked-by` 現行派工架構，但**具名依賴**是 `scripts/committee_run.sh:103-118`（可 grep 的檔:行），不是「零 grep ＝架構限制」。`SU-RESID-9A-UI` 的阻塞是「`api/` 無 `EventSamplePipeline.run` 生產呼叫」——這是**能力缺口／未派接線 Task**，較貼近 `needs-research: 生產投影接線設計` 或 `blocked-by: <具名 wiring Task ID>`，而非 brief 表的四值閉集。

**4. 攻 K4「成本超標時改交付範圍」**

**立場**：**又是自己沒擇的二擇一**（同型 R7 J3／R6 Task 9.1 二擇一），**現在就該擇定**。

**碼證**：L149 寫「若成本超出 9A…應改為只交付前兩層並併入 §N」——把決策推給實作者；但 §V L218 仍 **硬性** `ASSERT metadata.split_unify 帶該鍵`；§N L267 又把 `metadata.split_unify` 列為「本延伸交付」第三層；`M-SU-D2-03` 仍綁 exact-key 契約測試。三處同時存在 ⇒ Agent 不知要做五處同步還是推遲。

**該擇哪邊**：依 L149 自己的成本論述與「揭露成本極低」定位，**現在定案只交付前兩層**（`build_event_keys.discarded` + `EventSplitPlan.summary`），第三層併入 §N（例 `SU-RESID-9A-META`），刪 §V／mutation 03 對 metadata 之 discarded 斷言，避免 IC 路徑上五處 exact-key 半套。

**5. K1–K8 修訂引入的新問題／殘留衝突**

| 群 | 複驗 | 新問題 |
|----|------|--------|
| K1 G-4c/4d | §G 已寫 | G-4d②③未派 §V／mutation（P1-02）；L127 與 G-4a 互斥（P1-03） |
| K2 殘留落地 | §N 有 UI 殘留 | L137 目標句未同步（P2-02） |
| K3 類別 | 部分採納 | 引 brief 範本而非 SPEC 範本（P2-01） |
| K4 metadata 成本 | 五處已列 | 二擇一未決 + §V 仍硬 ASSERT（P1-04） |
| K5 步驟 0 | Task 9.2b L182 已寫 | §V 無 early/late（decision=50/450）斷言（P2-04） |
| K6 (6.2) | L92 已更正 | 無 |
| K7 具名測試 | §V L225 已指名 | 測試仍不存在（延續 R8-P2-01，已誠實標註） |
| K8 mutation 02/03 | 已改指 summary/metadata | 與 P1-04 第三層未定案連動 |

## §1 必查摘要（11 類）

1. **矛盾**：L127 vs G-4a/4c；L137 vs L142；L149 vs §V L218 — **有**
2. **漏項**：G-4d②③、K5 early/late §V — **有**
3. **不可測**：G-4c 散文紀律；SU-RESID 觸發 — **有**
4. **quant 假設**：G-4c correlated error 可固化錯側 — **有**
5–11. 其餘 — **無新增 BLOCKING**

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

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `grep -c 'SU-RESID-9A-UI' docs/SPLITUNIFY_SPEC.D-002.md` | **3** |
| `rg 'EventSamplePipeline\(\)\.run' api momentum --glob '*.py' \| rg -v test` | **0** |
| G-4c 探針（見上） | **g3b_pass=True 且 correct=train 可同時成立** |
| `rg 'decision_at_ms != feature_cutoff\|零位移' tests/ docs/SPLITUNIFY_SPEC.D-002.md` §V 段 | **僅 §G，無 §V** |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R9-P1-01,COMPOSER-R9-P1-02,COMPOSER-R9-P1-03,COMPOSER-R9-P1-04
CLOSED: COMPOSER-R8-P2-02,COMPOSER-R8-P2-03,COMPOSER-R8-P1-03

ASSUMPTIONS_VERIFIED: R8 六條逐條對讀第九次修訂；G-4c 探針；SU-RESID grep；obligation rc=0；§N／brief／SPEC 範本對讀  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r9-composer.md --family composer`（交件前自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
