"""PRE-RED Task 2.3 mutant①：is_run_status_cacheable 恆 False。"""
from momentum.FeatureEngineering import consumer_gate as cg
cg.is_run_status_cacheable = lambda status: False
