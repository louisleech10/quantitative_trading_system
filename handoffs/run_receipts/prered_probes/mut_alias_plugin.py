"""PRE-RED Task 2.1 mutant 外掛：set_batch_alias 刪除 deleting 檢查（以 -p 載入，只影響該次 pytest）。"""

from momentum.FeatureEngineering import feature_registry as fr


def _mutant_set_batch_alias(self, batch_id, batch_alias):
    normalized = batch_alias.strip() if batch_alias is not None else ""
    affected = 0

    def mutate():
        nonlocal affected
        targets = [i for i in self._entries if str(i.get("batch_id") or "") == batch_id]
        if not targets:
            raise KeyError(batch_id)
        for t in targets:  # mutant：不檢查 deleting
            if normalized:
                t["batch_alias"] = normalized
            else:
                t.pop("batch_alias", None)
            affected += 1

    self._require_healthy()
    self._locked_mutate(mutate)
    return affected


fr.FeatureRegistry.set_batch_alias = _mutant_set_batch_alias
