# 第 1 批決策簡述（給使用者）｜2026-06-12

## 一句話
HANDOFF 第 1 批動工前，實測推翻了 d* cache 項的前提（已抽出留你決策），其餘 5 小修經 Codex adversarial 判「需重作」後**升級為大任務**重寫 SPEC，走 Codex 實作 + Composer review + 雙家族 adversarial。

## 發生了什麼（時序）
1. **§A 事實驗證**（鐵律：實測 > 假設）：6 項逐一用 grep/真實 run 自驗。
2. **發現 1**：「非 CGSA d* cache 接線」前提錯——真相是 fracdiff 在非 CGSA path 因欄名 regex 整體靜默失效（不是 missing_context）。修復會改非 CGSA 數值輸出，命中 (a)(b)(d) → **喊停，待你決策**，詳見 `docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md`（A 修復對齊 / B 顯式化現狀 / C 棄用非 CGSA path；我建議 A 但可延後排程）。
3. 其餘 5 小修先按你拍板的中型管線寫了 SPEC/TODO，派 Codex adversarial。
4. **發現 2**：Codex 判「有根本缺陷需重作」（7 BLOCKING/7 MAJOR/2 MINOR，`handoffs/20260612-batch1-followup-adversarial-codex.md`）。最重要的一條：**分級錯了**——N6 動 NaN quality gate 觀測量、N3 動 winsor 數值參數來源、改 4 個共用檔，按 CLAUDE.md 規則命中 (a)(b) 應為大任務。我接受，按鐵律「命中高風險原則→當大辦」升級，未靜默沿用中型。

## 我替你做的技術決策（你可否決）
| # | 決策 | 理由 |
|---|---|---|
| 1 | 分級改**大**：Codex 實作 + Composer review + 雙家族 adversarial | Codex BLOCKING #1 + CLAUDE.md 規則；原「中型 Composer 實作」的拍板前提（不命中 a-d）已不成立 |
| 2 | N6 fallback 語義定一套：producer 必產 warmup-aware nan_ratio；消費端缺鍵→warning+沿用既有保守 fallback | 消除規格自相矛盾（BLOCKING #2）；fail-closed 方向不變（寧可誤標 partial 不漏標） |
| 3 | N6 共用函式 ownership 定死在新 `utils/nan_stats.py`，O(1) 累積器重用既有 nan_mask | 解 BLOCKING #3（循環依賴）+ MAJOR #10（streaming hot path 記憶體） |
| 4 | N3 不新增 min_periods config 欄位，validator 與 L6.5 共用同一 resolver 公式（252→63 兩邊本就一致） | 解 BLOCKING #4 + MAJOR #12（同名不同義）；預設行為 byte 不變由 golden 保護 |
| 5 | N7 不動 manifest 持久化契約（裸 `L{n}`），只在 result.metadata 邊界統一為 `L{n}:{tf}` | 避免 schema version bump / migration（MAJOR #8）；舊資料零影響 |
| 6 | Golden baseline 改由獨立 freeze script 在實作前單獨 commit；測試缺檔=FAIL | 解 BLOCKING #5（自我認證 oracle） |
| 7 | 回歸基線修正為 **78 passed**（Codex 實測；原文件寫 77 是沿用 Batch4 舊數） | BLOCKING #6 |

## 風險與回退
- 4 個 Phase（resource / quality-metric / winsor-config / metadata）各自獨立 commit，單獨可 revert；Golden FAIL 不 merge。
- 數值影響面：N3/N6 預設行為設計為 byte 不變（golden + 既有 failopen 78 測試雙保險）；唯一語義變更=N6 不再把 warmup NaN 誤判 partial（修 bug，雙向斷言防修鬆）。

## V3 增補決策（雙家族 adversarial round2 後，2026-06-12）
| # | 決策 | 來源 |
|---|---|---|
| 8 | all-NaN 欄 abnormal=total_nan（V2 我寫 0 是錯的，會弱化 gate）；oracle 由 freeze script 在改動前凍結 | Codex r2 B1 |
| 9 | winsor 注入定案 **per-call 參數**（`validate_factory_output(..., winsor_window=)`），拒 constructor/setter；`window=0` 必 raise 禁靜默變 252 | Codex r2 B2（Composer P7 建議 setter，被 per-call 否決：避免共享 mutable state） |
| 10 | N7 組裝點補上 legacy L7（:3325-3326）共三處，用冪等 canonicalizer；failure_reasons 按扁平字串規則插 tf | Composer P1 + Codex r2 B3 |
| 11 | N6 增**真實 kline gate**（BTCUSDT/12h 切片，slow、禁 skip）——合成 registry 測試保留為精確單元層 | Codex r2 B4 + 驗證保真度鐵律 |
| 12 | perf gate 改「freeze script 同機基準比對」（×1.15/×1.10）+ accumulator O(1) 結構斷言，不加 production flag | Codex r2 B5 + Composer P6 |
| 13 | T5 scope 補 scripts/ 2 個消費者；grep gate 擴 scripts/ | Composer P4 |

## 你需要做的
- **無阻塞事項**：本批 5 小修按上述決策繼續，不等你。
- **待決策（不急）**：d* cache/fracdiff 的 A/B/C 三選一（FINDING 文檔 §5）。
