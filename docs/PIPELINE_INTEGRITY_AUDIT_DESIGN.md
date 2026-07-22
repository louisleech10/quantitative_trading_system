# 委員蓋章 Pipeline 完整性盤查 + 加固設計(草稿,待委員對抗)

> 2026-07-22 Claude 起草。緣起:IC discovery reconcile 手抄漏~15 項(使用者抓包)。
> 使用者要求:盤查**整條大流程從第一件事到完工**所有「需委員審核/蓋章」節點,標出**逃脫點**,再整合 4 個加固要點。
> **誠實定位**:無單層完整;目標=把「Claude 自願才跑」的紀律點,換成 harness 強制點;殘留靠使用者兜底。

## 一、全流程節點盤查(大任務,開工→完工)

圖例:🟢機器強制(gate/hook/quorum script) | 🟡紀律(合約/memory,可靜默跳) | 🔴無守

| # | 節點 | 需委員? | 現行強制 | 逃脫點 |
|---|------|--------|---------|--------|
| 1 | 開工前稽核 HANDOFF/ROADMAP vs repo | 是(joint) | 🟡紀律 | 可略稽核直接開工;稽核**完整性**無驗 |
| 2 | 偵察 discovery 派工 | 是(3家) | 🟢 gate.sh dispatch token | 派工本身有 gate;但**派幾家/涵蓋面**無驗 |
| 3 | **discovery reconcile(Claude 綜合)** | 是 | 🔴**無**(stamp 只在 --spec 派實作觸發) | **本次踩雷**:手抄掉項 + 語意降級,無人擋 |
| 4 | SPEC 起草(Claude) | — | 🟢 gate.sh artifact(PreToolUse gate_check) | 檔名不含 SPEC 可閃?(gate_check 認 docs/*SPEC*) |
| 5 | SPEC 委員審(**現行 3 家** codex+composer+grok;Claude 起草非實作者) | 是 | 🟢 review_quorum_check.sh(機檢 floor=2 非實作者家族) | 審**完整性/深度**無驗(可淺審蓋章);grok 為正式委員不得漏 |
| 6 | **SPEC-review reconcile(Claude 綜合審意見)** | 是 | 🟡 stamp(有 hash)但… | **同 #3 病**:Claude 收審意見時**手抄掉 finding**;stamp 證「委員簽了此 body」但不證「Claude 收齊了委員的 finding」 |
| 7 | TODO 起草(Claude) + 委員審(**3 家** codex+composer+grok;Claude 起草非實作者) | 是 | 🟢 artifact + review_quorum_check | 同 #5;審完整性/深度無驗 |
| 8 | 實作派工(逐批) | 是 | 🟢 gate.sh dispatch --spec/--todo + 前批 quorum | 較嚴 |
| 9 | 實作 code review(**2 家**;實作者=1 CLI 家族**不自審**→僅另 2 家非實作者審) | 是 | 🟢 review_quorum_check(floor=2) | 審完整性無驗;agy 實習不算 quorum |
| 10 | **Finding 閉合複驗(原提出方重跑反例)** | 是 | 🔴**無機檢**(合約+memory) | 可「宣稱已修」不真重跑;假綠 |
| 11 | 接回 diff 防假綠(Claude 讀 diff+測試) | — | 🟡紀律 | 可不 diff 既有測試斷言 |
| 12 | 完工回報 + HANDOFF/ROADMAP 更新 | — | 🟡紀律 | 漏記(HANDOFF 屢犯) |

> **審查家數規則**:= 正式家族總數(codex+composer+grok=3) − 實作者(不自審)。Claude 起草的 artifact(SPEC/TODO,#5/#7)→ 3 家 CLI 全審;CLI 家族實作的 code(#9)→ 實作者排除 → 2 家審。agy 實習 advisory 不計入 quorum。

## 二、核心洞察:同一個病灶在**多個節點**復發
**「Claude 手抄合併多方產物」不是 discovery 獨有**——它出現在 **#3 discovery reconcile、#6 SPEC-review reconcile、SPEC-review 之外任何 Claude 收攏委員意見的地方**。每處都有相同掉項/降級風險。
- stamp(#6)看似有守,但 **hash-bound stamp 只證「委員簽了這份 body」,不證「Claude 把委員的 finding 收齊了」**。若委員審時只查自己的點(如本次 closure),照樣簽過而漏項存在。
- 所以修法必須**在每個 reconcile/聚合節點都套同一套**,不是只補 discovery。

## 三、逃脫點清單(🔴+🟡,依危害排序)
- **EP1(#3/#6 最貴)**:Claude reconcile 手抄掉項/降級——下游接 reconcile 一路錯,洞滾大。
- **EP2(#10)**:Finding 閉合只憑「宣稱已修」,無機檢原提出方真重跑反例。
- **EP3(#5/#9)**:委員審「完整性/深度」無驗——可淺審蓋章。
- **EP4(#1)**:開工前稽核可略過/不完整。
- **EP5(#11/#12)**:接回假綠 diff、HANDOFF 漏記。

## 四、整合加固設計(4 要點 × 對應節點 × 各擋什麼)

### ① 機械 union 聚合流程(改「手抄」為「先全收再刪」)
- **做法**:reconcile 前,腳本從所有來源檔抽 finding 錨點(key/`file:line`/bullet 標題/severity 標記)→ **全 union 進 reconcile 骨架**;Claude 只能在骨架上**整理/刪重**,刪除留 diff 痕跡。
- **擋**:EP1 手抄靜默掉項(掉項變成「顯式可稽核的刪除」)。
- **擋不到**:語意降級(錨點在但描述改壞)→ 交 ③④。

### ② completeness_check.sh(0 token 機械 diff)
- **做法**:吃 `綜合檔 + N 來源檔` → 列來源有、綜合無的錨點 → 非空 exit 1。
- **封節點**:#3 #6 及任何 reconcile 的**聚合完整性(B)**。
- **擋不到**:語意降級(字串在就 PASS,本次 coverage 錯它會放行)、共同盲點。

### ③ PreToolUse hook(harness 強制,非我自跑)——封 EP「我跳過不跑」
- **雙向觸發(防改名閃避,使用者 Q2)**:`檔名含 Reconcile/SPEC/TODO`(命名規約:綜合一律 `*_Reconcile_Vx`)**OR** `內容特徵`(findings 表/引用多份委員產物/`RECONCILE-STAMP` 段)。**內容像 reconcile 但檔名沒關鍵字 → 判「疑似改名閃避」→ 擋下**。想靠改檔名逃 → 被內容特徵抓。
- **動作**:自動跑 ② completeness_check;未附來源清單或有漏→**擋寫/警示**;標「委員全項忠實度覆議(C)未完成」。
- **殘留**:若內容也不像 reconcile(無表無戳記段)→ 兩特徵皆不中,但此時它**不被下游 gate 認可為合法 reconcile**,下一階段派工(⑤)因「找不到通過的上階段結論」被擋。雙夾擊。

### ⑤ 階段入口 gate(使用者 Q3/Q4:每階段前檢查上階段過關 + 引用遞移)——封 EP1 入口
- **掛在 `gate.sh dispatch`**(本來就是所有派工必經咽喉;PreToolUse `gate_check.sh` 無 token 就擋 codex/cursor/grok CLI)→ **不過檢查就發不出下一階段 token**。
- **引用遞移檢查**:被創建/派工的產物(SPEC/TODO/brief)**引用**了哪些治理文件 → 逐一驗**每份被引用文件本身已 stamp/過 completeness**。→ 完整性要求**遞移**:不能間接建在未驗產物上。
- **Finding 閉合(EP2)**:原提出方重跑反例的 receipt 進 gate;無 receipt→閉合不算。
- **能否「不被逃脫」(Q4)**:掛在已強制咽喉=最硬;**真殘留邊**=`gate_check.sh` 分類器覆蓋面(我用它沒認出的方式調模型就繞)+ hook 設定檔可被改(見 ⑥/⑦)。歸零做不到。

### ⑥ CI/server 端後盾(使用者 Q5:唯一擋得住「連 hook 都被改」的層)
- **根因(Q5)**:hook 定義在 `.claude/settings.json`,**在我的寫入範圍內** → 我有檔案寫入工具 → 理論上能停/弱化 hook。**執法者設定檔與被執法 agent 同信任域**=根本問題;且 PreToolUse matcher 只攔被設定要攔的 pattern。
- **唯一硬層**:把關鍵檢查(completeness/stamp/引用遞移)也放進 **GitHub Actions CI**(push 時 server 端跑)——**session 內無法停用**。本機 hook=第一線快回饋;CI=push 後盾;稽核日誌讓竄改**事後可查**。
- **誠實**:tamper-evident 非 tamper-proof。純靠 agent 自己能改的檢查永遠可被 agent 繞;**最硬層必須在 agent 修改範圍外(CI/你)**。

### ④ 便宜模型全項忠實度覆議(C)——省 token
- **做法**:② 標出候選 + reconcile 全項 → 丟 **Haiku 或單一家**(非 3 家 frontier)覆議 severity/描述是否降級/曲解。貴的 frontier 委員只留給**節點 A 偵察**(需多樣強推理)。
- **封節點**:#3 #6 的**語意忠實度(C)**。
- **擋不到**:共同盲點(unknown unknowns,無解)。

## 五、分層總表(每層擋什麼、擋不到什麼)
```
A 偵察   : 多家 frontier 獨立(貴)          → 擋單家盲點;擋不到共同盲點
B 聚合   : ①機械 union + ②completeness     → 擋手抄掉項;擋不到語意降級
C 忠實   : ④Haiku/單家全項覆議             → 擋語意降級;擋不到共同盲點
強制1    : ③hook(雙向:檔名 OR 內容特徵)    → 擋「我跳過不跑」+改名閃避;擋不到「內容也不像」(交強制2)
強制2    : ⑤gate.sh 階段入口+引用遞移       → 擋「建在未驗上階段」;擋不到 gate_check 分類器盲區
閉合     : ⑤receipt gate                   → 擋假綠閉合
硬後盾   : ⑥CI/server 端(session 改不到)   → 擋「連 hook 都被改」;擋不到 CI 本身被停(需 repo 權限,repo owner=你)
兜底     : 使用者 + 稽核日誌               → 擋以上全部殘留(本次即靠此)
```

## 六、誠實邊界
- 無層完整;所有**在我寫入範圍內**的自動層(hook/gate/settings)都有 meta 逃脫,最終兜底是使用者。
- **唯一擋得住「連 hook 都被改」= CI/server 端(⑥),在我 session 修改範圍之外**。tamper-evident 非 tamper-proof。
- 本設計本身也是「Claude 一版」→ 應丟**三家**委員對抗一輪(找我盤查漏的節點/逃脫點)再定案動工。
