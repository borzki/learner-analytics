"""learner-analytics: knowledge tracing and dropout-risk analytics for course logs."""

from learner_analytics.bkt import BKT, BKTParams
from learner_analytics.data import load_logs, simulate_logs, validate_logs
from learner_analytics.metrics import fairness_gap, roc_auc
from learner_analytics.risk import dropout_risk, engagement_features

__version__ = "0.1.0"

__all__ = [
    "BKT",
    "BKTParams",
    "dropout_risk",
    "engagement_features",
    "fairness_gap",
    "load_logs",
    "roc_auc",
    "simulate_logs",
    "validate_logs",
    "__version__",
]
