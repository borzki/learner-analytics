import numpy as np
import pandas as pd
import pytest

from learner_analytics.metrics import accuracy, fairness_gap, roc_auc
from learner_analytics.risk import dropout_risk, engagement_features


def test_roc_auc_known_values():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0
    assert roc_auc([0, 1], [0.5, 0.5]) == 0.5
    assert roc_auc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == pytest.approx(0.75)


def test_roc_auc_input_errors():
    with pytest.raises(ValueError, match="one class"):
        roc_auc([1, 1], [0.2, 0.3])
    with pytest.raises(ValueError, match="same length"):
        roc_auc([0, 1], [0.2])


def test_accuracy():
    assert accuracy([0, 1, 1, 0], [0.2, 0.9, 0.4, 0.6]) == 0.5


def test_fairness_gap_reports_groups_and_gap():
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1])
    s = np.array([0.1, 0.9, 0.2, 0.8, 0.6, 0.4, 0.5, 0.7])
    g = np.array(["a", "a", "a", "a", "b", "b", "b", "b"])
    res = fairness_gap(y, s, g)
    assert res["auc_by_group"]["a"] == 1.0
    assert res["auc_by_group"]["b"] == 0.5
    assert res["gap"] == 0.5


def test_fairness_gap_skips_single_class_groups():
    res = fairness_gap([0, 1, 1], [0.1, 0.9, 0.5], ["a", "a", "b"])
    assert res["auc_by_group"]["b"] is None
    assert res["gap"] == 0.0


def test_engagement_features(small_course):
    logs, _ = small_course
    feats = engagement_features(logs)
    assert feats.shape[0] == logs["student_id"].nunique()
    assert {"n_attempts", "active_days", "accuracy", "days_since_last", "group"} <= set(feats)
    assert (feats["days_since_last"] >= 0).all()
    assert feats["accuracy"].between(0, 1).all()


def test_dropout_risk_separates_dropouts(small_course):
    logs, students = small_course
    risk = dropout_risk(engagement_features(logs)).merge(students[["student_id", "dropped"]])
    assert risk["risk"].between(0, 1).all()
    assert roc_auc(risk["dropped"], risk["risk"]) > 0.75


def test_dropout_risk_validation():
    feats = pd.DataFrame({"n_attempts": [1, 2]})
    with pytest.raises(ValueError, match="missing"):
        dropout_risk(feats)
    full = pd.DataFrame(
        {
            "days_since_last": [1, 1],
            "active_days": [2, 2],
            "n_attempts": [3, 3],
            "accuracy": [0.5, 0.5],
        }
    )
    with pytest.raises(ValueError, match="threshold"):
        dropout_risk(full, threshold=1.5)
    assert dropout_risk(full)["risk"].tolist() == [0.5, 0.5]  # constant features -> neutral score
