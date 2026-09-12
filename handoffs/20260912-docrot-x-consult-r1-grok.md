# DOCROT X-CONSULT R1 — grok

task-id: 20260912-DOCROT-X-CONSULT-R1  
family: grok  
findings-round: R1  
brief: handoffs/20260912-DOCROT-CONSULT-R1-BRIEF.md  
note: brief 寫 `GROK-DOCROT-R1-P*`；`completeness_check` 之 canonical 正則為 `FAM-Rn-Pn-NN`，本檔改用 `GROK-R1-P*`（否則 `--single` 非 0）。

---

## 必答總覽（1–6）

### 1. 我自己量到什麼

| 量 | 結果 | 可重跑指令 |
|---|---|---|
| D-002 十二輪新 finding 總數 | **164**（R1–R12：15/11/15/8/11/16/15/14/21/13/12/13） | 見下方 `MEASURE-A` |
| SPEC 行數成長 | 初版 **154** → 現行 **351**（約 2.3×）；同日 14 次修訂 commit | `git log --follow --pretty=%h -- docs/SPLITUNIFY_SPEC.D-002.md` + 各 sha `wc -l` |
| 沿革外「活文」內 `vN` 考古標記 | **109** | 見 `MEASURE-B` |
| 單一決策在活文複述 | `Task 9.2b` 在沿革前出現 **19** 次 | 見 `MEASURE-B` |
| R11／R12 主委停輪自述 | R11「**首度全為**上一版修法缺陷」；R12「**無一為新面向**…全是字面同步」 | `grep -n '停輪判斷' handoffs/reconcile/20260911-splitunify-b9-review-r1{1,2}/synth.md` |
| `RECONCILE-STAMP APPROVED` | 十二份 synth **皆 0** | `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/20260911-splitunify-b9-review-r*/synth.md` |
| 白話 GAP-3 平行檔 | **8** 檔、合計 **5404** 行 | `wc -l 白話說明/GAP-3*.md` |
| xref 閘誠實邊界 | 腳本自白「只驗存在，**不驗語意等價**」 | `sed -n '1,25p' scripts/spec_xref_check.sh` |

```bash
# MEASURE-A（家族交件本輪 ID 計數）
python3 - <<'PY'
import re, pathlib
for i in range(1,13):
    n=0
    for fam in ('grok','codex','composer'):
        t=pathlib.Path(f'handoffs/20260911-splitunify-b9-review-r{i}-{fam}.md').read_text()
        n+=len(re.findall(rf'^## {fam.upper()}-R{i}-P[0-3]-[0-9]+', t, re.M))
    print(i, n)
print('sum', sum(
  sum(len(re.findall(rf'^## {fam.upper()}-R{i}-P[0-3]-[0-9]+',
      pathlib.Path(f'handoffs/20260911-splitunify-b9-review-r{i}-{fam}.md').read_text(), re.M))
      for fam in ('grok','codex','composer'))
  for i in range(1,13)))
PY
```

```bash
# MEASURE-B（活文 vs 沿革）
python3 - <<'PY'
from pathlib import Path
import re
text=Path('docs/SPLITUNIFY_SPEC.D-002.md').read_text()
live, _, hist = text.partition('## 沿革') if '## 沿革' in text else (text, '', '')
# 本檔實際沿革標題可能是「### 沿革」等——改用 regex 切
parts=re.split(r'^#+ .*沿革', text, maxsplit=1, flags=re.M)
live=parts[0]; hist=parts[1] if len(parts)>1 else ''
print('live_vN', len(re.findall(r'\bv\d+\b', live)))
print('Task_9.2b_live', live.count('Task 9.2b'))
print('live_lines', live.count('\n')+1, 'hist_lines', hist.count('\n')+1)
PY
```

本輪實跑摘要：`MEASURE-A` sum=**164**；`MEASURE-B` live_vN=**109**、Task_9.2b_live=**19**。

### 2. 問題是什麼（我的界定）

問題不是「文筆差」或「委員太嚴」，而是：

**同一操作決策被手寫進多個非生成落點（Task 正文／§V ASSERT／mutation 列／register／§N／沿革敘事／HANDOFF／白話進度），落點之間沒有單一可編輯真相源；adversarial 輪次在架構面收斂後，會系統性改去打「上一版修法的字面同步」，形成修訂→再審→再修訂的閉環，消耗輪次卻幾乎不推進程式碼。**

使用者「層層疊疊、修已修過的東西」**方向正確**；但若解讀成「幾乎所有 finding 都是假問題」，則**過度**——R1–R6 確實抓到同側約束、caller 未改、producer 仍單選等真架構缺口。

### 3. 根因（排序，非並列可能性）

1. **主因｜多落點手寫真相（文檔結構）**：一個決定在活文被複述多次（`Task 9.2b`×19），改一處靠記憶同步 → R12 O3 形態（Task／§V／mutation 互斥）結構上必然反覆出現。
2. **次因｜修訂考古寫進活義務**：活文 109 個 `vN` 標記＋大量「作廢／更正」句，委員每次重讀都會撞到已取代敘述，誤把歷史當現行。
3. **三因｜閘的取向**：`spec_xref_check` 只驗反引號 token **存在**、不驗 Task↔§V↔mutation **語意一致**；`obligation_block_check` 擋義務區散文形狀，不擋跨段複寫。格式閘綠 ≠ 單源一致。
4. **四因｜流程誘因**：多輪找碴以「還有 finding」為燃料；架構面飽和後，finding 表面自動滑向字面同步，直到 R12 才有「全是打上一版」的停輪判準。

### 4. 修法（可機械驗證；不新開治理 epic）

專案已裁定「不再擴建治理工具」（HANDOFF 2026-09-12）。因此**不**提案新閘腳本／新票；修法＝**改寫結構 + 用既有／一次性命令驗收**。

| ID | 修法 | 判定指令（成效指標） |
|---|---|---|
| F1 | **活文禁修訂考古**：`vN`／「作廢／前版」只准出現在沿革段（或獨立 `*_HISTORY.md`）；Task／§V／mutation 只陳述現行契約 | `MEASURE-B` 之 `live_vN` → **0**（沿革內不限） |
| F2 | **數字單點**：條數／版本號只寫在 register 表標題（或單一 SSOT 表）；其餘寫「見 (5.6)」指標 | `grep -nE '共 [0-9]+ 條' docs/SPLITUNIFY_SPEC.D-002.md` → **恰 1 行** |
| F3 | **決策單述**：每個 Task 規則正文只出現一次；§V 只留 ASSERT；mutation 只留改壞面——禁止在三處各寫一段散文重述 | 對關鍵 Task：`grep -c 'Task 9.2b' <活文>` 應顯著下降（目標 ≤3：標題+§V 掛名+mutation 掛名） |
| F4 | **流程（已部分落地，須寫死）**：當一輪群集「全部／近乎全部」指向「上一版修法／字面同步」→ **停審進實作**，殘餘交 pytest | 重現 R12 停輪句；下一次同類 epic 若再出現 R11→R12 形態仍續派 → 本修法失敗 |

若只做「改前先 grep、自證七條」而無 F1–F3 結構收縮 → **標為紀律型**，預期同型 finding 會再出現（HANDOFF 已自承該假設「未驗證」）。

### 5. 範圍（逐類）

| 類 | 判定 | 碼證 |
|---|---|---|
| `docs/SPLITUNIFY_SPEC.D-002.md` | **是（病灶核心）** | live_vN=109；Task 9.2b×19；R12 停輪句 |
| `HANDOFF.md` | **是（症狀鏡像）** | 同檔複述 v13／十二輪／29 條等（`grep -c 'v13\|十二輪\|29' HANDOFF.md` → 多命中）；應改為指標 |
| `docs/SPLITUNIFY_TODO.md` | **部分** | `SU-RESID-*` 與 SPEC §N 雙寫狀態（TODO:470 仍 `needs-research` 而 SPEC 稱落實）——跨檔雙 SoT |
| `handoffs/reconcile/*/synth.md` | **不適用作「病」** | 收斂檔本就是輪次歸檔；重複是歷史紀錄，不是活義務。委員若把 synth 當現行 SPEC 讀才會二次中毒 |
| `白話說明/*.md` | **是（平行複寫）** | GAP-3 八檔 5404 行；SPLITUNIFY／接下來／現在／治理日誌合計數千行進度敘事 |
| `docs/VERDICTGATE_SPEC.md` | **同型（對照）** | `git log --oneline -- docs/VERDICTGATE_SPEC.md` 可見 v1→v9 多輪收斂；與 D-002 同屬「規格多輪字面修訂」族譜，非本票主證據 |

### 6. 是否不值得解

- **值得解的部分**：SPEC 活文多落點 + 考古入活文（F1–F3）。不解則下一張中／大規格票仍會重演 R8–R12。
- **不值得再解的部分**：再蓋一層治理閘／新 epic 去「檢查漏改」——與既定「不再擴建治理工具」衝突，且 xref 已證明「存在性檢查」擋不住語意漂移。
- **可接受的殘餘成本**：收斂檔與沿革的歷史敘事；白話檔是否合併屬使用者看板偏好（HANDOFF 已標）。
- **換掉整個文檔體系**：**現階段不必要**。先把活 SPEC 收成「現行契約＋沿革分家＋數字單點」；若下一張大票仍出現 ≥8 輪且末兩輪全是字面同步，再評估「結構化表（YAML）生成 SPEC 段落」。

---

## §0 挑戰前提

| 前提 | brief | grok 重判 | 證據 |
|---|---|---|---|
| 使用者原話屬實 | fact-verified | **成立** | brief 逐字；本輪不重審對話 log |
| D-002 十二輪／十三修 | fact-verified | **成立** | `git log` 14 條修訂主題；synth r1–r12 存在 |
| 十二輪 STAMP APPROVED=0 | fact-verified | **成立** | 十二檔 `grep -c` 皆 0 |
| 四家不看主委版仍能獨立界定 | assumed | **成立（本家）** | 本檔僅用 raw 材料＋自跑量測；未讀 `…-claude.md` |
| 此問題有解 | assumed | **有條件成立** | F1–F3 結構收縮可機械驗；純紀律解 → 否證傾向成立 |
| 「7 成」分母＝輪數／回合 | assumed | **部分成立、比例偏高** | 見 P2-01：末段輪次浪費極高，但全 164 條不能算 7 成假問題 |

## 被當成事實的未驗證假設（§0）

- 「自證七條／改前 grep」已能消除漏改 → HANDOFF 自標**未驗證**；本輪量測支持「尚未消除」（R12 仍是字面同步）。
- 「7 成時間浪費」若被當成已校準的計量 → **assumption**；本輪只能量到輪次／finding／行數代理，未做 wall-clock 分母。

---

## GROK-R1-P0-01

**斷言**: D-002 活文把同一決策手寫進多個落點（例：`Task 9.2b` 在沿革前出現 19 次），使「改一處漏一處」成為結構產物而非偶發疏忽；此結構直接驅動 R11–R12「全打上一版修法」閉環。

**碼證**: `MEASURE-B` → `Task_9.2b_live=19`、`live_vN=109`；R12 synth 停輪句：「十三條無一為新面向…剩餘七群全是字面同步」。RECHECK：重跑 `MEASURE-B`；`grep -n '停輪判斷' handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24；handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[BLOCKING] 信心度=High。會怎麼失敗：實作者／委員各自抓住不同落點 → 互斥指示（R12 O3 形態）或假完成。**修法**：F1+F3（活文去考古、決策單述）；可行性＝純刪併與搬移，不需新閘；成效指標＝`Task 9.2b` 活文計數 ≤3 且 `live_vN=0`。

---

## GROK-R1-P1-01

**斷言**: 現行產出端閘（`spec_xref_check`）明確不驗語意等價，因此「閘全綠」不能否定多落點漂移；把綠閘當成文檔健康信號會誤判。

**碼證**: `scripts/spec_xref_check.sh` 檔頭：「誠實邊界：只驗『存在』，不驗語意等價（synth 寫 A、SPEC 寫 A' 抓不到）」。RECHECK：`sed -n '1,25p' scripts/spec_xref_check.sh | grep -n '語意'`。

**來源摘要**: scripts/spec_xref_check.sh#7073db9808bd

[MAJOR] 信心度=High。會怎麼失敗：主委以 xref／obligation／format 全綠結束修訂，委員下一輪仍用語義對讀打穿。**修法**：不新開閘；改以 F1–F2 減少需要語意對齊的表面積。若強行加「語意 xref」→ 違反「不再擴建治理工具」，本家標為**不採**。

---

## GROK-R1-P1-02

**斷言**: 使用者「文檔問題浪費大部分輪數」對 **R8 之後**成立，且 R11–R12 為極端型；但把「7 成」外推到 **全部 164 條 finding／整個 epic** 會抹掉 R1–R6 的真架構收益。

**碼證**: finding 序列 15/11/15/8/11/16/15/14/21/13/12/13（無單調下降）；R1 synth 含同側／mutation 覆蓋等架構群；R11／R12 停輪句自承「全為上一版修法／字面同步」。粗代理：末 5 輪（R8–R12）finding=14+21+13+12+13=**73／164≈45%** 輪次份額，若加計同日 14 次修訂與派工開銷，wall-clock 體感可逼近使用者所說；但 **非**「七成 finding 無價值」。RECHECK：重跑 `MEASURE-A`；對讀 r1 與 r12 synth 群集表。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md#849e2869746a；handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md#b98eb1d9665c；handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。會怎麼失敗：若修法目標設成「消滅審查」，會連早期真缺陷一起關掉。**修法**：F4 停輪判準（已在 R12 觸發）寫進編排慣例；保留早期架構審查，切斷晚期字面閉環。

---

## GROK-R1-P1-03

**斷言**: 同病在 `白話說明/` 與 `HANDOFF.md` 以「進度複寫」形態存在；GAP-3 八檔 5404 行平行敘事，使「現況數字」有多個可漂移副本。

**碼證**: `wc -l 白話說明/GAP-3*.md` → 8 檔／5404 行；`grep -l '29 條' HANDOFF.md docs/SPLITUNIFY_SPEC.D-002.md 白話說明/*.md` 多檔命中。RECHECK：同上命令。

**來源摘要**: 白話說明/GAP-3施工進度.md#8209ea221c00；HANDOFF.md#101a5e0c449b

[MAJOR] 信心度=High。會怎麼失敗：SPEC 改了條數，白話／HANDOFF 仍引用舊數 → 下一輪審查或人類讀板被舊數錨定。**修法**：進度類白話只留一份權威、其餘改指標（合併與否交使用者）；HANDOFF 對條數／輪次只留 `見 SPEC:(5.6)`。成效：`grep -l '29 條' …` 命中集縮到單一權威檔。

---

## GROK-R1-P2-01

**斷言**: `handoffs/reconcile/*/synth.md` 不應被當成與 SPEC 同類的「活文病灶」；它們是輪次歸檔。把清理歷史 synth 當修法會無效且傷審計。

**碼證**: 十二份 synth 皆含「附錄：findings 逐字保留（byte-faithful）」契約；刪改會破壞 completeness／attribution 回溯。RECHECK：`grep -n 'byte-faithful' handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MINOR] 信心度=High。修法：範圍上排除歷史 synth；只收縮活 SPEC／HANDOFF／白話。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P0-01,GROK-R1-P1-01,GROK-R1-P1-02,GROK-R1-P1-03
CLOSED:
STATUS: DONE
