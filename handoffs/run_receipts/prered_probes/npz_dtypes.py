"""列出 npz 中欄之 dtype 分布（可給名稱樣式過濾）。用法：python npz_dtypes.py <npz> [regex]"""

import re
import sys
from collections import Counter

import numpy as np

z = np.load(sys.argv[1])
rx = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
names = [n for n in z.files if rx is None or rx.search(n)]
print(len(names), Counter(str(z[n].dtype) for n in names))
