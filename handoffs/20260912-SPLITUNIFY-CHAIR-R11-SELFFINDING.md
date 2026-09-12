# 主委自產發現（待併入 R11 收斂）

task-id: 20260911-SPLITUNIFY-X-REVIEW-R11；family: chair(claude)；findings-round: R11
性質：**主委自查**，非委員交件；不進 `reconcile_build` 之 sources，僅供 R11 收斂時併入群集表。
產生時點：R11 派工後、兩家交件前。**未改動 `docs/SPLITUNIFY_SPEC.D-001.md`**（避免審查中途變更標的）。
緣由：R11 brief 必答二要求委員攻擊主委之核心主張；依「主委自產一版」之規矩，主委先自行嘗試否證。

## CLAUDE-R11-P2-01

**斷言**: 主委在 R10 寫入 D-001 的核心主張「投影入口之指紋重驗足以擋下建構後對 `row_index_local` 之竄改」**不完整**：指紋依規格**依位置遞增排序後**才序列化，故對**排列竄改**不敏感——把 `row_index_local` 重新排序後指紋完全相同。該類竄改實際上是被**另一道**「必須嚴格遞增」之閘擋下，不是被指紋擋下。規格若只寫「指紋重驗為權威守衛」，等於把一道必要的守衛留在文件之外。

**碼證**: 主委依 D-001-C2 第 1 點之算法（`list[list]`、元素順序 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`、**依 `position` 遞增排序後** `json.dumps(rows, sort_keys=True, separators=(",",":"))` 取 `sha256`）以 `venv/bin/python` 模擬四種竄改：

```
生產時指紋      : d5babec89cef
① 竄改一格 [0,2,4]->[0,3,4]: 508c3deef8ff => 相同? False
② 整體位移 ->[1,3,4]       : 4cd420be7c85 => 相同? False
③ 順序打亂 ->[4,2,0]       : d5babec89cef => 相同? True      ← 指紋抓不到
④ 竄改[1,3,4]＋配套索引    : ae8ebe576292 => 相同? False
```

④ 為最強攻擊：同時竄改位置並提供一份「讓時刻恰好對得上」的索引，指紋仍不同，因為**位置值本身進了 payload**。故指紋對「值」的竄改具偵錯力，對「順序」無偵錯力。

排列竄改在語意上**有害**：投影端以 `row_index[0]`／`rows[-1]` 取「最早／最晚的列」（首尾同源對證、`test_start_ms`），順序被打亂即取到錯時刻。現行擋它的是 `momentum/core/split_preview.py:161-165` 之 `assert_positional_rows(..., require_sorted=True)`（預設值），該閘要求嚴格遞增。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c；momentum/core/split_preview.py#；momentum/Analysis/event_samples/split_projection.py#98ee62905643

**影響／修法判定**: 不改的具體失敗＝規格把「權威守衛」單獨押在指紋上，而指紋對排列無感；若 b8 實作者依規格字面把長度閘改成 `require_sorted=False`（例如為了容納亂序輸入——R10 才剛放寬亂序立場，這個誤讀有現實誘因），排列竄改就**同時穿過兩道守衛**。修法：於 D-001-C2 明寫三點——①指紋依設計**依位置排序後**序列化，故**對排列不敏感**，此為明示邊界而非缺陷；②`row_index_local` 之**嚴格遞增**由投影入口之長度閘承擔，該閘**不得**關閉 `require_sorted`；③補一條 ASSERT（排列竄改後應紅）與一條變異（`require_sorted` 被關掉應紅）。

**與 R10 之關係**: 本條**不推翻** R10 之修法方向（權威守衛在消費入口仍成立），只指出該主張需要**兩道**入口守衛而非一道，且第二道目前只存在於碼中、未寫進規格。

**待辦**: 待 R11 兩家交件後一併收斂；若兩家亦獨立指出同一點，合併為同一群集；若兩家未指出，本條仍應入規格。
