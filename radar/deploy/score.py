"""Azure entry point: reuse the tested model loader and scoring implementation.

prepare.py stages the required ml/data packages beside this file. This wrapper
adds no alternative feature mapping, threshold, consent filter or business logic.
"""
from ml.azureml.score import init, run
