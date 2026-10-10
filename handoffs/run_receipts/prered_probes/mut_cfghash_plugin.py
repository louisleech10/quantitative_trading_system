"""PRE-RED Task 2.2 mutant 外掛：_generate_features_impl 傳空字串 config_hash 給 _prepare_cgsa_registry（記憶體內改寫）。"""

import inspect
import textwrap

from momentum.FeatureEngineering import feature_factory as ff

_src = textwrap.dedent(inspect.getsource(ff.FeatureFactory._generate_features_impl))
_old = 'self._prepare_cgsa_registry(symbol, timeframe, config_hash or "")'
assert _old in _src, "mutant 錨點不存在"
_ns: dict = {}
exec(compile(_src.replace(_old, 'self._prepare_cgsa_registry(symbol, timeframe, "")'), ff.__file__, "exec"),
     ff.__dict__, _ns)
ff.FeatureFactory._generate_features_impl = _ns["_generate_features_impl"]
