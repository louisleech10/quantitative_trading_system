## CODEX-R30-P3-00

**斷言**: 本輪逐項核對後無 finding；接受 r29 之 `CODEX-R29-P1-01` 駁回理由，現行防線未發現可在既定「意外漂移」威脅模型下同步縮小 AST 閉包、收據與 golden 且仍綠的非蓄意操作序列。

**碼證**: 隔離複本 `/tmp/ffstat-r30-work.pRxuQZ` 執行 `venv/bin/python handoffs/run_receipts/ffstat_probes/stable_start_receipts.py inventory --out handoffs/run_receipts/20260928-ffstat-r30-inventory.json` → `INVENTORY_RC=0`、`steps 391`、`unclassified []`，golden SHA-256 前後均 `91481e1f1af5...`；同複本 `venv/bin/python -m pytest -p no:cacheprovider tests/feature_engineering/test_ffstat_stable_start.py::test_nan_propagation_inventory_complete -q` → `1 passed`、`TEST_RC=0`。隔離單邊閉包縮小突變產出 `390` steps，golden 保持 `391`，同一測試 `TEST_RC=1`；故 r29 之「閉包意外縮小即紅」成立。

**類別**: other

**來源摘要**: handoffs/reconcile/20260926-ffstatauto-x-review-r29/synth.md#3614e638e572; docs/manifests/FFSTAT.json#cfdf0e220780; tests/feature_engineering/test_ffstat_stable_start.py#0785e104efde; handoffs/run_receipts/ffstat_probes/stable_start_receipts.py#bdbc189e42f7; tests/_golden/ffstat/nan_propagation_classes.json#91481e1f1af5

本輪必答核對：

1. **(1a)** 接受 `CODEX-R29-P1-01` 駁回理由並列入 `CLOSED`。**(1b)** 因接受駁回，不提出非蓄意綠燈反例；實跑的單邊閉包縮小突變反而在 `test_nan_propagation_inventory_complete` 以 `TEST_RC=1` 被攔下。三者同步縮小仍需另行刪改 golden 附碼證條目，已超出意外漂移序列。

2. **(2a)** 本輪標的無新缺陷。**(2b)** 未觀察到可重現的非蓄意綠燈反例；以 `--out tests/_golden/ffstat/nan_propagation_classes.json` 的參數誤用雖會改寫檔案，但輸出為 receipt 的 `steps` list 而非 golden 的 `steps` map，後續測試實跑 `TEST_RC=1`（`TypeError: unhashable type: 'dict'`），不是靜默放行。

3. **(3a)** assumed 成立。**(3b)** `rg -n 'nan_propagation_classes\.json' scripts tests handoffs/run_receipts/ffstat_probes` 僅命中 probe 說明／讀取與測試讀取；寫入型式交叉掃描結果 `DIRECT_WRITE_HITS=0`。正常 inventory 實跑 `INVENTORY_RC=0` 且 golden SHA-256 不變；因此沒有 repo 內例行 writer 使三者同步縮小。

4. **(4a)** 未查項①無命中；未查項②有「可由任意 `--out` 路徑覆寫」的介面命中，但沒有仍綠的命中。**(4b)** `stable_start_receipts.py:29` 以 `CLASSES.read_text()` 讀 golden，`:106` 接受任意 `--out`，`:110` 寫 `args.out`；實跑 `inventory --out tests/_golden/ffstat/nan_propagation_classes.json` 後檔案變為 `steps=list[391]`，完整性測試 `TEST_RC=1`。測試 `test_ffstat_stable_start.py:179-182` 讀取 golden 並對 AST／receipt／golden 做雙重 exact-set gate。

5. **(5a)** 本版 TODO 可放行實作：`VERDICT: proceed`。**(5b)** 無需列 P0／P1 blocker。

審查紀錄：一次建立複本的指令曾被 PreToolUse hook 以 `rm -rf` 擋下；另一次初始探針誤留在原 repo cwd，均未作為證據，後續改用新 `mktemp` 複本並以明確 workdir 重跑。原 repo 未修改碼、文檔、SPEC、manifest 或 git；只新增本交件檔。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R29-P1-01
