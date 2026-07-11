# IC 1e+1b B5 終驗 R3 — Codex

前置：`bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS，body sha256=`b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043`。

## F5c — STILL-OPEN（BLOCKING）

1. **雙件 file receipt — CLOSED**：`shasum -a 256 baseline_old_regen_{854d444,c0b29ac}.json` 實算依序為 `b31115d284b2452abbb193e62e369944cc53a214f0df758e7043c4cd3af4c40b`、`3d2232c17a1c14fc4e369fad1198e46810ac8e670c721446cd78b9ba87571f8a`，逐字吻合 `regen_receipts.json` 與各自 meta 的 `baseline_sha256`。
2. **normalized receipt — CLOSED**：獨立 `json.loads` 後移除頂層 `generated_at`，再以 `json.dumps(payload, sort_keys=True)` UTF-8 取 SHA-256；兩件皆為 `2f3617b96cab5817168f3e7fb77e9fc7b0936a4688e48d99ee5839af9ba7c1ec`，吻合 receipt，交叉相等成立。（注意：receipt 未明載 serialization 規則；本次由匹配值反推出上述規則。）
3. **meta override — CLOSED**：兩份 `baseline_meta_regen_*.json` 的 `request.config_override.ic_train_test_split` 均為 `false`；兩份 meta 除 `baseline_sha256` 與 `task_id_used_for_freeze` 外相同。
4. **reproduction command / README — STILL-OPEN**：兩份 meta 與 receipt 的 command 都是 `python tests/golden/ic_phase1_1a_cut1/freeze_baseline.py --max-features 50 --timeout-seconds 1800`，字串未記 override；目錄內亦無 patched freeze script。`git show {854d444,c0b29ac}:tests/golden/ic_phase1_1a_cut1/freeze_baseline.py | rg 'ic_train_test_split|config_override'` 兩者皆 0 match。因此 README 第 4 點「reproduction_command 皆記錄 override」不實，command 在所標 commit 單獨執行也無法證明套用 False。
5. **README 全主張之目錄內支撐 — STILL-OPEN**：目錄可支撐雙 JSON、雙 meta、file/normalized hash 相等及 `request.config_override=false`；但無 inputs/其 hash、worktree/run log、patched script、commit/full-SHA provenance、原檔滅失證據、schema/yaml 歷史證據、Grok 首跑證據、現行兩態重凍測試 receipt 或 `IC1EB-GOLDEN-DIFF.md`。README 對這些事項僅自述或指向目錄外文件，不符合「每一主張皆有目錄內產物支撐」。

RECEIPT: `git cat-file -t 854d444 c0b29ac` 分別確認為 commit；full SHA=`854d4448fc70d1c2760874921debfb8737afe9ab`,`c0b29ac62e70db21d19c31cf1bd65f8fd3f2feac`，但 `regen_receipts.json` 只以短 SHA 作 key，未把 full SHA/commit metadata 綁入收據。
ASSUMPTIONS_VERIFIED: generated_at 僅豁免頂層；兩件 JSON 可解析；收據採 Python default sorted JSON serialization；meta request override 與 command 實值；README 逐項對目錄 inventory。
TESTS_RUN: reconcile stamp check PASS；兩件 `shasum -a 256` PASS；獨立 normalized SHA 重算 2/2 PASS；meta `jq`/`diff` PASS；兩 commit script override grep 0/2 match（反證）；README→目錄產物逐項稽核 FAIL。
FAILURES_SEEN: reproduction command 未攜帶或在目錄內綁定 override；README 多項歷史/程序主張缺目錄內 receipt。
SCOPE_CHANGES: 僅新增 `handoffs/IC1EB-B5-REVIEW-R3-codex.md`；未改其他檔案。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查與輕量 hash 計算）。

VERDICT: BLOCK
