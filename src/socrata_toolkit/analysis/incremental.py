"""Incremental/online quality model using River (optional)."""
from __future__ import annotations
try:
    from river import tree, metrics as river_metrics
    _RIVER = True
except ImportError:
    _RIVER = False

class IncrementalQualityModel:
    """Online Hoeffding Tree that updates on each scored dataset."""
    def __init__(self):
        if not _RIVER:
            raise ImportError("river is required: pip install river")
        self._model = tree.HoeffdingTreeClassifier()
        self._metric = river_metrics.Accuracy()

    def learn(self, features: dict, label: int) -> None:
        self._model.learn_one(features, label)

    def predict(self, features: dict) -> int:
        return self._model.predict_one(features) or 0

    def accuracy(self) -> float:
        return self._metric.get()
