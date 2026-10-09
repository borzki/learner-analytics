"""Evaluation metrics: ROC AUC, accuracy and a group fairness gap."""

from __future__ import annotations

import numpy as np
import pandas as pd


def roc_auc(y_true: np.ndarray | list, y_score: np.ndarray | list) -> float:
    """Area under the ROC curve via the Mann-Whitney U statistic (ties count 0.5).

    Raises
    ------
    ValueError
        If the inputs differ in length or ``y_true`` contains only one class.
    """
    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=float)
    if y.shape != s.shape:
        raise ValueError("y_true and y_score must have the same length")
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        raise ValueError("AUC is undefined when only one class is present")
    ranks = pd.Series(s).rank(method="average").to_numpy()
    u = ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2
    return float(u / (n_pos * n_neg))


def accuracy(
    y_true: np.ndarray | list, y_score: np.ndarray | list, threshold: float = 0.5
) -> float:
    """Share of correct binary predictions after thresholding ``y_score``."""
    y = np.asarray(y_true).astype(int)
    pred = (np.asarray(y_score, dtype=float) >= threshold).astype(int)
    return float((y == pred).mean())


def fairness_gap(
    y_true: np.ndarray | list, y_score: np.ndarray | list, groups: np.ndarray | list
) -> dict[str, object]:
    """AUC per group and the largest difference between any two groups.

    Groups where AUC is undefined (a single class) are reported as ``None``
    and ignored when computing the gap.
    """
    y = np.asarray(y_true)
    s = np.asarray(y_score, dtype=float)
    g = np.asarray(groups).astype(str)
    per_group: dict[str, float | None] = {}
    for name in sorted(set(g)):
        mask = g == name
        try:
            per_group[name] = roc_auc(y[mask], s[mask])
        except ValueError:
            per_group[name] = None
    values = [v for v in per_group.values() if v is not None]
    gap = float(max(values) - min(values)) if len(values) >= 2 else 0.0
    return {"auc_by_group": per_group, "gap": gap}
