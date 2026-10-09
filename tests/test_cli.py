import json

import pytest

from learner_analytics import __version__
from learner_analytics.cli import main


def test_simulate_then_analyze(tmp_path, capsys):
    data = tmp_path / "data"
    assert main(["simulate", "--students", "40", "--skills", "2", "--out", str(data)]) == 0
    assert (data / "logs.csv").exists() and (data / "students.csv").exists()

    out = tmp_path / "results"
    code = main(
        [
            "analyze",
            str(data / "logs.csv"),
            "--truth",
            str(data / "students.csv"),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    for name in ("mastery.csv", "risk.csv", "mastery.png", "risk.png", "summary.json"):
        assert (out / name).exists(), name
    summary = json.loads((out / "summary.json").read_text())
    assert summary["n_students"] == 40
    assert 0.5 < summary["bkt_next_answer_auc"] <= 1.0
    assert "dropout_fairness" in summary


def test_analyze_single_skill(tmp_path):
    data = tmp_path / "data"
    main(["simulate", "--students", "20", "--skills", "3", "--out", str(data)])
    out = tmp_path / "res"
    assert main(["analyze", str(data / "logs.csv"), "--skill", "skill_2", "--out", str(out)]) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert list(summary["bkt_params"]) == ["skill_2"]


def test_analyze_unknown_skill_fails(tmp_path, capsys):
    data = tmp_path / "data"
    main(["simulate", "--students", "10", "--skills", "1", "--out", str(data)])
    assert main(["analyze", str(data / "logs.csv"), "--skill", "nope", "--out", str(tmp_path)]) == 2
    assert "none of the skills" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
