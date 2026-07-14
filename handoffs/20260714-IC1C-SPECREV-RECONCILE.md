# IC1C SPEC 審查 RECONCILE(r1)— Claude 主編

task-id: IC1C-SPECREV | 日期: 2026-07-14 | 輸入: handoffs/20260714-IC1C-SPECREV-{codex,composer,grok}.md
verdicts: codex REJECT(7B) / composer REJECT(6B) / grok REJECT(4B) → **SPEC v0.1 退回改寫 r2**

## 修法裁決(三家 RULING)

| 委員 | RULING |
|------|--------|
| grok | B(嚴格執行=禁 net_ic 別名) |
| composer | B(scalar 路徑=B 子集) |
| codex | 第三案=B+「canonical 可交易報酬序列未建立前,net/breakeven/profitable 一律 unavailable+reason,禁以 IC 或現有摘要代填」 |

**Claude 裁決:採 B+codex fail-closed 收緊**(記 RULING-FINAL: B-strict)。理由:codex CODEX-1 實證現有 `ls_returns` 構造本身錯位(reset_index 位置相減),composer 建議的「export ls_return_series」會把錯位序列扶正為 canonical——**不可採**。canonical time-aligned factor-portfolio return series 的構造是獨立數值正確性工程 → **拆單獨票(1c-FR,排 1c 後)**,1c 本體=量綱修復+fail-closed+成本全棧接線。

## Finding 裁決表(全 17 筆;跨家合併同源)

| 合併主題 | 來源 | 裁決 | SPEC r2 落點 |
|----------|------|------|--------------|
| F1 factor_returns 來源不存在/型別不符/錯位 | CODEX-1+COMPOSER-1+GROK-1 | **ACCEPT** | Task 1.2 改寫:fail-closed(unavailable+reason);canonical series 拆 1c-FR 票;刪「net_mean 有限 float」e2e,改斷言 unavailable+reason |
| F2 orchestrator 模組間無資料通道 | COMPOSER-2 | **ACCEPT** | 1c-FR 票前置設計註記;1c 內 net_ic runner 顯式宣告依賴矩陣+skipped 語意 |
| F3 turnover 語意/×2 四腿重複計費/holding period | CODEX-2 | **ACCEPT** | 新 §T:定義 one-way/round-trip;quantile_turnover 已含雙腿→成本=`cost_bps×turnover`(去 ×2,附 turnover_semantics 欄);M2 mutation 改測「重複計腿」 |
| F4 5bps 三層 fallback+config_override 繞過+route 先 200 後驗 | CODEX-3+COMPOSER-4+GROK-2 | **ACCEPT** | Task 2.1 改寫:typed nested request+HTTP 邊界 422;刪 schema/YAML/analyzer 三處 5.0 預設;cost_enabled default=False;config_override 對成本鍵 API 層 reject;slippage_bps 刪或接入;cost_scenarios 去硬編碼 |
| F5 summary 三欄失定義 | GROK-3+COMPOSER-6(部分)+CODEX-6 | **ACCEPT** | Task 1.1 凍 summary 契約:刪 `avg_ic_loss_pct`→`avg_cost_drag_return`;`rank_correlation_gross_vs_net` 在無報酬序列時=null+reason;`profitable_count` 只計 evaluable,分母=evaluable_count |
| F6 net_ic 鍵必刪禁別名 | GROK-8+COMPOSER-6 | **ACCEPT(裁死)** | Task 1.1 明文:`net_ic` 鍵禁止輸出(含 cost_sensitivity 內);reporter/前端全改名 |
| F7 §G golden 白名單漏欄/可假綠/phase 生命週期 | CODEX-5+COMPOSER-5+GROK-4 | **ACCEPT** | §G 改:全 feature 全鍵集合 equality+獨立 canonical 公式重算全量比對(非抽 3)+NaN mask;G-OLD(Phase0)/G-NEW(Phase1 後)分層;JSON 禁 inf |
| F8 consumer-map 漏 10+ 處 | CODEX-4+COMPOSER-3+GROK-5 | **ACCEPT** | §C 補全清單(見 r2);`compute_net_ic_proxy` 同病→**納入 1c scope 一併刪/正名**(禁雙重標準);NetICChart turnover fallback 0.1 假值禁止 |
| F9 NaN→null DTO 契約 | CODEX-6 | **ACCEPT** | Task 2.1:DTO `number|null`+reason code;breakeven turnover=0 → null+reason(禁 inf) |
| F10 M1-M4 紙面 mutation/既有測試固化舊錯 | CODEX-7+COMPOSER-8+GROK-6 | **ACCEPT** | §V 重寫:property→oracle→具名 test→mutation probe 表;補 M5(5bps 復活)/M6(summary IC-vs-IC)/M7(config_override 繞過)/M8(turnover 重複計腿);「新建 vs 改寫」測試表逐檔列 |
| F11 timeframe 標籤不足/持有期≠bps 階梯 | CODEX-2(部分)+COMPOSER-9+GROK-7 | **ACCEPT(收斂版)** | Phase 3 改:輸出 turnover_semantics+cost_semantics;文件禁年化/禁跨 TF 直比;**持有期矩陣不入 1c**(依賴 1c-FR canonical series),記 1c-FR 票 |
| F12 幽靈 slippage_bps | GROK-9+CODEX-3 | **ACCEPT** | Task 2.1:刪除(使用者成本=單一 cost_bps 輸入,要 slippage 未來另議) |
| F13 案 A 永久封存條件 | GROK-10 | **ACCEPT** | §A 記:重提 A 須另附 σ 估計 PIT+交叉校準,不得混入 1c |

**REJECT/降級:無**——17 筆全收。無互相矛盾裁決;唯一分歧(composer「export series 可先做」vs codex「構造本身錯位」)依 codex 實證裁 codex 勝,composer 方案移入 1c-FR 票前置條件。

## 下一步
1. SPEC 改寫 r2(本檔裁決全落);2. 三家閉合重驗(原提出方重跑同反例,章程 §B8)+RECONCILE-STAMP;3. 戳記機檢 PASS 後生 TODO。

<!-- 委員戳記區:各委員 append 一行 `RECONCILE-STAMP APPROVED — <name> <date> sha256:<本檔改前 hash>` -->
RECONCILE-STAMP APPROVED — composer 2026-07-14 sha256:d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7
RECONCILE-STAMP APPROVED — grok 2026-07-14 sha256:d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7

## r2 輪閉合記錄(2026-07-14,Claude 補記)
- composer APPROVE(6/6 BLOCKING CLOSED)+STAMP;grok APPROVE(10/10 CLOSED,0 復開)+STAMP;codex REJECT(CODEX-3/5/6 PARTIALLY+CODEX-7 STILL-OPEN+CODEX-R2-1 phase 倒置)。
- **r3 裁決(全 ACCEPT)**:F14 佔位形狀三表示不相容(CODEX-6+GROK-R2-1+COMPOSER-R2-1)→新 §U discriminated union 唯一形狀;F15 鍵集合無確定 oracle(CODEX-5+GROK-R2-2)→§U 三套精確 profile(SKIPPED/GROSS_ONLY/COST_ENABLED);F16 phase 倒置(CODEX-R2-1)→cost_enabled/cost_bps schema 提前 Task 1.1,Phase 2 只做 API+前端,G-NEW/G-NEW2 分工重定;F17 override 漏 cost_enabled/cost_scenarios(CODEX-3)→config_override 對 net_ic_analysis 整節 reject;F18 mutation 紙面(CODEX-7)→§V 綁 測試檔:函式+同檔自證 probe+mutation_probe_check.sh(已確認存在);F19 用語誤導(GROK-R2-4)→Task 1.2 改「canonical series 未建立」;F20 compute_net_factor_return 去留(GROK-R2-3)→deprecated+batch_analyze 忽略注入。COMPOSER-R2-2(422 無獨立 bullet)併 F17 落 Task 2.1;COMPOSER-R2-3(summary 恒 0 UI 語意)併 §U profile+前端文案 Task 2.2。
- SPEC r3=v0.3;交 codex r3 閉合重驗(composer/grok 之 R2 findings 全為 NON-BLOCKING 且已落 r3,原 STAMP 維持,若 codex APPROVE 後將請兩家對 r3 delta 快速 concur)。

## r3 輪閉合記錄(2026-07-14,Claude 補記)
- codex r3:CODEX-3/5/6/R2-1 CLOSED;REJECT(4B)=CODEX-7 殘留(T4 前端無同檔 probe,checker 僅掃 Python)+CODEX-R3-1(union「一律輸出」vs profile 禁鍵自相矛盾)+CODEX-R3-2(cost_sensitivity 階梯 Phase 3 才定義=phase 倒置重現)+CODEX-R3-3(cost_bps/turnover 非有限無合法 profile,裸欄可產 JSON inf)。
- **r4 裁決(全 ACCEPT)**:F21 union 只約束「存在時形狀」,presence 由 profile 唯一決定;F22 階梯算法移 §T、Phase 1 實作,Phase 3 縮為零 schema 之 UI 註記(G-NEW2 byte 等值證明);F23 finite/range validator 三層強制(config/API/analyzer)+turnover 非有限→SKIPPED(reason=non_finite_turnover)+M10;F24 T4 同檔 vitest probe `test_mutation_m4_frontend_drop_cost`,並明文 Python checker 不覆蓋前端、TODO 須列 vitest 獨立驗收命令。
- SPEC r4=v0.4;交 codex r4 閉合重驗。

## r4 輪閉合記錄(2026-07-14,Claude 補記)
- codex r4:CODEX-7/R3-1/R3-2/R3-3 全 CLOSED;REJECT(2B)=R4-1(cost_bps=0 三處矛盾)+R4-2(三層 validator 只有 T1 probe)。
- **r5 裁決(全 ACCEPT)**:F25 cost_bps=0 非法——「無成本」唯一表示=cost_enabled=False,0 於 enabled 語意無意義,config/API/analyzer 三層一致拒絕(Task 1.1 邊界+§V 邊界目錄同步);F26 M10 三層各綁具名 test+各自同檔 probe(T1 analyzer/T2 API/T5=tests/phase24/test_deep_analysis_config.py config 層)。
- SPEC r5=v0.5;交 codex r5 閉合重驗。
RECONCILE-STAMP APPROVED — codex 2026-07-14 sha256:e3774b483965f66ca328fd5d6f4985de6cd905ad16ad1d465512dd46fbdb79cd
RECONCILE-STAMP APPROVED — composer 2026-07-14 sha256:d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d
RECONCILE-STAMP APPROVED — grok 2026-07-14 sha256:d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d

## 戳記
RECONCILE-STAMP: composer APPROVED 2026-07-14 sha256:ab910286af9a82058a2e57b880c3092ae3ebf580ff08041a6870e13a97680347 task:IC1C-SPECREV
RECONCILE-STAMP: codex APPROVED 2026-07-14 sha256:ab910286af9a82058a2e57b880c3092ae3ebf580ff08041a6870e13a97680347 task:IC1C-SPECREV
RECONCILE-STAMP: grok APPROVED 2026-07-14 sha256:ab910286af9a82058a2e57b880c3092ae3ebf580ff08041a6870e13a97680347 task:IC1C-SPECREV
