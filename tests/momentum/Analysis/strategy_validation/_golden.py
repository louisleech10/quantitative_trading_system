"""GAP-1 §G golden 檔之唯一 loader（B4 review N6：sha256 常數單一定義處；三檔測試皆經此驗 sha）。

改 `tests/momentum/Analysis/golden/gap1_reference_cases.json` 須同步改 `GOLDEN_SHA256`（兩處變更＝可審計；就地改寫即紅）。
"""

import hashlib
import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "golden" / "gap1_reference_cases.json"
GOLDEN_SHA256 = "09a04b67168d571f1b1ec48cbfbfa0c402fd301bccd09a5b60d15bad1e95c418"


def load_golden() -> dict:
    raw = GOLDEN_PATH.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == GOLDEN_SHA256, f"golden 檔被就地改寫（sha256 {actual[:12]}… ≠ {GOLDEN_SHA256[:12]}…）"
    return json.loads(raw.decode("utf-8"))
