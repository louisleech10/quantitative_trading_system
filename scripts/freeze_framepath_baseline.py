"""FRAMEPATH Task 1.1：CGSA 指紋基準之凍結與比對（docs/FRAMEPATH_SPEC.md §G、Task 1.1）。

於 HEAD 6e07e0ad（Phase 1 任何生產碼改動之前）以真實 `data_cache/feature_klines/kline_cache.h5` 跑設定矩陣 C1–C9，
寫 `tests/_golden/framepath/cgsa_fingerprint.json`；`tests/feature_engineering/test_framepath_invariance.py`
以同一 `run_cell` 重跑並以 `compare_cell` 逐項比對（無容差）。

設定矩陣（`stat_payload` 級精簡指標、短窗；週期取值由 `ffstat_helpers` 參數給定，比對器不寫死週期或標的）：
- C1 單週期平穩化開；C2 單週期平穩化關；C3 多週期（主週期＋一個較長次週期，`FFACT_MULTI_TF_PARALLEL=0`）平穩化開；
- C4 ＝C1 於 `FFACT_L3_PERSIST_MODE` 之 streaming 與 hybrid 各一（子格 C4-streaming、C4-hybrid）；
- C5 ＝C1 同 work dir 第二次生成（resume 命中）；C6 ＝C3 但 `FFACT_MULTI_TF_PARALLEL=1`；
- C7 ＝C1＋`persist=False`；C8 ＝C1＋`FFACT_L3_PERSIST_MODE=in_memory`；
- C9 ＝C3＋`allow_partial_timeframes=True`，真實 kline 副本刪 `<symbol>/<次週期>` 之 data dataset 並讀回確認缺失，
  子行程啟動前（kline storage 建構前）於其環境把 `LEGACY_KLINE_CACHE_DIR` 指向空受控目錄 ⇒ `run_status=partial`。

每格內容（§G baseline 內容）：公開輸出欄名序列 sha256、欄數、列數、時間索引 sha256；逐欄 NaN／inf mask sha256
與 float32 值位元 sha256；平穩化決策表 sha256；manifest 經 `compare_domain.json` 篩選後之 canonical JSON sha256；
run_status、各週期 completeness 與失敗／降級原因；生成路徑收據（L3 落地模式、多週期 serial／parallel、L6.5 CGSA 臂）；
記憶體（`memory_guard._Readings`，根＝該格生成子行程，間隔 0.1 秒）峰值、讀數筆數、秒數。C7 以回傳結果與
completeness metadata 為比對對象。

凍結拒寫條件（§G、Task 1.1 邊界）：C5 與 C1 fingerprint 不等；C1–C8 任一 `run_status` 非 complete；C9 之
`run_status` 非 partial 或 skipped／failed 週期不含該次週期；任一格記憶體 FAIL（讀數 `failed` 非空、`injected`
為真、無讀數、峰值 ≥ 2 GB；C6 無任一讀數含根以外成員）；`ICFA_GUARD_READINGS_FILE` 已設 ⇒ 具名拒跑。

用法：
  PYTHONPATH=. venv/bin/python scripts/freeze_framepath_baseline.py freeze   # 只准於 HEAD 6e07e0ad 碼態執行
  PYTHONPATH=. venv/bin/python scripts/freeze_framepath_baseline.py check    # 重跑並比對，列出差異
真實資料重測試：各格單組串行；委員審查期間不跑。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO = Path(__file__).resolve().parents[1]
BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
COMPARE_DOMAIN_REL = "tests/_golden/framepath/compare_domain.json"
HEAD_COMMIT_PREFIX = "6e07e0ad"
CELLS = ("C1", "C2", "C3", "C4-streaming", "C4-hybrid", "C5", "C6", "C7", "C8", "C9")
PARTIAL_CELLS = ("C9",)
PEAK_LIMIT_BYTES = 2 * 1024 ** 3
SAMPLE_INTERVAL_SECONDS = 0.1
# 每格 fingerprint 之比對項（§G baseline 內容；compare_cell 逐項無容差比對）
FINGERPRINT_KEYS = (
    "column_names_sha256", "column_count", "row_count", "time_index_sha256", "columns",
    "stationarity_decisions_sha256", "manifest_sha256", "run_status", "completeness", "failure_reasons",
    "path_receipt",
)


class FramepathBaselineError(RuntimeError):
    """凍結／比對前置條件不成立（具名拒寫或拒跑）。"""


CODE_STATE_ROOTS = ("momentum", "api", "config")


def code_state_errors(git_runner: Any = None) -> List[str]:
    """凍結前置：工作樹之 `momentum／api／config` 須與錨點 6e07e0ad 逐位元相同——①`git rev-parse 6e07e0ad` 可解析
    ②`git diff --name-only <錨點完整 sha> -- <roots>`（以錨點為比較端、含未提交改動；不得以 HEAD 為比較端）為空
    ③`git ls-files --others --exclude-standard -- <roots>` 為空（未追蹤之原始碼亦屬碼態）；任一不成立 ⇒ 錯誤字串
    （freeze 具名拒寫、不產任何輸出）。執行時 HEAD 可為錨點之後之提交（TODO／審查提交只動 tests／docs），故判準是
    碼態而非 HEAD 值；HEAD 值只記入基準供追溯。`git_runner(args) -> (rc, stdout)` 供測試注入（審查 r17
    CODEX-R17-P1-01、r18 CODEX-R18-P1-01）。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def resolve_commits(git_runner: Any = None) -> Dict[str, str]:
    """{"code_anchor": `git rev-parse 6e07e0ad` 之完整 sha, "head_commit": `git rev-parse HEAD`}——兩次獨立解析，
    freeze 寫入基準（審查 r19 CODEX-R19-P1-02）。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def load_compare_domain(path: Path = REPO / COMPARE_DOMAIN_REL) -> Dict[str, Any]:
    """讀 `compare_domain.json` 並驗：category ∈ allowed_categories；path 之最後一段不屬 forbidden keys 或
    `feature_storage.COMPLETENESS_FIELD_NAMES`；path 語法只含物件鍵與單層 `*`。違反 ⇒ `FramepathBaselineError`。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def filter_manifest(manifest: Mapping[str, Any], domain: Mapping[str, Any]) -> Dict[str, Any]:
    """依 domain.exclude 刪除 manifest 中匹配之純量鍵；匹配到物件或陣列 ⇒ `FramepathBaselineError`（防祖先鍵整段排除）。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def manifest_sha256(manifest: Mapping[str, Any], domain: Mapping[str, Any]) -> str:
    """`filter_manifest` 後之 canonical JSON（sort_keys、(",", ":")、ensure_ascii=False）utf-8 sha256。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def cell_settings(cell: str) -> Dict[str, Any]:
    """格之設定：payload（ffstat_helpers.stat_payload 系）、env 覆寫、training_tfs、persist、repeat（C5＝2）、
    allow_partial、drop_secondary（C9）。週期與標的一律取自 ffstat_helpers 常數。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def generate_cell(cell: str, work_root: Path, *, force_regenerate_second: bool = False) -> Dict[str, Any]:
    """行程內跑一格生成並回傳 {"fingerprint", "receipt"}（不含記憶體；`run_cell` 於子行程呼叫本函式並取樣）。
    `receipt["resume_hit"]`＝第二次生成期間 `ColumnGroupRegistry.resume_from_manifest` 實際被呼叫且回傳非空 registry
    （以包裝該 classmethod 之 spy 觀測，不以格名推定；審查 r18 CODEX-R18-P1-02）；只 C5 有第二次生成，其兩次皆以
    `force_regenerate=False`。`force_regenerate_second=True` 只供 mutation 測試（第二次強制重算 ⇒ resume_hit 須 False）。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def run_cell(cell: str, work_root: Path) -> Dict[str, Any]:
    """於子行程跑一格生成，父行程以 `memory_guard._Readings`（根＝子行程）每 0.1 秒取樣；回傳
    {"fingerprint": {FINGERPRINT_KEYS…}, "memory": {"peak_bytes", "readings", "seconds", "non_root_member_seen"},
    "receipt": {"resume_hit": bool（第二次生成實際由 CGSA resume 跳過層計算之觀測值，取自 registry 之 resume 狀態而非
    比對輸出；C5 須 True、其餘格須 False——審查 r17 CODEX-R17-P1-02）, …，C9 另含 symbol、source_kline、kline_copy、
    dropped_timeframe、deleted_dataset（`<symbol>/<次週期>`）、readback_before（"present"）、deleted_readback
    （"missing"）、legacy_kline_dir、legacy_kline_dir_entries_at_start（[]）、child_env（子行程實際之
    LEGACY_KLINE_CACHE_DIR）——審查 r19 CODEX-R19-P1-06}}。`ICFA_GUARD_READINGS_FILE` 已設 ⇒ 拒跑。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def memory_gate_errors(cell: str, memory: Mapping[str, Any]) -> List[str]:
    """§G 記憶體閘：讀數 failed 非空、injected、無讀數、峰值 ≥ PEAK_LIMIT_BYTES、C6 無根以外成員 ⇒ 錯誤字串。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def compare_cell(baseline: Mapping[str, Any], fresh: Mapping[str, Any]) -> List[str]:
    """逐項（FINGERPRINT_KEYS；columns 逐欄之 NaN／inf mask 與 float32 值位元 sha256）無容差比對；回傳
    「項目／欄名」差異列表（空＝相等）。不得含任何週期或標的字面。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def freeze(out: Path = REPO / BASELINE_REL) -> Dict[str, Any]:
    """先以 `code_state_errors()` 核對碼態（非空 ⇒ `FramepathBaselineError`，不產任何輸出），再跑全部格、驗拒寫條件後
    寫基準：`code_anchor`（6e07e0ad 完整 sha）、`head_commit`（執行時 `git rev-parse HEAD`）、`code_state_errors`（[]）、
    python、各格 fingerprint／memory／receipt。"""
    raise NotImplementedError("FRAMEPATH Task 1.1")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("freeze", "check"))
    args = ap.parse_args(argv)
    if args.action == "freeze":
        freeze()
        return 0
    raise NotImplementedError("FRAMEPATH Task 1.1")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
