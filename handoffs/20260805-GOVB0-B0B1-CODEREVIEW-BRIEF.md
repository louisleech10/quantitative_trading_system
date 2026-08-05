
# 第 0 批 B0＋B1 code review（雙家族）

brief-kind: review

**受審 commit**：`596fcb4`（`feat(governance): 第 0 批 B0+B1 實作完成`）
新測試檔行數 `VERIFY:govb0-b0b1-testfile-lines`（**讀碼** `wc -l tests/governance/test_gate_deny_fields.py` → `356`）
**依據**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）Phase 0 / Task 0.1 ＋ §B 的 B0 列

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 finding heading 格式（引用檢查器正則本身）

`scripts/completeness_check.sh:153` 的 canonical 正則**逐字**為：

```
^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$
```

**本輪合法範例**：`CODEX-R10-P1-01`／`COMPOSER-R10-P0-02`。
**本輪唯一允許的 `##` 標題**：`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`
＋ canonical finding heading。其餘分段用 `###`。零 findings 請明寫 `FINDINGS_COUNT: 0`。

## §0 前提宣告

**已查證**（主委實跑，可自行復跑）：

- fact-verified: 測試由 **701 → 715 passed** —— 基線 `VERIFY:govb0-test-baseline`（**真跑** `701 passed`）；
  改後 `VERIFY:govb0-b0b1-test-count`（**真跑** `715 passed in 221.20s`）。
  🔴 **後者為主委事後補跑**：本 brief 派工當下主委**未親自復跑**，僅轉述實作者數字，
  已於下方 assumed 段自標；claim checker 於 commit 時擋下並逼出實跑。數字屬實，但**過程順序是錯的**。
- fact-verified: **既有測試檔零改動** → `git diff HEAD~1 --name-only -- tests/governance/`
  排除新增檔後為空。
- fact-verified: `TEST-0.1-INVARIANCE` 非空心——實際以 B0 snapshot 對照現行 `gate_check.sh`
  跑語料 A 並逐項比對 `(rc, kind)`，差分行數斷言 `== 0`。
- fact-verified: `TEST-0.1-MUT` 非空心——實際複製並剝除新欄位 jq 模板，
  且錨點漂移時 `assert` 會失敗而非靜默通過。

**假設**（請優先攻）：

- assumed: **主委只讀了 diff 與兩個關鍵測試的實作，未逐行讀完 356 行新測試**。
  其餘 17 個測試是否有恆真斷言／只驗「不拋錯」的 smoke，**未經查核**。
- assumed: **實作者宣告的三處 scope 變更皆為必要且最小**（見下），未經第三方驗證。
- assumed: **`715 passed` 是主委轉述實作者的數字，主委未親自復跑全套**（基線 701 有親跑 receipt）。
- assumed: **B0 snapshot 真的是「Phase 2 動工前」的狀態**——
  即 `gate_check.sh` 在 B1 改動**之前**被複製。未驗證複製時序。

## 🔴 本輪首要標的：實作者宣告的三處 scope 變更

實作者**明文宣告**（非靜默偏離），主委判定三處**皆為主委 TODO 的缺口**。**請獨立驗證此判定**：

| # | 變更 | 實作者理由 | 你要確認 |
|---|---|---|---|
| 1 | `required_fields_per_event.gate_deny` 保留既有 `tool`／`kind` | TODO 只列新欄位，但 `test_gate_deny_audit.py` 基線已斷言 `tool`／`kind` 必在 ⇒ 照 TODO 字面做會弄紅既有測試 | 此理由是否屬實？保留後是否**擴大**了 required_fields 的語意而弱化檢查？ |
| 2 | `event_object_allowed_keys` 由 array 改 map | 原為 debt 欄位 array，TODO 要求 `.gate_deny` 鍵，結構不相容 | 改 map 是否影響既有 debt 相關檢查的語意？有無更小的改法？ |
| 3 | 語料 B 放最小占位檔 | `TEST-0.1-CORPUS-DISTINCT` 要求兩份語料皆入版控，但語料 B 屬 Task 2.0 ⇒ TODO 自相矛盾 | 占位檔是否會讓 Task 2.0 誤以為語料 B 已建？是否該加標記防止？ |

## 逐項核對表（**用表格，不要用標題**）

| # | 查什麼 | 你的判定 | 依據（實跑命令＋結果） |
|---|---|---|---|
| 1 | **判定行為真的不變？** 語料 A 的 24 條是否**足以涵蓋**現行判定的所有分支？漏掉的分支即為未受保護 | | |
| 2 | **`grep -Eo` 是否真的在判定之後**？有無任何路徑使其結果回饋進 `(rc, kind)` | | |
| 3 | **測試品質**：依範本 §1 第 9 類逐條舉證 | | |
| 4 | **B0 snapshot 時序正確？** 它是否為 B1 改動**前**的 `gate_check.sh`（可比對 `596fcb4^` 的檔案雜湊） | | |
| 5 | **截斷規則邊界**：4 MB prompt → audit 單行 ≤1 KB；含換行／控制字元 → 仍為合法 JSON | | |
| 6 | **兩份語料 sha256 不同且皆 tracked**；語料 A 是否含真實被擋案例而非全部憑空造 | | |

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`，不計入 findings）

1. 重開 SPEC／TODO 的設計裁決（SPEC 七輪＋TODO 三輪皆已收斂並戳記）。
   **例外**：該裁決導致本實作有實質缺陷。
2. B2 以後的 Task（`1.1`／`2.*`／`3.*`）——本批未實作，不在範圍。
3. `E-SCOPE` 四項、`H-1`／`H-2`、`F-7`／`B-36` 等已具名殘留。
4. 措辭／命名／可讀性。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ B0+B1 驗收通過，可進 B2。**

## 硬性要求

1. **禁改碼、禁改測試、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`／`git clean`；不要 commit、不要 push；**禁碰 `data_cache/`**。
4. 每條 finding 附**可執行修法**與**重現命令**。
5. 若你要跑全套 `pytest tests/governance -q`，**丟背景並導檔再取尾**（約 230 秒）。

## 產出

上表六項逐項判定、三處 scope 變更的獨立驗證、findings（若有）、`## 出場判準核算`、
對 §0 四條假設的攻擊結果。收尾清 /tmp workdir（保留 claude-501）。
