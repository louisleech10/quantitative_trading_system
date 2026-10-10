#!/bin/zsh
# PRE-RED Task 2.8 mutant：閘門解析恆回 None（＝不擋）⇒ 四支注入型測試須紅。於隔離 worktree 改壞，不動主樹。
# 用法：zsh <本檔> <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
WT=$S/wt_stopgate_mut
git -C $REPO worktree add -f --detach $WT HEAD > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
cp $REPO/tests/api/test_gap3_ic_stop_gate.py $WT/tests/api/test_gap3_ic_stop_gate.py
mkdir -p $WT/data_cache/feature_klines
ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
cp -R $REPO/data_cache/features $WT/data_cache/features
ln -s $REPO/venv $WT/venv
NODES=(test_gap3_ic_feature_cap_covers_implicit_latest_longitudinal test_gap3_ic_feature_cap_covers_implicit_latest_cross_sectional
       test_gap3_ic_feature_cap_cross_run_empty_hash_means_latest test_gap3_matrix_duplicate_symbol_last_is_big_must_block)
ARGS=(); for n in $NODES; do ARGS+=("tests/api/test_gap3_ic_stop_gate.py::$n"); done
(cd $WT && venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=no $ARGS > $S/stopgate_clean.log 2>&1)
echo "clean: $(tail -1 $S/stopgate_clean.log | tr -d '=')"
F=$WT/api/services/ic_analysis_service.py
perl -0pi -e 's/(def resolve_planned_feature_count\([^)]*\)[^:]*:\n)/$1        return None  # MUTANT\n/' $F
grep -c "return None  # MUTANT" $F
(cd $WT && venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=no $ARGS > $S/stopgate_mut.log 2>&1)
echo "mutant: $(tail -1 $S/stopgate_mut.log | tr -d '=')"
git -C $REPO worktree remove --force $WT > /dev/null 2>&1
