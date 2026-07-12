# P2DEBT-T6 reconcile(SPEC/TODO 定稿,派實作前)
Task-id: p2debt-t6 | Date: 2026-07-12 | Chair: Claude(Opus 4.8)

## 審查鏈
- 起草:Composer SPEC/TODO R1(逐 nodeid 盤點,有效 horizon=5)。
- 雙家族 adversarial:**Grok=APPROVE**(CE-1 殘差:釘 return_5、勿宣稱 horizon 數值正確);
  **Codex=BLOCK**(同 CE-1 但升為阻擋:純 rename 無法證 N=5,要求補 falsifiable oracle)。
- 事實面兩家一致:default_horizon=5、三 API request 無 override、欄名 N 為權威、B1 stub 不走 orchestrator、裸 label 是殘留。

## 主委裁決(分歧=嚴重度;採「adversarial 勝簽核」+ 反廉價綠燈)
Codex 的 BLOCK 有理:純 rename→return_5 而零斷言,未來誤改 return_1 會**靜默通過**(合成噪音+斷言只查 HTTP/結構)。
但補「end-to-end horizon/purge 數值 oracle」需生產碼暴露 metadata=**出 scope**(effective_horizon 僅進 log,ic_filter_orchestrator.py:258)。
故採 **bounded 測試側可證偽守衛**,兩家立場交集:

### 定稿 scope(R2 delta,派 Codex 實作)
1. **rename 釘死 `return_5`**(A1 test_ic_deep_analysis.py:118 / A2 test_ic_analysis_api.py:89 / A3 test_export_api.py:109),**禁任意 N**。
2. **加 falsifiable 守衛(測試側,floor 必做)**:於共用 fixture 或一測顯式 `assert label_names == ["return_5"]`
   → 誤改 return_1 時**硬失敗**非靜默綠(直接關閉 CE-1)。
3. **best-effort 強守衛(可選,不擴 scope)**:若能以 caplog 乾淨捕捉 "Resolved label horizon" INFO 的 effective_horizon==5
   (test_full_analysis 走真 orchestrator),加之;若 log 捕捉脆弱則略,不得為此改生產碼。
4. **B1 出 scope**:test_ic_analysis_service.py:123 stub 不走 resolver 且已綠;Task 2.4 skip 改碼(僅 receipt)。
5. **計數修正 23 非 26**:scope=API 23 nodeid(service cross-sectional 3 已綠,含 append return_1)。
6. **契約敘述修正**:縱向 HDF5 fail-closed(拒裸 label)與**橫截面 in-frame 接受裸 label→structural horizon=1**是兩份契約;
   收尾報告勿寫「生產一概不接受 label」。
7. **誠實邊界**:收尾僅可稱「契約命名對齊 + return_5 釘死 + 誤改可證偽 + 23 API 轉綠」;
   **不得**宣稱「end-to-end horizon/purge 數值正確」(那需另立有 oracle 的票)。

### 禁止(同 R1)
禁動 momentum/ api/ 生產碼、禁弱化 resolver 正則、禁刪既有斷言、禁降門檻。

## 驗收
23 API nodeid 轉綠 + fixture label_names==return_5 斷言存在且誤改 return_1 會 FAIL(可證偽 receipt 正反極性)
+ 生產碼 grep 零 diff + 票2 v6_baseline 由 Claude 閉合後縮減(impl 只提案)。

## Verdict
Verdict: APPROVE(條件式)— Codex BLOCK 以 §定稿 scope 第 2 點 bounded falsifiable 守衛化解;Grok scope-bound 保留。
待 Grok+Codex append RECONCILE-STAMP 確認本裁決化解各自立場後派實作。

## 戳記
(待 grok / codex append)
RECONCILE-STAMP: grok APPROVED 2026-07-12 sha256:5a8f96403a34b779d4586361d773a31d5d44f45d0a999e8d03685df13ca5827f task:t6-recon-grok
RECONCILE-STAMP: codex APPROVED 2026-07-12 sha256:5a8f96403a34b779d4586361d773a31d5d44f45d0a999e8d03685df13ca5827f task:t6-recon-codex
