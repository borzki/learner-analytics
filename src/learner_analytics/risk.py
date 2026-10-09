"""Engagement features and a transparent dropout-risk score.

The score is a deliberately simple, explainable baseline: a logistic function
of standardised engagement features with fixed, documented weights. It is meant
to flag students for a teacher to look at, not to make automatic decisions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Weight of each standardised feature in the risk score (positive = riskier).
DEFAULT_WEIGHTS: dict[str, float] = {
    "days_since_last": 1.5,
    "active_days": -1.0,
    "n_attempts": -0.8,
    "accuracy": -0.6,
}


def engagement_features(
    logs: pd.DataFrame, reference_time: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Compute per-student engagement features from a validated log.

    Parameters
    ----------
    logs
        Output of :func:`learner_analytics.data.validate_logs`.
    reference_time
        "Now" for ``days_since_last``; defaults to the latest timestamp in the log.

    Returns
    -------
    DataFrame with one row per student and columns ``n_attempts``,
    ``active_days``, ``accuracy``, ``days_since_last`` and ``group``.
    """
    ref = pd.Timestamp(reference_time) if reference_time is not None else logs["timestamp"].max()
    grouped = logs.groupby("student_id", sort=True)
    features = pd.DataFrame(
        {
            "n_attempts": grouped.size(),
            "active_days": grouped["timestamp"].agg(lambda t: t.dt.normalize().nunique()),
            "accuracy": grouped["correct"].mean(),
            "days_since_last": grouped["timestamp"].max().rsub(ref).dt.total_seconds() / 86400,
            "group": grouped["group"].first(),
        }
    )
    return features.reset_index()


def dropout_risk(
    features: pd.DataFrame,
    weights: dict[str, float] | None = None,
    threshold: float = 0.7,
) -> pd.DataFrame:
    """Add ``risk`` (0-1) and ``at_risk`` (bool) columns to ``features``.

    Each feature is standardised (z-score) across students, multiplied by its
    weight, summed and passed through a logistic function.
    """
    weights = weights or DEFAULT_WEIGHTS
    missing = [k for k in weights if k not in features.columns]
    if missing:
        raise ValueError(f"features are missing column(s): {', '.join(missing)}")
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be between 0 and 1")

    linear = np.zeros(len(features))
    for name, weight in weights.items():
        col = features[name].astype(float)
        std = col.std(ddof=0)
        z = (col - col.mean()) / std if std > 0 else col * 0.0
        linear += weight * z.to_numpy()
    out = features.copy()
    out["risk"] = 1.0 / (1.0 + np.exp(-linear))
    out["at_risk"] = out["risk"] >= threshold
    return out
