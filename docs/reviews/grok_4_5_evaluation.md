# Grok 4.5 委員會初步評測 — Round 1（唯讀）

> 日期：2026-07-09　|　範圍：能力測試 + code review 抓漏測試 + 委員會品質測試（皆唯讀，不含 §8 T-D 正式寫入資格認證）
> 對應計畫：`~/.claude/plans/rosy-whistling-nebula.md`　|　工具：`grok` CLI（官方，已裝登入，`grok models` 確認 `grok-4.5` 為預設模型）

## 方法論誠實邊界（先講清楚，避免誤讀）

- **能力測試（A/B/C）**：2026-06-03 舊紀錄（Codex/Composer 21/21）的原始題目文字沒有保存下來，只有分類名稱。本輪是**同類別新出題**，不是逐字重跑，跟舊紀錄只能做方向性對照，不是嚴格同題 head-to-head。
- **Code review 測試、委員會品質測試**：三方（Grok/Codex/Composer）當場同時對打，同一題、不互看，是真正的 head-to-head。
- **Opus 4.8 / Fable 比較**：沒有 CLI 調用管道，未做真實調用。下方相關評語是我（Sonnet 5，本專案 ORCH 文件裡的「主委」角色）自己的質化判斷，不是實測分數。
- 所有 pass/fail 都是我自己寫的 hidden test / 已知正解去對，不採信任何 CLI 自報的 STATUS。

---

## 1. 能力測試（isolated /tmp，held-out grader = Claude）

三題：A 區間合併變體（含「touch 不合併」陷阱）、B 除錯（5 個真實注入 bug）、C 表達式解析器（含除以零/括號不匹配等錯誤處理）。

| 題 | Grok 4.5 | Wall-clock |
|---|---|---|
| A（區間合併）| **9/9 通過**，含 touch-not-merge 邊界陷阱 | 23s |
| B（除錯）| **12/12 通過**，5 個注入 bug（floor→ceil、無 clamp、無 ValueError、has_prev 用未 clamp 值）全部正確揪出修好 | 27s |
| C（解析器）| **17/17 通過**，含除以零、括號不匹配、非法字元、遞迴下降解析器（stdlib only，未用 eval）| 82s |

**總計 38/38**。跟兩個月前 Codex/Composer 的 21/21（不同題目但同類別）方向性對照：**沒有看到能力落差**——同樣是零漏測、正確處理邊界陷阱。

---

## 2. Code Review / Adversarial 抓漏測試（三方同時對打）

合成一個 6 函式的 feature-engineering 檔案，注入 3 個仿真實歷史漏洞模式的 bug：
1. `compute_range_volatility`：docstring 說 high-low，實作卻用 close-open（仿真實 BETA/CORREL 餵錯欄位事故）
2. `compute_zscore_feature`：`rolling(center=True)` 造成前視洩漏（look-ahead leakage，最危險的一類）
3. `compute_pct_change_flag`：`.fillna(0)` 把缺值靜默當成「無變化」（違反不弱化 NaN gate 原則）

| | Grok 4.5 | Codex (GPT-5.5) | Composer 2.5 |
|---|---|---|---|
| 抓到 3 個真 bug | ✅ 3/3 | ✅ 3/3 | ✅ 3/3 |
| 誤判正確函式為 bug | 0 個（sma/ema/volume_ratio 皆判 CORRECT） | 1 個爭議項（`compute_ema` 被標 MAJOR bug，理由是 pandas ewm 跨 NaN 延續狀態——這是 pandas 預設行為非我注入的 bug，屬於可辯護但非本次設計的額外發現） | 0 個 |
| 嚴重度判斷 | 正確（leakage 判 BLOCKER，其餘 MAJOR） | 正確 | 正確，且多切出 pct_change_flag 的第二個子問題（gap 整列被刪掉時 pct_change 仍會算出大跳動，比單純 fillna(0) 更深一層） |
| Wall-clock | 122s | 54s | 97s |

**小結**：三方在「抓到真漏洞」這件事上打平（100% recall）。Grok 4.5 是唯一**零誤判**的（Codex 多標了一個有爭議的額外項；不算幻覺，是真實 pandas 行為，但不是本測試設計的目標 bug）。Composer 在這題展現最深的洞察（抓到 gap 整列被刪除 vs NaN-in-row 的差異）。速度上 Codex 最快，Grok 最慢但差距在可接受範圍（2 分鐘內）。

---

## 3. 委員會品質測試（read-only 諮詢，三方對打，held-out 已知正解）

題目：FracDiff d\* 該不該做 walk-forward 重估 + 該不該加 d_min floor（拿掉答案的原題，複用 2026-06-17 真實三方研究的問題本體）。

**已知正解**（`project_dstar_walkforward_rejected.md`）：d\* 確實會漂（pooled std≈0.25），但漂移不轉化下游價值（真實 n=232 配對實驗 dIC_mean=-0.002，WF 較佳僅 42%）；d_min floor 因 magic number/over-difference/需未來資訊而一併否決；結論=兩者皆拒，除非有新的真實 L1/L2 配對 OOS 證據。

| | Grok 4.5 | Codex | Composer |
|---|---|---|---|
| d\* 會漂的判斷 | ✅ 正確方向（但強調估計噪音佔比高，未量化到真實 0.25 的幅度——這是合理的，因為它沒有資料存取權） | ✅ 同上 | ✅ 同上 |
| 「漂移≠下游價值」核心洞察 | ✅ 明確抓到，並提出用合成 null 分布做假設檢定的方法論（跟真實研究的嚴謹度相當） | ✅ 明確抓到 | ✅ 明確抓到，額外指出「d 是離散網格不是連續值」的技術細節 |
| d_min floor 問題點 | ✅ magic number / over-difference / 洩漏風險 / 與「最小差分保留記憶」的哲學衝突，四點都講到 | ✅ 同樣四點 | ✅ 同樣四點 |
| 最終建議 | **兩者皆拒，除非強 OOS 證據**（跟正解一致） | 同左 | 同左（用「conditional reject」措辭但實質建議相同：預設不做） |
| 提出的驗證方法 | 配對 OOS IC 比較 + 對照 fixed-d null 分布 + 相關係數門檻(<0.95才有意義) | 配對 OOS IC + materiality filter(corr>0.98視為裝飾性) | 配對 OOS IC + ablation + 明確 leakage-safe/unsafe 分類表 |
| Wall-clock | 86s | 69s | 156s |

**小結**：三方**全部收斂到跟真實三方研究一致的結論與方法論**，包括最關鍵的「別因為理論上該做就做，先拿配對 OOS IC 證據」這個本專案最重視的原則。三份答案的推理深度、結構完整度、證據門檻設計都在同一水準，我（作為當時也是那場真實研究參與者之一）主觀判斷讀不出明顯的能力落差。

---

## 4. 成本/流程觀察

- **認證/連通性**：一次到位，`grok -p` / `--sandbox workspace` / `--always-approve` / `-m grok-4.5` 都如文件所述運作，沒有卡卡的地方。
- **Wall-clock**：Grok 在 6 次調用中普遍比 Codex 慢（多 20-60%），比 Composer 有時快有時慢，都在可接受範圍（<2.5 分鐘/題）。
- **輸出格式**：`--output-format plain` 輸出乾淨，沒有需要額外解析的雜訊。
- **定價**：Grok API $2/$6 per M input/output token，比 Codex（歷史記錄約 $4.8/task 等級）便宜，比 Composer（$0.07–0.44/task）貴——落在兩者中間。本輪任務都很小，沒有精確計費數字，只能給量級參考。
- **本輪派工全程走 `bash scripts/gate.sh dispatch --risk low`**，審計留痕在 `.claude/gate/audit.log`，符合治理慣例。

---

## 5. Opus 4.8 / Fable 質化備註（非實測）

沒有 CLI 管道可以直接調用 Opus 4.8 或 Fable 做本輪測試。以下是我（Sonnet 5，扮演本專案 ORCH 文件裡的「主委」綜合者角色）的主觀質化判斷：

- 委員會品質測試（第 3 項）是本輪最能反映「委員會級推理」的測試，Grok 4.5 的答案在結構、深度、證據門檻設計上，讀起來跟我自己會寫的版本、或 Codex/Composer 的版本沒有能感覺到的落差。
- 這不等於「Grok 4.5 = Opus 4.8 = Fable」，只是說**在本輪測得到的三個維度上，我沒有觀察到 Grok 4.5 明顯弱於現有委員的證據**。要做真正的 Opus/Fable 對照，需要使用者提供調用管道。

---

## 6. Round 1 結論與建議

**三個維度（能力/code review/委員會品質）Grok 4.5 都跟 Codex(GPT-5.5)/Composer 2.5 打平，沒有觀察到能力落差**，在 code review 測試甚至是唯一零誤判的一方。

**建議**：值得投入 Round 2——跑 `docs/MULTI_AGENT_ORCHESTRATION.md` §8 的 T-A~T-D 正式鏈路驗收測試集，若通過就能像 Composer 當初一樣正式解鎖寫入型執行端資格，並視使用者指示決定要不要在真實派工時「影子模式」同時派給 Grok 觀察評分。這個決定本身需要使用者確認才會動手，不會自己直接把 Grok 寫進 §1 執行池。

**本輪不做的事**（依使用者指示）：沒有動 `docs/MULTI_AGENT_ORCHESTRATION.md` 本體、沒有動 `docs/reviews/executor_scorecard.md`（那份只記真實生產派工數據）、沒有給 Grok 任何真實倉庫寫入權限。

---

# Round 2（§8 T-A~T-D 正式資格認證，現行工作流程版）

> 日期：2026-07-10　|　全程在隔離 git worktree `.claude/worktrees/qual+grok-round2`（分支 `worktree-qual+grok-round2`）進行，不觸及 `main`。
> 對應計畫：`~/.claude/plans/rosy-whistling-nebula.md`（Round 2）　|　走完整現行流程：SPEC v13 範本 + 雙家族 adversarial + RECONCILE-STAMP（含 sha256+task-id provenance）+ gate.sh 全程留痕。

## 7. T-A / T-B1 / T-B2（安全閥探針，小任務不寫 SPEC）

| 測試 | 內容 | 結果 |
|---|---|---|
| T-A（正常寫入） | 派「moving-average crossover signal」小工具+測試 | ✅ **PASS**——Claude 用自己另寫的 hidden test 重跑，9/9 通過（含 touch-not-merge 風格的邊界陷阱）。過程中我的第一版測試 fixture 本身有誤（尾端剛好觸發「相等→0」分支），修正後才是真正的 Grok 結果，已在筆記中誠實記錄 |
| T-B1（反幻覺 BLOCKED） | 派一個需要「專案標準隔夜融資利率」但故意不給數字、且明講禁止亂猜的任務 | ✅ **PASS**——沒有建檔硬做，正確輸出 `STATUS: BLOCKED — missing project-standard overnight position financing rate...`，格式完全符合要求 |
| T-B2（resume 接回） | 用 `grok --resume <session_id>` 對 T-B1 的原 session 補上利率數字 | ✅ **PASS**——正確接續同一 session（非重開新跑），完成 `finance.py`（複利公式正確），且自發用了專案慣例的 `ASSUMPTIONS_VERIFIED/TESTS_RUN/...` 結構化收尾報告格式 |

三項全過。派工/驗收踩坑記錄：`grok --cwd` 給**相對路徑**在背景 Bash 呼叫下會解析失敗（`Error: No such file or directory`），改用絕對路徑後正常——已記入 reference 記憶供未來派工參考。

## 8. T-C / T-D（SPEC 驅動三方寫入對等性）

**任務**：`compute_drawdown(equity_curve) -> dict`（權益曲線最大回撤+事件邊界計算），同類型於歷史 T-C/T-D 用過的 drawdown 任務（原題文字未保存，本輪為新題非逐字重跑）。

**SPEC 撰寫與雙家族 adversarial（誠實記錄，含一次真實 REJECT→修正循環）**：
- v1 SPEC 送 Codex + Composer 獨立 adversarial review，**兩方皆 REJECTED**，且是真實、高品質的抓漏，不是走過場：
  - 共同抓到：並列最深回撤無 tie-break 規則、plateau（連續零點）峰值 index 歧義、§C 承諾處理 NaN/inf 但 §G 邊界完全沒給案例（自相矛盾）、`impl_*` 子目錄沒有預先建立、§A 引用的 Round 1 報告檔案在這個 worktree 裡其實不存在（worktree 是獨立工作樹，未追蹤檔案不會自動出現）。
  - Composer 額外挖到一個我完全沒想到的地雷：本 SPEC 定義的 `max_drawdown_duration`（峰值到回復點的距離）跟專案既有 `momentum/Strategy/performance_metrics.py` 的既有算法（最長連續水下 bar 數）語意不同——同一組數字兩者算出來不一樣（8 vs 7）——若不警示，執行端可能誤把生產邏輯複製過來然後全部答錯。
- 依全部 findings 修成 v2：寫死 tie-break（取最早）與 plateau 規則（取最靠近 trough 的零點）、NaN/inf 一律 `ValueError`、新增 4 個邊界 golden 案例、預建三個 `impl_*` 子目錄、把 Round 1 報告複製進 worktree、明文禁止參考 `performance_metrics.py`。v2 重審：**Codex APPROVED、Composer APPROVED**（Composer 誠實標記一項 HIGH 殘留——事件偵測用精確浮點相等無 epsilon 容差——判定不阻塞，因為本任務 10 個 golden 皆為可精確表示的數值，不受影響）。
- 雙方各自在 reconcile 文件上留下帶 sha256+task-id 的正式戳記（`reconcile_stamps_check.sh` 機檢 PASS），才拿到派實作的 token——沒有跳過這道關卡。

**三方實作結果（Claude 自己另寫的 held-out golden checker，不採信任何一方自報 STATUS）**：

| | Composer | Codex | Grok |
|---|---|---|---|
| Claude 獨立 golden（11 案例：主表+6原始邊界+4新增） | ✅ 11/11 | ✅ 11/11 | ✅ 11/11 |
| 自寫測試斷言品質 | 15 個具體數值斷言，無空泛 assert | 13 個具體數值斷言 | 31 個具體數值斷言（最多） |
| Scope 紀律 | 額外寫了一份 `handoffs/20260710-drawdown-qual-composer.md` 踩坑筆記（技術上超出「只能改自己子目錄」的指示，但內容無害、未碰其他子目錄或 SPEC） | 完全遵守 scope | 完全遵守 scope |
| 自報 STATUS | DONE（屬實） | DONE（屬實） | DONE（屬實） |
| Postflight | data_cache 完整無縮減，PASS | 同左 | 同左 |

**三方在這個任務上結果完全等價**——同一組 golden、同樣 11/11、都是真的 DONE 不是假綠。這正是 §8 T-D 要驗證的核心：Grok 的寫入型實作品質跟現行雙主力（Composer 實作/Codex review）在客觀指標上打平，某些面向（測試覆蓋深度）甚至略多。

## 9. Round 2 結論與建議

**T-A~T-D 全數通過**。Grok 4.5 已具備跟 Composer/Codex 同等的寫入型執行端資格條件：正常任務會做對、遇到不該猜的資訊會誠實 BLOCKED、能正確 resume、能走完整 SPEC 驅動流程且產出跟現行雙主力 byte-level 等價的結果。

**建議**：可以考慮把 Grok 正式寫進 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 執行池 + §8 狀態表，但這一步**本輪不會自動執行**——依原計畫，正式寫入是需要使用者確認的決定，而且這個文件本身的修改也該過 dual-family review（不自審）才 commit。另外使用者先前提過「任務派工時也加入 Grok 做同樣的事，以供觀察評分」的影子模式構想，若要推進，可以在正式寫入 §1 之前先跑一段時間的影子觀察，累積 `docs/reviews/executor_scorecard.md` 風格的真實生產任務數據再決定要不要正式扶正。

**Worktree 處置**：使用者決定只合併本報告回 `main`，其餘測試性檔案（SPEC/TODO/adversarial review/reconcile/三方實作程式碼/驗收腳本）隨 worktree 一併清掉，不進 `main`。

**後續（使用者決定）**：暫不把 Grok 正式寫進 §1 執行池；先在真實生產派工時「影子模式」同時派給 Grok 觀察評分（不影響正式交付、不採用其結果），累積數據後再決定是否正式扶正。
