# fail-open SPEC — 雙家族 adversarial 彙整(兩輪,給使用者審閱)

> 對象:docs/FF_FAILOPEN_FIX_SPEC.md(v2)。審查者:Codex(GPT-5.5)+ Composer 2.5,各獨立。Claude reconcile。
> 稽核檔,不 commit。

---

## 第 1 輪 adversarial(對 SPEC v1)— 找到 4 BLOCKING + 修正 Claude §A 假設

### BLOCKING(兩家一致)
- **B3**:`_safe_execute` 根本無法實作「engine-partial vs 整層失敗」分流——engine 例外早在 layer 方法內被吞(`feature_factory.py:527`),caller 只見 DataFrame-or-exception。→ 需 typed 結果協議。
- **B1**:lazy 遷移抓不到真正殘缺的舊 artifact——現碼 V2 **已寫 `quality_status="complete"`**(`feature_storage.py:1529`),殘缺 artifact 是「被錯標 complete」而非缺欄。
- **B2**:現碼**雙層狀態**(run+artifact)+ 既有合法值 `empty_selection`(`:1057`)、`legacy`(`feature_reader.py:354`)超出 SPEC 的 `complete|partial|failed` enum。
- **§G**:golden 凍結時機錯(應 Phase0 動工前,非 Phase4)。

### Claude §A 被抓出的 3 個「假設當已驗證事實」(實測>假設事故型)
1. 「舊 manifest 缺 quality_status」→ **錯**:V2 已寫 complete(實碼)。
2. 「`_safe_execute` 可辨 engine-partial」→ **錯**:資訊流不支持。
3. 「ratio 門檻可分 warmup vs 異常 NaN」→ 技術上**不成立**(只能擋總量,不能分位置)。

### 範圍決策(使用者 2026-06-09 定)
四主軸 + **第5軸 validator 全樣本 winsor 洩漏**(`feature_validator.py:169`)納入。

---

## 第 2 輪 adversarial(對 SPEC v2)— 半數解決,半數仍破

> SPEC v2 已修:Phase0 golden、Task2.0 LayerExecutionResult、狀態模型、遷移偵測、第5軸、覆蓋漏項、frozen list、config contract、rollback。

### ✅ RESOLVED(兩家一致)
- **G-3 遷移偵測**:改用「缺 schema_version 或缺 expected/present/failed 欄」判 unknown(非看 quality_status 存在),能抓「已錯標 complete」的舊殘缺。
- **G-4 時序**:Phase0 凍結移到動工前。
- **G-6 覆蓋範圍**:combine/API restart/registry add 三點有 Task。
- **G-7 防假綠 frozen list**:`檔:line:原斷言:新行為:理由` + git diff 100% 對照。
- **G-9 rollback**:`unregister_group`(真實 API,含 shard 刪除)+ 集合相等斷言。

### ❌ STILL-BROKEN(兩家一致,High 信心)
| # | 仍破原因 | 修法 |
|---|---|---|
| **G-1** enum 不窮盡 | L3 CGSA streaming **成功回空 DF**(`:1136`)、L5 空有 5 成因、「全 engine 失敗」未定、L2 parallel 例外也被 `continue` 吞(`:1035`) | 加第6類 status(如 `offloaded_to_registry`)+ CGSA/L6.5/L5 映射表 + 全滅衍生規則 |
| **G-2** 聚合無演算法 | 沒定義偏序(`failed>unknown>legacy>partial>empty_selection>complete`?);`raw=complete+processed=empty_selection` 的 run-level 未定;writer 每寫 artifact 覆蓋 top-level(`:1550`) | 寫死 `merge_quality_status(artifacts)->run_status` 偽碼 + 原子 read-modify-aggregate + consumer 白名單 |
| **G-4** winsor golden 空洞 | Task2.5 改 winsor 值 vs Task4.1 凍結「全部正常值不變」= **自相矛盾**;Phase0 又無法凍結改前還不存在的 expected/present/failed 欄 | affected-column 排除 + winsor 路徑用獨立 PIT + 第二 causal baseline;Phase0 baseline 只含改前真有的欄 |
| **G-5** winsor 判準未形式化 | 「若必要改因果否則移除」無判準;validator winsor 現**無條件執行**(`:148`),不能因預設有 L6.5 就全域移除;因果 winsor 不冪等 | config 決策樹(L6.5 winsor on × validator winsor on × CGSA/non-CGSA × IC-First)→ 保留/移除/改因果;測「每條 config 路徑 ≤1 winsor」 |
| **G-8** flag 值未釘死 | `max_nan_ratio` =「Phase0 baseline 上界+裕度」但 **Phase0 驗收未要求輸出該值**(循環依賴);6 新 flag 落 FactoryConfig 還 API-only 未定;§C 指 `momentum/core/config.py` 但 FactoryConfig 在 `feature_config.py`(衝突) | Task0.1 產出 max_nan_ratio 預設值 artifact;釘死各 flag 所屬 model/API/TS 檔案 |

### ⚠️ NEW-ISSUE(兩家獨立都標)
- **Phase 依賴循環**:Task1.2 的 `_build_completeness_meta(layer_results,...)` 需要 Phase2 的 layer 結果,但 §P 說 Phase2 依賴 Phase1 → forward dependency。**修法**:reorder → 1.1 schema only → Phase2(2.0–2.6)→ 1.2 persist-meta → Phase3。
- **Task 2.0 規模膨脹**:改 6 個 layer 回傳型別 + L1/L2 engine 例外語義 + CGSA/multi-TF 衛星,單 commit 難回退(與「每 Phase 獨立 revert」張力)。**Composer 建議** TODO 拆 2.0a(contracts+L1)/ 2.0b(L2-L6+CGSA);**Codex 建議** 2.0 獨立成前置 Phase,明列所有 caller 遷移 + `result.data` unwrap。
- **Task 4.3** 文案退回「無 quality_status→unknown」,與 G-3 的新 predicate 矛盾,須一致。

### 兩家總評
- Codex:`STATUS: BLOCKED`——G-1/G-2/G-4/G-5/G-6/G-8/G-9 與 Phase 循環仍不足以安全派工。
- Composer:「B1/B3/B4 核心有進步;B2 聚合、全 pipeline 閉環、Phase 依賴、golden/winsor 交界仍不足以無歧義派工。**建議修 SPEC 後再派,不必整份重寫。**」

---

## 給使用者的結構決策(兩家獨立都指向)
**核心張力**:Task 2.0(LayerExecutionResult,改 6 個 layer 回傳型別)是大型跨切重構,被低估成 fail-open 任務的 sub-task。
- **選項 A**:把 LayerExecutionResult 協議**拆成獨立前置任務/PR**(自己的 SPEC+adversarial+實作+review),穩了再做 fail-open gating。每 PR 可獨立回退、blast radius 小。
- **選項 B**:第 3 次修訂維持單一大 SPEC(reorder phase + 補 6 blocker),一次派工。最徹底但單次回退難。
