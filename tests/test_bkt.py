import numpy as np
import pytest

from learner_analytics.bkt import (
    BKT,
    BKTParams,
    fit_skills,
    mastery_table,
    next_step_predictions,
    sequences_by_skill,
)
from learner_analytics.metrics import roc_auc


def test_params_validation():
    with pytest.raises(ValueError, match="strictly between"):
        BKTParams(p_init=0.0)
    with pytest.raises(ValueError, match="degenerate"):
        BKTParams(p_guess=0.6, p_slip=0.5)


def test_correct_answer_raises_mastery_and_wrong_lowers_it():
    model = BKT(BKTParams(p_init=0.5, p_learn=0.05, p_guess=0.2, p_slip=0.1))
    assert model.update(0.5, 1) > 0.5
    assert model.update(0.5, 0) < 0.5


def test_trace_stays_in_unit_interval_and_grows_with_success():
    model = BKT()
    trace = model.trace([1] * 10)
    assert np.all((trace > 0) & (trace < 1))
    assert np.all(np.diff(trace) >= 0)
    assert trace[-1] > 0.95


def test_predict_sequence_uses_only_past_answers():
    model = BKT()
    preds = model.predict_sequence([0, 1, 1])
    assert preds[0] == pytest.approx(model.predict_correct(model.params.p_init))
    assert len(preds) == 3


def test_fit_improves_log_likelihood(small_course):
    logs, _ = small_course
    seqs = sequences_by_skill(logs)["skill_1"]
    default_ll = BKT().log_likelihood(seqs)
    fitted = BKT().fit(seqs)
    assert fitted.log_likelihood(seqs) >= default_ll


def test_fit_recovers_parameters_from_known_process():
    rng = np.random.default_rng(0)
    true = BKTParams(p_init=0.2, p_learn=0.2, p_guess=0.15, p_slip=0.05)
    seqs = []
    for _ in range(400):
        known, seq = rng.random() < true.p_init, []
        for _ in range(15):
            seq.append(int(rng.random() < (1 - true.p_slip if known else true.p_guess)))
            known = known or rng.random() < true.p_learn
        seqs.append(np.array(seq, dtype=float))
    est = BKT().fit(seqs).params
    assert est.p_init == pytest.approx(true.p_init, abs=0.1)
    assert est.p_learn == pytest.approx(true.p_learn, abs=0.1)
    assert est.p_guess == pytest.approx(true.p_guess, abs=0.1)
    assert est.p_slip == pytest.approx(true.p_slip, abs=0.05)


def test_fit_requires_data():
    with pytest.raises(ValueError):
        BKT().fit([])


def test_skill_level_helpers(small_course):
    logs, _ = small_course
    models = fit_skills(logs)
    assert set(models) == {"skill_1", "skill_2", "skill_3"}
    table = mastery_table(logs, models)
    assert table.shape[0] == logs["student_id"].nunique()
    values = table.drop(columns="student_id").to_numpy()
    assert np.nanmin(values) > 0 and np.nanmax(values) < 1
    preds = next_step_predictions(logs, models)
    assert len(preds) == len(logs)
    assert roc_auc(preds["correct"], preds["p_correct"]) > 0.7
