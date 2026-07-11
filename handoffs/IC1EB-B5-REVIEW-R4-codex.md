# IC 1e+1b B5 終驗 R4 — Codex

範圍：只重驗 R3 兩殘項；除本檔外未改 workspace 檔案。

1. **reproduction command／腳本快照 — CLOSED**：`shasum -a 256 freeze_baseline_used_for_regen.py` 實算 `7f35f550f35606793f5cafc39b290bb8fefa6a613277b09a3413f39203861136`，與 receipts 完全一致。快照 L61-66 先取既有 `inputs/` h5+meta，L105 使用該 materialized inputs，L113-116 顯式 `config_override={"ic_train_test_split": False}`；`PYTHONPYCACHEPREFIX=/tmp/ic1eb-r4-pycache python -m py_compile ...` → PASS。兩原 commit 腳本以 `git show ... | rg 'ic_train_test_split|config_override'` 均 0 match；README/receipts 已明說原 meta command 不能單獨重產，正確程序為複製本快照及指定 inputs 入 worktree 後執行，未再冒充原 command 可重產。

2. **receipts 自洽 — CLOSED**：`git rev-parse 854d444 c0b29ac` 分別為 receipts 的 full SHA `854d4448...e9ab`、`c0b29ac6...feac`，且 `git cat-file -t` 均為 commit。主樹兩 inputs 實算 SHA 為 `fb3332ba...ba21`、`c3aa5921...f37f`，逐字吻合 receipts。雙 artifact file SHA 實算 `b31115d2...c40b`／`3d2232c1...f8a`，同時吻合 receipts 與各 meta `baseline_sha256`；meta 的 override、reproduction command、archive 路徑亦逐欄一致。

3. **normalized 規則 — CLOSED**：依 receipts 明載規則 `json.loads → pop 頂層 generated_at → json.dumps(sort_keys=True, ensure_ascii=False) UTF-8 → sha256` 獨立重算，兩件皆為 `2f3617b96cab5817168f3e7fb77e9fc7b0936a4688e48d99ee5839af9ba7c1ec`；`cross_commit_normalized_equal=true` 自洽。

4. **README A 區 — CLOSED**：A1 有雙 artifact+雙 meta+receipts；A2 有雙 normalized receipt、規則及雙件實體；A3 有雙 meta request；A4 有腳本快照、SHA、內容與 reproduction 程序；A5 有 receipts inputs SHA 且主樹實檔重 hash 相符。五條皆有本目錄產物支撐；未把原 commit 未留存的執行紀錄說成存在。

5. **README B 區 — CLOSED**：五組外部事項均明標為 pointer；所指 quarantine、B2 review、R2 review、Grok result、GOLDEN-DIFF 檔皆存在。唯一不可直接證明的「原凍結者套用未記錄 override」已明標為推論並交代依據與原始紀錄不可得；未僭稱為本目錄直接證據。

RECEIPT: `shasum -a 256` 腳本+2 inputs+2 artifacts 全吻合；Python receipt probe=`file_match/normalized_match/override_match/command_match` 兩 commit 全 True；pointer inventory 5/5 存在；原腳本 override grep 0/2。
ASSUMPTIONS_VERIFIED: receipts JSON 可解析；full SHA 指向 commit；腳本顯式 override 且重用 inputs；主樹 inputs 身分；normalized serialization；README A/B 證據邊界。
TESTS_RUN: 上述輕量 hash/JSON probe/git object+grep/pointer inventory/py_compile 均 PASS。
FAILURES_SEEN: 首次 `py_compile` 因系統 cache 路徑 sandbox PermissionError；改用 `/tmp` cache 後 PASS，workspace 無 `__pycache__`。
SCOPE_CHANGES: 僅新增 `handoffs/IC1EB-B5-REVIEW-R4-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查；未執行重生、未觸碰 data_cache）。
STATUS: DONE

VERDICT: PASS
