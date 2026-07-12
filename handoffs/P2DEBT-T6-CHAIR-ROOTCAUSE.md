# P2 債票 6 主委根因分析(獨立版,交委員審 + Composer 起草 SPEC/TODO)
Task-id: p2debt-t6 | Chair: Claude(Opus 4.8) | Date: 2026-07-12 | 大小: 中(RISK-HIT a 相鄰,純測試側)

## 現象
main@492c4cc 上 26 個既有紅(C-4 已裁非票 2 引入):
- api 23 nodeid:tests/api/test_ic_deep_analysis.py(3 FAILED:test_full_analysis[_endpoint/_with_deep_analysis_config])
  +test_ic_analysis_api.py+test_export_api.py 共 20 ERROR。
- service 3:test_ic_analysis_service.py cross-sectional(C-4/composer 補記,horizon 家族)。
根因訊息一致:`InvalidInputError: label horizon cannot be resolved from column: label`。

## 根因(主委實測,可證偽)
1. 生產 `momentum/Analysis/ic_filter_orchestrator.py:279 _resolve_label_horizon_from_column`:
   `re.fullmatch(r"return_(\d+)", name)` 才回 horizon;裸 `label` → raise。註解明示「無法證明單位換算時 fail-closed」。
   此為 1e/1b 委員會修過的 **xsec `_label` horizon 丟失** 資料正確性護欄(記憶 project_ic_phase1_decisions/ROADMAP 1e)。
2. 生產落盤永遠用 `f"return_{horizon}"`(ic_filter_orchestrator.py:2134),**從不產出裸 `label`**。
3. 失敗測試 fixture 用舊命名:tests/api/test_ic_deep_analysis.py:118 `_write_labels_h5(..., ["label"])`;
   test_ic_analysis_api.py:89、test_export_api.py:109 同;test_ic_analysis_service.py:123 `"label": [...]`。
4. 這些測試 label 值是 `rng.normal` 合成噪音(test_ic_deep_analysis.py:113),欄名無真 horizon 語意
   → rename 不改測試斷言意義,只對齊生產契約。

## 修法方向(主委建議,交委員 adversarial 確認)
- **改測試 fixture 命名 `label`→`return_<N>`**,N=各測試 request/config 宣告的 horizon(合成噪音,任何合法 N 皆語意中性,但須與 request horizon 一致以免 alignment/purge 錯)。
- **絕不弱化生產 resolver**:弱化=重開 1e/1b 已封的 horizon 單位歧義洞,違反 Data Truth 鐵律。
- 範圍:tests/api/test_{ic_deep_analysis,ic_analysis_api,export_api,ic_analysis_service}.py 的 label 命名點。
  可能另有 service cross-sectional 需 `_label` 後綴語意(composer 補記提到);Composer SPEC 須逐 nodeid 盤點確認。

## 委員 adversarial 必獵(防「為綠而綠」)
1. rename 的 N 是否與該測試 request 宣告 horizon 一致?錯 N → alignment 錯但可能仍綠 → 須驗。
2. 有無任一失敗測試其實在測「應接受 label」的真實 API 契約(反證主委「純測試殘留」假設)?
   —— 主委已查生產落盤只出 return_N,但委員請獨立反駁。
3. service cross-sectional 3 紅是否同根因,或另有 `_label` 前綴/後綴語意差異?
4. rename 後須全 26 nodeid 轉綠 + 不得動生產碼 + 不得弱化 resolver 正則。

## 驗收預期(VERIFY-EXEMPT:doc-example:p2debt-t6-rootcause;初判敘述,後被 epic 取代)
26 個 nodeid 全綠;grep 確認 momentum/api 生產碼零變更;resolver 正則不變;
V6 hermetic(票2)重跑 V6_NO_NEW_RED 之基線可同步縮減(23→少;票6 閉合後更新 v6_baseline_bad_nodeids)。

## 交辦
Composer 起草 docs/P2DEBT_T6_LABELHORIZON_{SPEC,TODO}.md(實作型初稿)→ 雙家族 adversarial → reconcile → 實作(Codex)→ 雙審 → 驗收。
