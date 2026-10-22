"""NUMVIEW Task 0.6 — 參考實作正確性證明之收據產生器（docs/NUMVIEW_SPEC.md Task 0.6）。

以 `tests/feature_engineering/test_numview_reference.py` 之四類證明（(a) 手算、(b) 第三方交叉核對〔真實 kline 欄與真實 L1 欄〕、
(c) 性質、(d) 任意精度〔含近零絕對門檻〕）與鏈之順序／錨點檢查
對 `tests/feature_engineering/numview_reference.py` 逐類實跑；四類皆零違規方寫收據
`handoffs/run_receipts/<date>-numview-reference-proof.json`（含 (d) 之最大相對誤差、近零值格數、兩精度之一致位數，以及邊界④
近零與價格級距混合之 (d) 報告），否則 rc=1、不寫收據。秒級；真實 kline 小段（不生成特徵）。參考實作模組本身不寫檔（其 import
白名單不含檔案與 JSON），故由本探針寫收據。

用法：venv/bin/python handoffs/run_receipts/numview_probes/reference_proof.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO: Path = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

RECEIPT_NAME = "{date}-numview-reference-proof.json"


def _gate() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("numview_estimate_gate", Path(__file__).resolve().with_name("_estimate_gate.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("無法載入 _estimate_gate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("numview_estimate_gate", module)
    spec.loader.exec_module(module)
    return module


def build_receipt() -> Dict[str, Any]:
    """實跑四類證明並組收據本體（`proofs` 各類之違規清單；`proof_d` 為 (d) 報告）。不寫檔。"""
    import numpy as np

    from tests.feature_engineering import numview_reference as ref
    from tests.feature_engineering import test_numview_reference as proofs

    violations: Dict[str, List[str]] = {
        "a_hand_cases": proofs.proof_a_violations(ref),
        "b_third_party_real_kline": proofs.proof_b_violations(ref),
        "b_third_party_real_l1": proofs.proof_b_l1_violations(ref),
        "c_properties": proofs.proof_c_violations(ref),
        "d_arbitrary_precision": proofs.proof_d_violations(ref),
        "d_near_zero_and_mixed": proofs.proof_d_near_zero_violations(ref),
        "d_independent_decimal_oracle": proofs.proof_d_independent_violations(ref),
        "chain_order_and_anchor": proofs.chain_violations(ref),
        "imports": proofs.import_violations(proofs._read_reference_source()),
    }
    close = proofs._real_slice(120)["close"]
    mixed = proofs._real_slice(40)["close"]
    mixed = np.concatenate([mixed[:20], mixed[20:] * 1e-9])
    criteria = _gate().resolve_criteria_path()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "head": head,
        "command": "venv/bin/python handoffs/run_receipts/numview_probes/reference_proof.py",
        "criteria_sha256": hashlib.sha256(criteria.read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(Path(ref.__file__).read_bytes()).hexdigest(),
        "inputs": {"kline": str(proofs.nh.KLINE_PATH.relative_to(REPO)), "symbol": "BTCUSDT", "timeframe": "1h",
                   "proof_b_rows": 240, "proof_b_columns": ["close", "volume"],
                   "proof_b_l1_column": proofs.PROOF_B_L1_FEATURE,
                   "proof_b_l1_source": str(proofs.ICPOSTLEAK_CONTRACT_PATH.relative_to(REPO)),
                   "proof_d_rows": 120, "window": 20,
                   "epsilon": 1e-8},
        "thresholds": {"relative": ref.PROOF_RELATIVE_THRESHOLD, "near_zero_cutoff": ref.PROOF_NEAR_ZERO_CUTOFF,
                       "near_zero_abs": ref.PROOF_NEAR_ZERO_ABS, "precisions": list(ref.PROOF_PRECISIONS),
                       "min_agreeing_digits": ref.PROOF_MIN_AGREEING_DIGITS},
        "proofs": violations,
        "proof_d": ref.proof_d_report(close, 20, 1e-8),
        "proof_d_boundary_near_zero_mixed": ref.proof_d_report(mixed, 20, 1e-8),
        "all_passed": all(not v for v in violations.values()),
        "exit_code": 0 if all(not v for v in violations.values()) else 1,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    receipt = build_receipt()
    if not receipt["all_passed"]:
        print(json.dumps(receipt["proofs"], ensure_ascii=False, indent=2), file=sys.stderr)
        print("[reference_proof] 證明未全綠，不寫收據", file=sys.stderr)
        return 1
    out = REPO / "handoffs" / "run_receipts" / RECEIPT_NAME.format(date=datetime.now().strftime("%Y%m%d"))
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = receipt["proof_d"]
    print(f"[reference_proof] 收據 {out.relative_to(REPO)}：(d) 最大相對誤差 {d['max_relative_error']:.3e}、"
          f"近零格 {d['near_zero_count']}、兩精度一致位數 {d['min_agreeing_digits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
