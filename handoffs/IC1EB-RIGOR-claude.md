# 統計嚴謹度充分性 — Claude 獨立完整版(委員會三腿之一)

**Task-id**: ic1eb-rigor-claude(自產)| **日期**: 2026-07-09 | **對象**: docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md v2.1 + IC Gatekeeper 全統計面
**方法**: 獨立作答,未參照本輪 codex/composer 諮詢產出(其尚在跑)。

## Q1 檢定層:bar-level NW t 夠嚴謹嗎?
**結論:夠,且是計量經濟/量化業界的標準工具。**
- 重疊 horizon 預測性迴歸的顯著性,教科書處理=Newey-West(1987)/Hansen-Hodrick HAC;Fama-MacBeth 逐期係數序列配 NW 修正=因子研究文獻主流作法。本刀的 bar-level 貢獻序列+NW 即此結構(h-bar label 重疊→MA(h-1)→maxlags 硬下限,SPEC D-A)。
- 相對「更高級」的替代=stationary/circular block bootstrap 作主 kernel:非參數、對厚尾/秩統計量更穩,但慢、且對 block 長度敏感。SPEC 已將其列為**測試側驗證腿**(D-B,兩法同判斷言)——這是正確的成本/嚴謹平衡:主 kernel 解析式可 oracle 鎖死,bootstrap 提供獨立交叉驗證。
- 真正的嚴謹保證不是引用文獻,而是 SPEC §V M-A:**實測 size control**(高自相關 null 下假陽率∈名目 α 允收帶,帶外=FAIL)。這把「NW 夠不夠」從權威問題變成可證偽測試。

## Q2 多重比較層:BH-FDR 在高相關特徵下站得住嗎?(全案唯一真開放點)
**結論:BH 為 default 合理,但有一個必補的測試缺口+兩個該登記的選項。**
- BH 的理論保證要求獨立或 PRDS(正回歸相依);數百~上千個高度相關特徵(同族指標不同參數)之間,檢定統計量多為正相關→PRDS 大體成立是**文獻常見的實務判斷**(Benjamini-Yekutieli 2001 證明 PRDS 下 BH 有效),但不是我們資料上被證明的事實。
- 替代:①BY(任意相依下保證,但懲罰 ~ln(m),m=1000 時約 7.5×,功效損失大概率過度保守);②Romano-Wolf / Westfall-Young resampling stepdown(用 bootstrap 吃真實相依結構,功效最好,但控制的是 FWER 非 FDR=更嚴的準則,且要重抽整個特徵×統計量矩陣,工程成本高)。
- **我的裁決**:default=BH(業界因子篩選主流),但:
  1. **必補(freeze 前 SPEC 修訂)**:M-B 的 FDR 控制測試**必須含相關 null 特徵場景**(如 50 個由同一 latent factor 生成、pairwise ρ≈0.7 的 null),實測 FDR 仍≤α——把 PRDS 從假設變成本資料類型上的被測性質;帶外=BH 不可用,自動升級 BY。
  2. `significance.fdr.method` 為 enum(既有 `adjust_multiple_comparisons` 已支援 bonferroni/fdr_bh),**BY 一行可加**——登記為 config 選項;Romano-Wolf 登記 §N 另立(工程量大,待 BH 實測失守才升級)。

## Q3 策略層 data-snooping(White RC/Hansen SPA/DSR/PBO)
**結論:不屬本刀,另立 epic 登記。** 這些工具控制的是「在多個**策略/回測**中挑最好」的 snooping;IC Gatekeeper 是特徵篩選層。兩層都要,但混在一刀=scope 爆炸。應在 ROADMAP 回測/上線 epic 登記(與既有 stateful 參數盤點 epic 同層)。

## Q4 IC Gatekeeper 其餘統計面盤點
| 項目 | 判定 | 理由/處置 |
|---|---|---|
| ic_mean/icir/hit_rate/coverage 門檻 | **可接受(啟發式閘,非檢定)** | 從未宣稱是統計檢定;應在 docs 明標「描述性門檻」,不升級 |
| monotonicity/quantile returns | 可接受(描述性) | 同上;無推斷宣稱 |
| ic_decay 指數擬合 | 可接受 | 已有 fit_warning/r2 誠實標記 |
| grouped IC(regime 子樣本) | **低優先缺口** | 子樣本 IC 無 n/se 顯示,易過度解讀;建議後續加每組 n(1f/grouped schema 刀順手) |
| event tier 樣本判準 | 本刀已修 | α 語意顯性化(alpha_source/exploratory 標記,D-E) |
| cross_sectional t/p | 本刀已修 | D-H(含 horizon 丟失修復) |
| deep 模組(factor_return NW=False 等) | 已登記 §N 另立 | 不阻本刀 |
| 1c Net IC 量綱/1d attribution | 已排序後續刀 | 裁定順序③④ |

**總圖**:1e+1b 落地後,selection 主鏈的推斷核心(p 值生產→多重比較→消費)就是嚴謹的;殘餘項屬「描述性指標該標成描述性」與「後續刀已排」,無隱藏的推斷級缺口。

## Q5 總裁決
**RIGOR-VERDICT: AMEND: M-B 增相關 null 場景(必補)+fdr method enum 留 BY 選項(一行)+Romano-Wolf/策略層 snooping 入 §N/ROADMAP 登記;其餘照 v2.1 凍結。**
架構本身(kernel 可換、FDR 層獨立、SelectionScope 稽核)已為將來方法升級留好插槽——就算委員會日後改判 BY/RW,也是換方法參數,不是重做刀。

ASSUMPTIONS_VERIFIED: SPEC v2.1 內容(本人起草);adjust_multiple_comparisons 已支援 bonferroni/fdr_bh(statistical_validator.py:58-73 親讀);其餘為統計文獻慣例判斷(BY 2001/NW 1987/RW 2005 屬領域常識,未逐篇重讀)。
TESTS_RUN: 無(判斷型文件);M-B 擴充屬 SPEC 修訂,實測在實作階段。
STATUS: DONE
