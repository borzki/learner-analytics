import pandas as pd
import pytest

from learner_analytics.data import (
    REQUIRED_COLUMNS,
    SimulationConfig,
    load_logs,
    simulate_logs,
    validate_logs,
)


def test_simulation_has_expected_schema(small_course):
    logs, students = small_course
    assert list(logs.columns) == list(REQUIRED_COLUMNS)
    assert set(logs["correct"].unique()) <= {0, 1}
    assert students["student_id"].nunique() == 60
    assert set(students["dropped"].unique()) <= {0, 1}


def test_simulation_is_reproducible():
    cfg = SimulationConfig(n_students=10, n_skills=2, attempts_per_skill=5)
    a, _ = simulate_logs(cfg, seed=7)
    b, _ = simulate_logs(cfg, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_dropped_students_answer_fewer_questions(small_course):
    logs, students = small_course
    counts = logs.groupby("student_id").size().rename("n").reset_index().merge(students)
    means = counts.groupby("dropped")["n"].mean()
    assert means[1] < means[0]


@pytest.mark.parametrize(
    "kwargs",
    [{"n_students": 0}, {"n_skills": 0}, {"attempts_per_skill": 0}, {"dropout_share": 1.5}],
)
def test_simulation_rejects_bad_config(kwargs):
    with pytest.raises(ValueError):
        simulate_logs(SimulationConfig(**kwargs))


def test_validate_sorts_and_parses():
    raw = pd.DataFrame(
        {
            "student_id": ["B", "A", "A"],
            "timestamp": ["2026-09-02", "2026-09-03", "2026-09-01"],
            "skill": ["s", "s", "s"],
            "correct": [1, 0, True],
            "group": ["g", "g", "g"],
        }
    )
    out = validate_logs(raw)
    assert list(out["student_id"]) == ["A", "A", "B"]
    assert pd.api.types.is_datetime64_any_dtype(out["timestamp"])
    assert out["correct"].tolist() == [1, 0, 1]


def test_validate_reports_missing_columns():
    with pytest.raises(ValueError, match="missing required column"):
        validate_logs(pd.DataFrame({"student_id": ["A"]}))


def test_validate_rejects_non_binary_correct():
    df = pd.DataFrame(
        {
            "student_id": ["A"],
            "timestamp": ["2026-09-01"],
            "skill": ["s"],
            "correct": [2],
            "group": ["g"],
        }
    )
    with pytest.raises(ValueError, match="0/1"):
        validate_logs(df)


def test_validate_rejects_empty_and_bad_timestamps():
    empty = pd.DataFrame(columns=list(REQUIRED_COLUMNS))
    with pytest.raises(ValueError, match="no rows"):
        validate_logs(empty)
    bad = pd.DataFrame(
        {
            "student_id": ["A"],
            "timestamp": ["not a date"],
            "skill": ["s"],
            "correct": [1],
            "group": ["g"],
        }
    )
    with pytest.raises(ValueError, match="timestamp"):
        validate_logs(bad)


def test_load_logs_roundtrip(tmp_path, small_course):
    logs, _ = small_course
    path = tmp_path / "logs.csv"
    logs.to_csv(path, index=False)
    pd.testing.assert_frame_equal(load_logs(path), logs)


def test_load_logs_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_logs(tmp_path / "nope.csv")
