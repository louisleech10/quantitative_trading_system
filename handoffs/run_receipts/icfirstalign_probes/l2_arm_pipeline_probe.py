import os, sys
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
import scripts.freeze_icfirstalign_baseline as f
from momentum.FeatureEngineering import feature_factory as ff
real = ff.FeatureFactory._layer2_derived_features
out = []
def spy(self, layer1, data, config):
    res = real(self, layer1, data, config)
    if getattr(self, "_calibration_domain", False) and not out:
        eng_cls = ff._derived_operator_engine_cls(); eng = eng_cls(self._filter_operators_config(config.operators))
        specs = self._build_indicator_specs(layer1, config)
        parts = [eng.compute_category(layer1, data, specs, c) for c in eng_cls.OPERATOR_CATEGORIES]
        cat = pd.concat([p for p in parts if p is not None and not p.empty], axis=1)
        ret = res.data
        common = [c for c in ret.columns if c in cat.columns]
        a = ret[common].to_numpy(np.float64); b = cat[common].set_axis(ret.index).to_numpy(np.float64)
        both = np.isfinite(a)&np.isfinite(b)
        out.append(dict(l1_dtypes=sorted({str(t) for t in layer1.dtypes}), ret_dtypes=sorted({str(t) for t in ret.dtypes}), cols=len(common), f64diff=int((both&(a!=b)).sum()), f32diff=int((both&(a.astype(np.float32)!=b.astype(np.float32))).sum())))
    return res
ff.FeatureFactory._layer2_derived_features = spy
cap = {}
f._run_generation(f.s3_payload(True), ("2025-07-01","2026-03-31"), "yi", cap)
print(out)
