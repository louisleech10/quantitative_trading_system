# R3 stamp review — Composer

Task: `fracdiff-maxlag-r3-stamp-composer-20260703`  
Input: `handoffs/20260703-FRACDIFF-MAXLAG-R3-RECONCILE.md`, `handoffs/20260703-FRACDIFF-MAXLAG-R3-COMPOSER.md`

## 載入核對

| 裁決項 | Composer 原意 | RECONCILE 對照 | 判定 |
|--------|---------------|----------------|------|
| D1 三約束 | (1) 禁「噪音/預期漂移」；(2) B1 idx508 vs 尾擾 2⁻⁷ 分 symptom；(3) 轉綠=storage epic 後去 xfail | §1 禁噪音文案；reason 僅錨 094044Z/2⁻⁷；D4 分列 idx508+ULP；「storage epic 修 codec 決定論後轉綠」 | ✅ |
| D2 | 單邊擾動契約 + d\* gate 為唯一驗收路徑 | §2 顯式單邊（full 擾/trunc 乾淨）+ receipt 須 match d\* gate 訊息 | ✅ |
| D3 | 含 MRFAIL 裁決案 2 預測更正 | §3② 明載「conv 修後尾擾 MR 轉綠」被 094044Z 推翻 | ✅ |
| D4 | 已確認根因（非假說） | §4 per-column codec 全窗選型 → idx508 NaN 翻面 + 2⁻⁷ ULP | ✅ |
| §5 使用者可見更正 | max_lag 已修；兩 MR 因 pre-existing storage 維持 xfail；轉綠時點=storage epic | 與 MRFAIL 裁決案 2/4 原文及 094044Z 實測一致，無粉飾 | ✅ |

## 戳記

`RECONCILE-STAMP: composer APPROVED 2026-07-03 sha256:8b0260a9a51aa031aff9b5c2ac5ff35744e509a03d56e8d21e97d579a633ebee task:fracdiff-maxlag-r3-stamp-composer-20260703`

```
ASSUMPTIONS_VERIFIED: reconcile_body_hash.sh 與 Codex 戳記 hash 一致；MRFAIL-RECONCILE 裁決案 2/4 原文已交叉
TESTS_RUN: bash scripts/reconcile_body_hash.sh handoffs/20260703-FRACDIFF-MAXLAG-R3-RECONCILE.md → 8b0260a9…
FAILURES_SEEN: none
SCOPE_CHANGES: append RECONCILE 戳記 + 本檔
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
