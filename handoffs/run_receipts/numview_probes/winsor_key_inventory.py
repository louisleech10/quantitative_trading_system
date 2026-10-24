"""NUMVIEW winsor 缺鍵盤點（docs/NUMVIEW_SPEC.md Task 2.1 改法）：生產碼（momentum/、api/）每個 `FeaturePreprocessor(`／
`create_feature_preprocessor(` 建構點之設定是否帶縮尾 `method` 鍵。

AST 窮舉建構點（呼叫原文＋檔:行）；每點依其設定來源以生產函式實跑產出該設定（預設 `FactoryConfig`），檢 `winsorization`
段含 `method` 鍵。建構點未登記於 `SOURCE_BUILDERS`（新增之建構點）⇒ rc≠0（fail-closed，須補登記）。收據
`handoffs/run_receipts/<date>-numview-winsor-key-inventory.json`：`sources[].{path（檔:行）, call, source, has_method_key,
winsor_enabled}`。盤點不成立（任一 has_method_key 為假）⇒ rc 3（SPEC：停下回 Task 1.5 增決定點）。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # 以腳本執行時 repo 根不在 sys.path（同 precision_chain.py:35）
    sys.path.insert(0, str(REPO))
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
SCAN_ROOTS = ("momentum", "api")
CALL_NAMES = ("FeaturePreprocessor", "create_feature_preprocessor")


def scan_sites() -> List[Dict[str, Any]]:
    """生產碼之建構點：{path（repo 相對）, line, call（首參數之 `ast.unparse`）}。定義本身不計。"""
    out: List[Dict[str, Any]] = []
    for root in SCAN_ROOTS:
        for path in sorted((REPO / root).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if name in CALL_NAMES:
                    first = ast.unparse(node.args[0]) if node.args else "<none>"
                    out.append({"path": str(path.relative_to(REPO)), "line": int(node.lineno), "call": f"{name}({first})"})
    return out


def _factory() -> Any:
    from momentum.factories import create_feature_factory

    return create_feature_factory()


def _factory_config() -> Any:
    """生產預設設定（`FeatureFactory._resolve_config(None)`，同未給覆寫之生成）。"""
    return _factory()._resolve_config(None)


def _l65_config() -> Dict[str, Any]:
    return _factory()._preprocessing_config_dict(_factory_config())


def _l7_raw_config() -> Dict[str, Any]:
    return _factory()._build_l7_raw_preprocessing_config(_factory_config())


def _native_scaled_config() -> Dict[str, Any]:
    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import scale_preprocessing_config_for_native

    cfg = _factory_config()
    return scale_preprocessing_config_for_native(_l7_raw_config(), "4h", cfg.timeframes.primary)


def _post_ic_config() -> Dict[str, Any]:
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    parent = FeaturePreprocessor(_l65_config())
    return parent._build_post_ic_transform_config(selected_columns=["x"], config=_factory_config().preprocessing)


def _ic_page_config() -> Dict[str, Any]:
    from momentum.factories import create_post_ic_transform_config

    return create_post_ic_transform_config(rank=True, rank_window=252, zscore=True, zscore_windows=[100, 252],
                                           gaussian=False).model_dump()


#: (檔, 呼叫原文) → (來源說明, 產出該點設定之生產函式)
SOURCE_BUILDERS: Dict[tuple, tuple] = {
    ("momentum/FeatureEngineering/feature_factory.py", "FeaturePreprocessor(self._preprocessing_config_dict(config))"):
        ("FeatureFactory._preprocessing_config_dict（IC-first post-IC 之母實例）", _l65_config),
    ("momentum/FeatureEngineering/feature_factory.py", "FeaturePreprocessor(preprocessing_config)"):
        ("FeatureFactory._build_l7_raw_preprocessing_config（生成 L6.5）", _l7_raw_config),
    ("momentum/FeatureEngineering/feature_factory.py", "FeaturePreprocessor(winsor_config)"):
        ("scale_preprocessing_config_for_native(_build_l7_raw_preprocessing_config)（校準縮尾器）", _native_scaled_config),
    ("momentum/FeatureEngineering/preprocessing/feature_preprocessor.py", "FeaturePreprocessor(post_ic_config)"):
        ("FeaturePreprocessor._build_post_ic_transform_config（transform_selected）", _post_ic_config),
    ("momentum/FeatureEngineering/preprocessing/feature_preprocessor.py", "FeaturePreprocessor(scaled_config)"):
        ("scale_preprocessing_config_for_native（native-tf 子實例）", _native_scaled_config),
    ("momentum/factories.py", "FeaturePreprocessor(config)"):
        ("create_feature_preprocessor 之呼叫端設定（生產呼叫端＝IC 頁 create_post_ic_transform_config）", _ic_page_config),
    ("api/services/ic_analysis_service.py", "create_feature_preprocessor(transform_config.model_dump())"):
        ("create_post_ic_transform_config().model_dump()（IC 頁第三步）", _ic_page_config),
}


def build(sites: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    unregistered: List[str] = []
    for site in sites:
        key = (site["path"], site["call"])
        if key not in SOURCE_BUILDERS:
            unregistered.append(f"{site['path']}:{site['line']} {site['call']}")
            continue
        label, fn = SOURCE_BUILDERS[key]
        config = fn()
        winsor = config.get("winsorization") or {}
        rows.append({"path": f"{site['path']}:{site['line']}", "call": site["call"], "source": label,
                     "has_method_key": "method" in winsor, "winsor_enabled": bool(winsor.get("enabled", True)),
                     "method": winsor.get("method")})
    stale = sorted(f"{p} {c}" for p, c in SOURCE_BUILDERS if not any((s["path"], s["call"]) == (p, c) for s in sites))
    return {"sources": rows, "unregistered_sites": unregistered, "stale_registrations": stale}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """rc 0＝每個建構點皆已登記且帶 method 鍵；rc 2＝有未登記或過期登記；rc 3＝有建構點之設定缺 method 鍵。"""
    body = build(scan_sites())
    receipt = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
               "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
               "command": "venv/bin/python handoffs/run_receipts/numview_probes/winsor_key_inventory.py",
               "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **body}
    if body["unregistered_sites"] or body["stale_registrations"]:
        receipt["exit_code"] = 2
    elif not all(r["has_method_key"] for r in body["sources"]):
        receipt["exit_code"] = 3
    else:
        receipt["exit_code"] = 0
    dest = RECEIPTS_DIR / f"{datetime.now().strftime('%Y%m%d')}-numview-winsor-key-inventory.json"
    dest.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"[winsor-inventory] 收據 {dest}；exit_code {receipt['exit_code']}；sources {len(body['sources'])}；"
          f"未登記 {body['unregistered_sites']}；過期 {body['stale_registrations']}")
    return int(receipt["exit_code"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
