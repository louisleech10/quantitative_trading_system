# GAP-1 TODO R2 受限複驗（R9）——22 條 closure ＋ J1 新 golden 實跑 ＋ 新增機制攻擊面

brief-kind: review

## 🔴 本輪範圍受限（收斂紀律；違反者之 finding 主委將逕列 RESIDUAL-OK）
上一輪（R8＝TODO 第一輪 adversarial）三家共 22 findings，主委**全數處置**（收斂檔六群集 J1–J6），
另主委自產 3 條 P0（§G／§V 數值級，三家皆未發現）。本輪**唯一任務**＝複驗處置是否真關閉，並攻擊**新增之機制**。
**不受理**新的一般性議題——除非該議題滿足「**不修就會使 B1–B4 產出數值錯誤或不可重現結果，且附可執行反例**」。

## 審查標的
- **TODO R2**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（就地修訂版；`template_check todo` PASS）
- **SPEC 延伸檔 A1**：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`（A1-1..A1-15；母 SPEC 定版不就地改，衝突以此為準）
- **母 SPEC**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（R8，未改）
- **收斂與處置**：`handoffs/reconcile/20260817-gap1-x-review-r8/synth.md`（群集 J1–J6＋22 條逐字附錄）
- **殘留登記**：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-1 待補完登記」（G1-R3／R7 理由已改、R8 收回為小票、新增 R9）
- 主委自產版：`handoffs/20260817-gap1-todoadv-r8-claude.md`；receipts：
  `handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.{py,log}`、
  `handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.{py,log}`

## 本輪任務（三段皆必答）
**段 A — 22 條 closure**：對**你家族**上一輪之每個 ID 判 `CLOSED`／`OPEN`／`PARTIAL`，並**重跑你的原始反例**
（codex 尤須重跑 P0-01 之 top-K probe 與 P0-02 之 `rankdata` 反例）。另兩家之 ID 可只在你有異議時評論。
仍 OPEN 者請答：可否作具名殘留帶進 TODO（yes/no ＋理由）。

**段 B — J1 三條數值處置之可重現性（🔴 必須實跑，不接受紙上判斷）**：
1. `alpha_detectable`（A1-1）：`mu = 0.01 * 0.15`（per-period SR 0.15）於
   `rng=np.random.default_rng(20260817)`、`M=rng.standard_normal((1200,50))*0.01`、`S=12` 之 PBO 是否 `< 0.30`？
2. 全噪音 band（A1-2）：同生成式之 PBO 是否落在 `[0.30, 0.70]`？band 放寬之理由（924 path 高度相關）是否成立，
   或你認為應改用「多 seed 平均」等更嚴形式？
3. `alpha_undetectable`（A1-1）：`mu = 0.01*1.0/sqrt(8760)` 是否 `> 0.40`？
4. §V-4 新形式（A1-3；champion 改由 OOS 選）是否**真的**會使 ① 或 ② 轉紅？（請實跑該 mutation）
5. Task 3.1 驗收⑨（A1-9）：`mean(max annualized SR) <= 1.0` 且與 `0.833943` 之 `rtol<0.05` 是否成立？
   主委已具名「per-seed 上界不成立（max=1.216377）」——若你認為 20-seed 平均仍不穩，請給你的數值。
可直接跑主委 receipt 腳本（`venv/bin/python handoffs/run_receipts/…-pbo-probe.py`，數分鐘）或自寫等價探針。

**段 C — 新增機制之攻擊面（本輪重點；新機制自己就是新攻擊面）**：
1. **AST wiring（A1-11／TODO Task 2.4）**：以 `ast` 取 `build_validation_section` 之組裝鍵集合 ＋ W3 三形掃描
   ＋ 非 `Constant` 一律 `[unresolved]` rc=1——有無**可執行的假綠路徑**（例如經 helper 函式組裝、`**dict` 展開、
   `dict(**kwargs)`、迴圈組裝、`setattr`）？若有，請給具體 Python 片段。
2. **`universe_scope`（A1-4）**：以「可觀測欄位＋Task 3.3 強制降級」取代 codex 要求之
   「一律非 ok／不可偽造 proof」是否足夠誠實？是否存在「呼叫方繞過降級」之路徑（如只讀 `pbo.value` 不看 `universe_scope`）？
   若你認為必須更嚴，請具體說明較嚴版之通過條件（且不得使 PBO 永不可用——違交付範圍 A）。
3. **例外分類（A1-8）**：`(OSError, json.JSONDecodeError, ContractViolation, ValueError)` 之集合是否恰當？
   `ValueError` 涵蓋 `assess_eligibility` 之參數驗證 raise ⇒ 是否會把「呼叫方傳錯參數」這種**程式 bug** 也吞成
   `reporter_failed`？若是，請給修法（收窄集合或改用自訂例外階層）。
4. **`n_rows_rejected`（A1-7）**：六欄計數是否自洽？`n_candidates_considered` 只算 schema-valid 列是否會與
   `n_is_lower_bound` 恆真之語意衝突？Task 2.3 conformance 之新斷言是否可證偽？
5. **Task 2.4 移至 B4 末（A1-11）**：新拓撲（B4 依賴 B3 3.3）是否使 §R「B3／B4 可獨立 revert」失效？
   若失效，處置為何（改 §R 或改落點）？

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（V13）。canonical ID `## <FAMILY>-R9-P<0-3>-<NN>`，
**本輪輪次=R9**（R1–R8 已用畢）。四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`）。
零 findings 時用 sentinel `## <FAMILY>-R9-P3-00`（body 須實質，禁空殼）。
段 A 之 closure 表與段 B 之數值表放 Verdict 段下，不佔 finding ID。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁蓋戳記**；只產你自己的 review 檔。
- 「函式/檔案尚不存在」不是缺陷（全票尚未動工）。
- 母 SPEC 與延伸檔衝突時**以延伸檔為準**；請勿把「母 SPEC 舊文字」列為 finding。
- `review-r7`／`review-r8` 之戳記於平行輪處理，**勿以「缺戳記」停工**。

## 本 brief 前提（逐條標）
fact-verified: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-17）
fact-verified: r8 收斂檔 completeness 22/22 全覆蓋（`completeness_check --synth … --lock …` rc=0，Claude 實跑）
fact-verified: J1 三條數值主張皆有 repo 內 receipt（PBO 三變體 0.6483／0.6158／0.5357；alpha 0.15 ⇒ 0.0054／0.0000；MinBTL mean 0.843077）
assumed: 22 條處置皆真關閉，且新增機制未引入新的假綠或不可達 gate ← 請攻（附可執行反例才算）
assumed: A1 延伸檔與 TODO R2 之間無新的抄寫漂移（欄位名／枚舉數／驗收編號）← 請逐項對證

## Time-box
優先序＝段 B（數值可重現）＞ 段 C（新機制）＞ 段 A（closure）。
**不受理**：使用者裁決（範圍 A／降級不硬擋／殘留三值規則）、前端樣式、治理機制設計、MinBTL 精確值、
DSR「同一 V」修法、C1 六條生產 bypass 之關閉（已具名殘留 G1-R4）、ledger 完整性之生產者側證明（已具名 G1-R9）。

## 產出
Verdict（可 Frozen／需修補後 Frozen／有根本缺陷需重作）＋ 段 A closure 表 ＋ 段 B 數值表（含你的實跑值）
＋ 段 C 五項逐項結論 ＋ canonical findings。收尾清 /tmp workdir（保留 claude-501）。
