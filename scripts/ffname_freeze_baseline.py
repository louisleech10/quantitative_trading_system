#!/usr/bin/env python3
"""FF-NAME 改前凍結腳本空殼（docs/FFNAME_SPEC.md §G、Task 0.1）。

用法（實作後）：
  venv/bin/python scripts/ffname_freeze_baseline.py            # 於改前 HEAD 碼態凍結
  venv/bin/python scripts/ffname_freeze_baseline.py --check    # 驗 baseline.json 封閉涵蓋

職責（SPEC §G）：
- 以真實 `data_cache/feature_klines/kline_cache.h5` 跑 reference 設定（全部產生端；多週期 ["1h","12h"]；
  CGSA 序列 `FFACT_MULTI_TF_PARALLEL=0`；L5 另以三標的小窗 run）；寫入一律經
  `tests.feature_engineering.fftfmeta_golden_helpers.prepare_env` 之隔離（不寫正式 data_cache）。
- 於事實盤點 A1–A12 每個組名點包裝，記錄組名零件 `NamingPart`；manifest 任一欄無零件紀錄 ⇒ 凍結失敗。
- 逐欄（舊名為鍵）記 dtype、shape、NaN mask sha256、值 sha256；另記 L2 配對簽名集合、L4 lag 輸入集合、
  欄序、group 結構、平穩化決策（鍵與值）。
- 另記 Task 4.3 重凍對象 golden（`tests/_golden/ffname/contract.json` 之 `refreeze.goldens`）之改前逐欄值雜湊
  （`golden_values`：golden 路徑 → {舊欄名 → 值雜湊}），作為重凍之不可變值 oracle（審查 r12 CODEX-R12-P1-04）。
- 舊名→新名映射由零件以新 formatter 推導（`derive_new_name`）；禁字串清單與全欄 replace。

本檔為 TODO 落點（介面凍結；由 handoffs/ 移入版控路徑，審查 r12 P1-01）；函式體由 FFNAME Phase 0 實作。不得改生產碼。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.json"
# 審查 r13 P1-05：baseline 不可變之錨——Task 0.1 產出 baseline.json 時一併寫其 sha256（單行 hex），Phase 2 起不得再改
BASELINE_SHA_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.sha256"
RECEIPT_PATH = REPO / "handoffs" / "run_receipts" / "ffname-value-invariance.json"


class FreezeError(RuntimeError):
    """凍結失敗（同名欄出自兩個組名點、manifest 欄缺零件紀錄等）；訊息須列出涉及之欄名與組名點。"""


@dataclass(frozen=True)
class NamingPart:
    """單一欄之組名零件（SPEC §G）：`(舊名, kind, source, raw_lookup_key, category, indicator, params, ops, tf)` 與組名點。

    `source`／`raw_lookup_key` 照實記錄，現況為 None 者（microstructure、tail-risk）記 None，不得補字串。
    """

    old_name: str
    kind: str
    source: Optional[str]
    raw_lookup_key: Optional[str]
    category: Optional[str]
    indicator: Optional[str]
    params: Tuple[Tuple[str, ...], ...]  # 同 FeatureIdentity（SPEC v13）：外層為配對成員，空 tuple 表無參數
    ops: Tuple[str, ...]
    tf: Optional[str]
    point: str


class PartRecorder:
    """組名零件之收集器（Task 0.1 邊界①②）。"""

    def record(self, part: NamingPart) -> None:
        """記錄一筆零件；同一 `old_name` 已由**另一個**組名點記錄 ⇒ `FreezeError`（訊息列出欄名與兩個組名點）。"""
        raise NotImplementedError("FFNAME Task 0.1")

    def parts(self) -> Dict[str, NamingPart]:
        """舊名 → 零件。"""
        raise NotImplementedError("FFNAME Task 0.1")

    def to_json(self) -> List[Dict[str, Any]]:
        """可序列化形式（None 保留為 JSON null）。"""
        raise NotImplementedError("FFNAME Task 0.1")


def reference_payloads() -> Dict[str, Dict[str, Any]]:
    """§G reference 設定：`main`（全部產生端、多週期）與 `xsec`（L5 三標的小窗）。"""
    raise NotImplementedError("FFNAME Task 0.1")


def missing_parts(manifest_columns: Iterable[str], parts: Mapping[str, NamingPart]) -> List[str]:
    """manifest 中無零件紀錄之欄（封閉涵蓋；非空 ⇒ 凍結失敗）。"""
    raise NotImplementedError("FFNAME Task 0.1")


def derive_new_name(part: NamingPart, timeframe: str) -> str:
    """由零件以新 formatter（`feature_naming.format_feature_name`）推導新名；禁字串 replace。"""
    raise NotImplementedError("FFNAME Task 0.1")


def derive_mapping(parts: Mapping[str, NamingPart], timeframe_of: Mapping[str, str]) -> Dict[str, str]:
    """舊名（含週期標記）→ 新名之映射。"""
    raise NotImplementedError("FFNAME Task 0.1")


def golden_value_fingerprints(path: Path) -> Dict[str, str]:
    """單一 golden 檔之逐欄值雜湊（欄名 → 值雜湊；與欄名無關之值位元組雜湊）。
    同一函式於 Task 0.1 凍結改前 golden（寫入 baseline `golden_values`）、於 Task 4.3 重算新 golden；
    各 golden 檔格式之解讀由本函式負責。審查 r13：每個重凍對象 golden 之結果須非空，且鍵數 == `golden_columns(path)` 之欄數。"""
    raise NotImplementedError("FFNAME Task 0.1")


def golden_columns(path: Path) -> List[str]:
    """單一 golden 檔所含之特徵欄名清單（與值雜湊分開解讀，供「fingerprint 數 == 欄數」之完整性比對）。"""
    raise NotImplementedError("FFNAME Task 0.1")


def run_reference(work_dir: Path, *, record_parts: bool) -> Dict[str, Any]:
    """跑 reference（真實 kline）並回傳 fingerprint：
    `columns`（名 → {dtype, shape, nan_sha256, value_sha256}）、`column_order`、`group_ids`、`groups`（group_id → 欄名清單）、
    `l2_pairs`、`l4_lag_inputs`、`stationarity_keys`、`stationarity_decisions`（決策鍵 → 決策值；SPEC v13 Task 4.2 比對基準）、
    `manifest`（含 `feature_naming_version`，改前為缺）、
    `manifest_groups`（group_id → 欄名清單）、`parts`（record_parts 時）、
    `run`（`{"base", "symbol", "tf", "config_hash"}`：主週期 run 位置，供以 FeatureReader 讀值驗 lag 位移）。"""
    raise NotImplementedError("FFNAME Task 0.1")


def freeze(out_path: Path = BASELINE_PATH) -> int:
    """改前 HEAD 碼態凍結（兩次重跑 baseline sha256 須相同）；baseline 另含 `golden_values` 與 `golden_column_counts`；
    同時寫 `BASELINE_SHA_PATH`（baseline.json 之 sha256）；rc 0 成功。"""
    raise NotImplementedError("FFNAME Task 0.1")


def check(path: Path = BASELINE_PATH) -> int:
    """驗 baseline：無紀錄欄數 == 0；L2 配對簽名、lag 輸入集合、欄序、group、平穩化決策、golden_values 均已記；rc 0＝通過。"""
    raise NotImplementedError("FFNAME Task 0.1")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只驗既有 baseline.json")
    parser.add_argument("--out", default=str(BASELINE_PATH))
    args = parser.parse_args(argv)
    if args.check:
        return check(Path(args.out))
    return freeze(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
