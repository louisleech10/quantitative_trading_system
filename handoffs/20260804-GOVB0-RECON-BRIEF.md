# 第 0 批（B-24／B-15／B-14）開工偵察 — 事實查證與修法方案實測

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 本輪是**偵察輪**，非 SPEC 審查輪。**尚無 SPEC**——本 brief 要的是**事實**與**實測數據**；SPEC 由主委收到本輪結果後才起草。
- **禁改碼**。所有探針一律用**隔離副本**（`cp` 到 `/private/tmp/<你的 workdir>/`），
  **禁直接變異 repo 內 `scripts/*.sh`／`tests/**`**，禁 `git checkout`／`git restore` 任何 tracked 檔。

## 審查標的（三張票，本批合一個管線）
| 票 | 檔案落點 |
|---|---|
| `B-24` `GOV-ACCEPTANCE-STATE-NOT-RC` | `handoffs/20260801-GOV-AMEND-BACKLOG.md`（`## B-24` 節）；`templates/` 全部 |
| `B-15` `GOV-GATECHECK-READONLY-PGREP-FP` | `scripts/gate_check.sh:78-92`；同上 backlog `## B-15` 節 |
| `B-14` `GOV-CURSORAGENT-POSTWRITE-HANG` | `scripts/cx_run.sh:455-465`；`scripts/committee_run.sh:280`；同上 backlog `## B-14` 節 |

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: `gate_check.sh:86` 的派工偵測正則為
`(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)`，
**只比對命令位置**（行首或 `;&|` 之後），設計上已避開 `cat sp_codex.txt` 這種檔名子字串
→ 讀 `scripts/gate_check.sh:82-92`（含其註解），2026-08-04。
⇒ **backlog `## B-15` 節內「判定僅比對指令字串是否含家族名，不區分讀寫」這句是錯的，已知須修正。**

fact-verified: `.claude/gate/audit.log` 的 `gate_deny` 事件**不記錄被擋的指令內容**，
欄位只有 `event/ts/tool/kind/reason`；全檔 599 筆的 `reason` 僅兩種值：
`token_expired` 493 筆、`open_debt` 106 筆
→ `grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c`，2026-08-04。
⇒ **audit.log 無法提供 B-15 的誤擋語料，也無法事後統計誤擋率。**

fact-verified: `scripts/cx_run.sh` **全檔無 `timeout`**；`cursor-agent` 於 `:461` 直接前景呼叫。
`scripts/committee_run.sh:280` 用裸 `wait "${pid}"`，**無上限**
→ `grep -n "timeout" scripts/cx_run.sh` 零命中；讀 `committee_run.sh:275-290`，2026-08-04。
⇒ B-14 的 2h20m 空等，在**我方程式碼**中無任何逾時保護。

assumed: 三個已知 FP（`pgrep -fl '…|cursor-agent|grok '`／`for f in codex composer grok; do … done`
讀產出檔／`completeness_check.sh --lock <路徑>`）**全部**源自「正則不理解引號」
——即引號**內**的 `;&|` 被當成命令分隔符。
← **請直接攻這條**。主委只對第一例（`pgrep`）做過紙上推導，**後兩例未實跑重現**；
第三例（`completeness_check --lock`）從正則看**根本不明顯為何會命中**。

assumed: `B-15` 修法選項②（改判準為「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」）
比選項①（引號感知）更乾淨。← 請攻。**手搓 `codex exec …` 而不經 `cx_run.sh`，是既有且被明文禁止
但技術上完全可行的路徑**，選項②會讓它整個漏網。

assumed: `B-24` 不需要新檢查器，只要把「狀態斷言」寫進各票驗收欄即可（backlog `## B-24` 節自己這樣寫）。
← 請攻。**這與使用者定死的「工具必須自帶強制機制——不准靠紀律和記憶」直接衝突**；
若真不建檢查器，須說明它憑什麼不會退化成又一條靠記性的 prose 規則。

## 必答（逐條 verdict；每條都要**實跑 receipt**，不接受純推理）

### Q1（B-15）三個 FP 逐例重現，指出正則的哪一段命中
對三個 FP 各建一條**與事故當時等價**的指令字串，餵給 `gate_check.sh` 的**隔離副本**
（或等價地單獨跑 `:86` 那條 `grep -Eq`），輸出：

| FP | 完整指令字串 | 是否命中 | 命中的 alternation | 命中處的字元位置與上下文 |

🔴 第三例（`completeness_check --lock`）若**無法重現，就明講重現不出來**，
**不要為了湊齊三例而編一條會命中的指令**。重現不出來本身即重要結論
（代表 backlog 記載有誤，或觸發源另有其他——例如 `Task` 工具通道、或 `claude[^|]*(-p|--print)` 那段）。

### Q2（B-15）建立語料並實測兩個修法方案
語料須**來自真實來源**（`git log` 內的指令紀錄／`handoffs/**` 留存的指令／`scripts/*.sh` 內實際會執行的命令列），
**禁憑空造**；每條標明出處。至少涵蓋：
- **TP（真派工，必須被擋）**：`cx_run.sh` 實際發出的 `codex exec …`／`cursor-agent -p …`／`grok -m …` 形態；以及**繞過 `cx_run.sh` 手搓**的等價形態。
- **TN（唯讀，必須放行）**：Q1 三例，加上你在 repo 內找得到的任何「指令含家族名但非派工」形態。

對**方案①引號感知**與**方案②呼叫點判準**各做一份最小原型（隔離副本），對同一語料實跑，出表：

| 方案 | TP 被擋 | TP 漏網 | FP 誤擋 | TN 正確放行 |

🔴 **漏網（TP 未被擋）是 fail-open，權重遠高於誤擋**。任一方案若有 TP 漏網，直說該方案不可用。
🔴 併請評估**方案③＝疊加**（引號感知後仍以家族名為主判準，另加呼叫點作為補強）。

### Q3（B-14）逾時保護的落點與「完整即成功」的判定
- per-family timeout 該加在哪一層：`cx_run.sh` 的 CLI 呼叫（`:461` 等）還是 `committee_run.sh:280` 的 `wait`？各自代價（訊號傳遞、孤兒進程、runlog 完整性）為何？
- 逾時後判「產出已完整 ⇒ 視為成功」的機械依據：`bash scripts/completeness_check.sh --single <產出檔>` rc=0 是否**充分**？
  它檢查 canonical ID 格式與 finding body（見 `completeness_check.sh:1459-1472`），**不檢查內容是否寫完**。
  請判斷：一份**中途被截斷、但恰好最後一條 finding 格式完整**的產出檔，會不會被誤判為成功？若會，補救判準是什麼？
- 逾時值取多少？請從 `handoffs/**` 既有 runlog／產出檔 mtime 取**真實的每家耗時分布**，用數據給建議值，**勿憑感覺給 30 分鐘**。
- 三值 `result_state`（`success`／`failed`／`format-failed`）的合法值與寫入點在 `cx_run.sh` 哪幾行？逾時該寫哪一個？

### Q4（B-24）驗收欄現況盤點與強制機制
- 掃 `templates/` 全部檔案與 `docs/*{SPEC,TODO}*.md`，統計驗收欄中「**只要求跑腳本／看 rc**」與「**要求狀態斷言**」各幾條，附檔名行號。
- 是否存在可機檢的形態（例如：驗收欄出現 `rc=0` 而同條無狀態斷言關鍵字則報錯）？誤報率預估多少？
- 若你判定「不建檢查器」正確，請正面回答：**它憑什麼不會退化成靠記性的 prose 規則？**（使用者定死條款）

### Q5 三張票合成一批，順序與耦合
`B-24`（橫向紀律）→`B-15`（改 gate 判定）→`B-14`（改委員生命週期）是否為正確順序？
有無**必須拆開**或**必須調換**的技術理由？三者是否共用檔案（`gate_check.sh`／`cx_run.sh`／`committee_run.sh`）而造成改動衝突？

### Q6 可以進下一步（主委起草 SPEC）嗎，還是有 BLOCKING 必須先修？

## 交付紀律（`B-24` 適用於本 brief 自身）
- 凡你寫「已驗證」，**必須附狀態斷言**，不得只寫某腳本 rc=0。
  例：跑完測試要附 `git status --short tests/golden/` 的**實際輸出**，而非 `restore_golden_inventory.sh` 的 rc。
- **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc）。

## 產出
canonical 四欄 findings + **Verdict**。Q1–Q4 的表格與 receipt 直接寫進產出檔。
**禁改碼**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
