# Handoff
**Agent**: Claude(Fable 5) | **Time**: 2026-07-16 | **Branch**: main→feat/ic-la1-p1-impl | **狀態**: 🔒 **LA-1 SPEC v0.4.3 + TODO v2.3 雙凍結**→ ▶ B0 實作派工(Grok)

## 🔒 雙凍結紀錄
- **SPEC** `docs/IC_LA1_SPEC.md` **v0.4.3**(file sha `41499dae…`);凍結檔 `handoffs/LA1-SPEC-FREEZE-RECONCILE.md`(canonical 戳記 task `20260716-la1-freeze5-*`,register-output×3,`reconcile_stamps_check.sh` **PASS** body sha `3dd1e94c…`);史料 `-history.md`。freeze 5 輪:codex 連 3 輪 REJECT 抓真洞(B1.3 邊界舊句/§A 基數 8→12〔grok 同抓〕/migration 幽靈列+`:23` 非 nodeid)。
- **TODO** `docs/IC_LA1_TODO.md` **v2.3**(sha `316d4c90…`):R1 三家 adversarial(8 BLOCKING:B0 入口契約/predeclare 流程/骨架雞蛋/偽碼壓縮/oracle 重編/測試域矛盾/int80 raise 錯/覆蓋表假陽性)→v2→R2(composer/grok 可 Frozen;codex 3 殘)→v2.1-2.3 codex closure 鏈(R3/R4/R5)→**FROZEN-OK**(`handoffs/LA1-TODO-ADV-R5-codex.md`)。reconcile=`handoffs/LA1-TODO-ADV-RECONCILE.md`。
- **實作合約**:Grok 實作(依額度)/Codex+Composer 雙家 review(機器閘門 review_quorum_check.sh)/每批過 review 即 commit/B4 三方 DATA-CORRECT。批次 DAG=B0→{B1,B2,B3}→B4(TODO §B)。

## ▶ LA-1(P1 look-ahead 收尾)當前進度
- **✅ 開場稽核**:HANDOFF vs repo 抓 2 處漂移(P1-1 行號實為 ic_engine:1106-1107;開關真名=`by_regime`+`include_regime_analysis` 雙閘)。
- **✅ 聯合偵察(4方)**:`handoffs/LA1-RECON-{claude,codex,composer,grok}.md`+`LA1-RECON-SYNTHESIS.md`。洩漏三點實跑證實(Grok+Composer 真 kline receipt;codex HDF5 逾時斷路器誠實 BLOCKED)。委員修我 8 處(B1 percent/fraction 單位陷阱=BLOCKING 等)。
- **✅ 使用者裁定×2**:①P1-1b(`regime_detector:306` kmeans fallback 同族洩漏)併入 LA-1 ②**P1-1c(kmeans 主路徑 `_align_labels:257` 全期命名洩漏,R1 codex 抓)併入 LA-1 完整修**;XGBoost 未開始使用可動;**LightGBM 0 hits 不受影響**(caller 圖實跑)。
- **✅ SPEC 4 輪 adversarial**:v0.1→R1(三家 8 BLOCKING:D1 guard 空殼/P1-2 退化非 NaN/紅標雙軌/kmeans 非 control/空 vol/真值表/xgboost caller/DAG)→v0.2→R2(B1.3 因果區間自相矛盾〔我寫錯,composer 37/50 flip 實證〕/G-A schema 不可實作/**P1-2 第三層洩漏=future-label availability 污染 dropna 後分箱,codex N3**/B0 覆蓋)→v0.3→R3(name_map same-model namespace〔codex+grok 雙家獨立抓〕/prefix 契約互斥/carrier 未鎖/migration 表矛盾)→**v0.4**(template PASS)。
- **▶ 進行中:freeze-stamp R4**(背景 task `20260716-la1-freeze1-{codex,composer,grok}`):v0.4 body sha256=`98b9b740…f53cdbb`,戳記收 `handoffs/LA1-SPEC-FREEZE-RECONCILE.md`。全 APPROVED → `reconcile_stamps_check.sh` 機檢 → 凍結。
- **audit 鏈**:`handoffs/LA1-SPEC-ADV-{R1×3,R2×3,R3×3}+RECONCILE×3`(gitignored 本地)。

## SPEC v0.4 關鍵定案(docs/IC_LA1_SPEC.md)
- **scope**:P1-1(regime rule 全期分位)+P1-1b(fallback 同病)+P1-1c(kmeans fit+命名 Segment-causal 完整因果化,偽碼鎖 SPEC)+P1-2(long_short qcut PIT+Policy-Strict require_full_q+feature 原時序分箱)+P1-3(fallback loud:root `analysis_status` 單名+G-A2+禁內層 persist+5 bypass oracle+carrier 鎖死)。FR/`_fit_global` §N exclude。
- **DAG**:B0(baseline 含 kmeans/xgboost legacy)→{B1 regime,B2 long_short,B3 fallback loud 並行}→B4(golden/歸因 5-wash/三方 DATA-CORRECT)。
- **golden**:control deep-equal(regime OFF/LS OFF/非觸發 fallback;kmeans**不是**control);修改路徑歸因表(class {P1-1,P1-1b,P1-1c,P1-2,P1-3-obs}+exact path/index/old-new)。dataset receipt:BTC/1h rows=20352 sha₁₆=1c93c379…;ETH/12h rows=1696 sha₁₆=00d1ee98…。

## 凍結後下一步(照 LA-0 範本)
①`reconcile_stamps_check.sh handoffs/LA1-SPEC-FREEZE-RECONCILE.md codex,composer,grok` PASS ②TODO 起草(Claude,`docs/IC_LA1_TODO.md`,template PASS+SPEC ID 覆蓋表)③TODO 三家 adversarial→凍結 ④逐批 Grok 實作+**Codex+Composer 雙家 review**(機器閘門 `review_quorum_check.sh`;實作者不自審)⑤每批過 review 即 commit(建議另開 branch `feat/ic-la1-p1-impl`)⑥B4 三方 DATA-CORRECT。

## 📌 慣例/環境(沿用)
- Grok=實作者(`--sandbox workspace`);reviewer=Codex+Composer;gate.sh dispatch 開 token;committee 產出 register-output。
- 委員 /tmp workdir 收尾清理(保留 claude-501);pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 勿 commit。
- pre-existing 7 紅(redirect state-leak 測試順序污染)非本 epic 另票;IC 過渡期跑 feature_filter 別全量(OOM,funnel deferred 整個 Gatekeeper 完成後)。

## ⚠️ 未 commit
docs/IC_LA1_SPEC.md(治理中,凍結後隨治理產物一起 commit)、docs/API_SPECIFICATION.md(session 前既存尾空白)、docs/IC_LA1_SPEC 相關 handoffs(gitignored)。docs/workflow_diagram.png+scratch/(session 前既存,非本工作)。
