# 全硬化合理性 + 全流程漏洞掃描 — Claude 自產版(待三方挑戰)

使用者指示:選全硬化,但委員會+Gemini 再議「收斂建議是否合理、會不會過嚴到一直撞牆無法執行」,並審查**整個任務流程**還有沒有類似捏造/驗證漏洞。
本檔=Claude 獨立版(feedback_claude_own_version),供 Codex/Composer(可寫)+Gemini(read-only)挑戰、修正、補充。

---

## 一、全硬化合理性 / 撞牆風險逐項評(誠實:哪些會卡死日常)

| 收斂項 | 合理? | 撞牆風險 | Claude 評 |
|---|---|---|---|
| B-FORGE receipt 綁 append-only 審計事件 | 是 | 低 | receipt 自動產;唯一摩擦=每個「已驗」要有真 run,這正是目的。**但須區分 `RUNTIME_VERIFIED` vs `READONLY_SIGNOFF`**(讀碼簽核如因果性 signoff 無 runnable test,不能逼附 run receipt,否則卡死合法讀碼結論)。 |
| B-HOOK PreToolUse 攔 Edit HANDOFF + git hook + CI + health | 是 | **高** | **最大撞牆源**:若每次 Edit HANDOFF 含「已驗/通過」字樣無 receipt 就擋,Claude 寫「上一步已驗(引用先前真 run)」「紅燈 supersede 舊 claim」會被攔到動彈不得。**設計要點:只擋『新的、無 backing 的驗收斷言』,放行 引用/supersede/討論;逃生口要快**(否則人改用 EXEMPT 繞=回原點,Codex 已預言)。 |
| B-CLASS runtime_class 推導 | 是 | 低 | receipt 工具內部,使用者無感。 |
| B-EXEMPT 窄類別豁免 | 是,但 | **中高** | **張力**:豁免太窄→**合法討論/forensic 文件被自擋**。**反諷:本事故這批 handoffs 全是引號內「已驗/真紅」,checker 會擋自己**。discussion-context 必須穩健(fenced block/forensic 白名單),否則寫事故分析都卡。 |
| B-LEDGER 狀態機 | 是 | 低(若自動管理) | 正確性需要;複雜度中等。 |
| B-SCOPE #7 RESULT 硬欄位 | 是 | 低 | 模板欄位。 |
| B-SCOPE #6 根 HANDOFF 生成索引 | 是,但 | **中** | churn 最大(改全員寫 HANDOFF 方式)。**這是全硬化最可能過頭處**;建議 v1 先做「過期/superseded claim 衝突檢查」(輕),完整 render 索引列 phase 2。 |

**Claude 平衡結論**:全硬化在**強制面+防偽面**值得(信任攸關);但**claim 偵測器必須高精度低誤報 + 快逃生口**,否則偵測器自己變成新的牆 → 人人 EXEMPT 繞過 → 換名重演。**過嚴的真風險不是「擋太多壞」,是「擋太多好→大家學會繞→防線空轉」**。三個高撞牆點(PreToolUse Edit 偵測精度、discussion/forensic 豁免、#6 churn)要設計治,不是砍掉硬化。

---

## 二、全流程漏洞掃描:其他「宣稱≠真做」的同型破口

**共同根因**:現有 gate **守『存在/有填內容』,不守『provenance(宣稱的流程真發生過)』**。receipt 的「審計事件背書」概念可推廣到所有「X 做過了」斷言。

| # | 破口 | 同型於 | 可偽程度 |
|---|---|---|---|
| W1 | `gate.sh` 自述「不驗證填入為真」→ SPEC §A「已確認事實」可捏造 | 第2/3次事故(拿推論當已驗) | 高:純文字 |
| W2 | `reconcile_stamps_check` grep「RECONCILE-STAMP APPROVED」→ **Claude 可自己 append 委員戳記** | 本事故(自證) | 高:grep 不驗來源 |
| W3 | gate `--adversarial` 只查**檔案存在**→ Claude 可自寫「adversarial review」假裝不同模型做過 | 本事故 | 高:存在≠真派工 |
| W4 | 驗收「diff 既有測試斷言防假綠」靠 Claude 自述跑過 | 本事故核心 | 高:無 receipt 即無證 |
| W5 | preflight/postflight 快照非全 dispatch 強制(hook 只擋 Task/Bash/Write 通道發 token,不強制跑 snapshot) | — | 中 |
| W6 | template_check/coverage_check 自承「只抓明顯空殼」→ 貌似合理邏輯空仍過 | 已知邊界 | 中 |
| W7 | audit.log「供使用者稽核」→ 若使用者不稽核則無強制 | — | 中:靠人 |
| W8 | MEMORY.md 記憶可記「PASS/簽核」成為未來可信 context(如 causality_signoff),捏造記憶持久污染 | 本事故信任階梯 | 中 |
| W9 | 執行端 RESULT 結構化欄位 Claude 只取事實,但「測試 pass/fail」欄本身若執行端造假,Claude 不重跑即信 | B3 已靠 adversarial 部分接住 | 中 |

**推廣修法(供委員議)**:把「provenance 事件」做成通用——凡 gate 的 receipt/stamp/adversarial/facts,都需對應「只有真流程能發的審計事件」(真派工才有 task-id+輸出指紋;真 run 才有 run receipt)。**但全做=巨大**;建議委員會**排序**哪些破口優先(W2/W3/W4 與本事故同型、最該先補;W1 接第2/3次事故)。

**反向自省(避免過度治理)**:W7「靠使用者稽核」其實是**設計上的最後人為關卡**,不必全機器化(使用者本來就是 ground truth)。不是每個破口都要堵成機器 fail-closed;有些列「殘餘風險+靠人」即可。**過度把人為判斷機器化=撞牆來源**。

---

## 三、給委員會/Gemini 的提問
1. 全硬化收斂建議**逐項**:哪些合理、哪些過頭(撞牆>收益)?特別是 PreToolUse Edit 偵測精度、discussion 豁免、#6 churn 三高風險點怎麼設計才不卡日常?
2. claim 偵測器「高精度低誤報」具體判準:怎麼分『新無backing驗收斷言』vs『引用/supersede/討論/forensic 引號』?
3. 全流程漏洞 W1-W9:同意?補充?**排序**哪些與本事故同型該先補,哪些列殘餘風險靠人即可?
4. 有沒有「治理加太多反而沒人遵守/繞過」的真風險?平衡點在哪?
