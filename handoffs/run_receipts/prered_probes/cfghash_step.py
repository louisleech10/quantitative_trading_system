"""bisect 步驟：於 cwd 版本計算凍結設定（1h＋12h、primary 1h）之 config_hash，等於 1dbe534e… ⇒ exit 0（good），
否則 exit 1（bad）；無法計算 ⇒ exit 125（skip）。"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
try:
    spec = importlib.util.spec_from_file_location("ffb", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    from momentum.factories import create_feature_factory

    f = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    payload = freeze._fixed_config_payload(["1h", "12h"], "1h")
    s, e = freeze._window_dates()
    h = f._compute_config_hash(f._resolve_config(payload), "BTCUSDT", "1h", start_date=s, end_date=e)
except Exception as exc:  # noqa: BLE001
    print("skip", type(exc).__name__, exc)
    sys.exit(125)
print("hash", h)
sys.exit(0 if h == "1dbe534ed08793b0ea2f80b3748fa1a0" else 1)
