"""PRE-RED Task 2.3 mutant②：_has_resume_checkpoint_for_timeframe 恆 False。"""
from momentum.FeatureEngineering.timeframe import multi_tf_generator as m
m.MultiTFGenerator._has_resume_checkpoint_for_timeframe = staticmethod(lambda *a, **k: False)
