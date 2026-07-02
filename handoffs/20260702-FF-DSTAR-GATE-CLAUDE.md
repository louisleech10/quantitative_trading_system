# FF fracdiff 截斷 MR d* gate 失敗 — Claude 獨立分析（待 Codex/Composer 挑戰）

## 事實（實測）
- B2 回歸(P0-FF-2 全鏈截斷 MR,單TF)真跑:8 passed / **2 failed** = `test_fracdiff_truncation_invariant`、`test_fracdiff_tail_perturbation_invariant`(receipt 20260702T042627Z-ff-b2-regression,2:17:16)。
- 失敗點:`_assert_d_star_gate`(ff_truncation_mr_helpers.py:1108)——精確相等比對 full vs trunc 每欄 d*;mismatch 樣本 `close_statistics_LINEARREG-INTERCEPT_13_Log1p 0.4844 vs 0.4688`(差 ~1/64 網格)。
- **非抽-helper 回歸**:`_assert_d_star_gate` 邏輯與 c94c850 原版逐字相同(git show 比對)。
- HANDOFF(07-01)載「B2 回歸尚未跑」→ 這是**首次真跑**,揭露 gate 從未驗證能否過。
- 記憶 project_dstar_first500_optionA:d* cross-window selection 不穩(Jaccard 0.2-0.43),run 自洽無洩漏但勿跨窗比;固定參考 d* = 未來 epic。project_stateful_param_audit:d* whole-window fit 是須持久化的 stateful param。

## Claude 判斷（供挑戰）
d* gate 斷言「截斷不改 d*」,但 d* 是**逐窗/逐run 校準**參數,截斷=換窗→d* 本就會漂(文件已定)。故此 gate 測的是**現行 fracdiff 設計不保證的性質**;在 d* 持久化(productionization epic)前,它**幾乎必然失敗**,非真 look-ahead、非 helper 回歸。

**連帶問題**:d* 差 → fracdiff transform 係數差 → fracdiff **欄值**也會差。故整個「fracdiff 截斷不變量」在 d* 逐窗浮動下**根本無法成立**(不只 d* gate,值 gate 對 fracdiff 欄同樣被 confound)。

## 待決（委員會,勿 solo）
1. 這 2 個 fracdiff 截斷測試在 d* 持久化前**是否本就不該存在/該 xfail**(附 epic 引用)?還是有辦法測「給定同一 d* 下 fracdiff 截斷不變」(如固定 d* 參考餵兩跑)?
2. d* 逐窗漂在**截斷情境**是否藏真 look-ahead(whole-window fit 用到未來),還是純良性 non-determinism(run 自洽)?——這關乎 P0-FF-2 截斷 MR 對 fracdiff 欄的效力。
3. 其餘 8 passed(非 fracdiff)是否足以證明抽 helper 行為不變、P0-FF-3 可收 WIP(把 fracdiff 2 項獨立為 d* epic 待辦)?
4. 修向選項:(A) xfail 2 測 + 引 productionization epic;(B) 餵固定參考 d* 給兩跑再比 fracdiff 值(真測截斷不變);(C) 從截斷不變量排除 d*-依賴欄,另立 d* 專測。

## 要求
Codex/Composer 各獨立判 1-4 + 挑戰我「gate 測了設計不保證的性質」的判斷是否正確(會不會其實藏真洩漏)。三方收斂才定修向。
