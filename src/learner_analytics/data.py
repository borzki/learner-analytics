"""Loading, validating and simulating course activity logs.

The log format mirrors a simplified Moodle quiz-attempt export: one row per
answered question, already pseudonymised (``student_id`` is a code, not a name).

==============  =========  ===================================================
column          type       meaning
==============  =========  ===================================================
student_id      str        pseudonymised student code, e.g. ``S0042``
timestamp       datetime   when the answer was submitted
skill           str        competency the question belongs to
correct         int (0/1)  whether the answer was correct
group           str        demographic group, used only for fairness checks
==============  =========  ===================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = ("student_id", "timestamp", "skill", "correct", "group")


def validate_logs(df: pd.DataFrame) -> pd.DataFrame:
    """Check that ``df`` follows the log schema and return a cleaned copy.

    The returned frame has parsed timestamps, integer ``correct`` values and is
    sorted by student and time, which every downstream function relies on.

    Raises
    ------
    ValueError
        If columns are missing, values in ``correct`` are not 0/1, timestamps
        cannot be parsed or the frame is empty.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"log is missing required column(s): {', '.join(missing)}")
    if df.empty:
        raise ValueError("log contains no rows")

    out = df.loc[:, list(REQUIRED_COLUMNS)].copy()
    try:
        out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.as_unit("ns")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"cannot parse 'timestamp' column: {exc}") from exc

    if not out["correct"].isin([0, 1, True, False]).all():
        raise ValueError("'correct' must contain only 0/1 values")
    out["correct"] = out["correct"].astype(int)
    out["student_id"] = out["student_id"].astype(str)
    out["skill"] = out["skill"].astype(str)
    out["group"] = out["group"].astype(str)
    return out.sort_values(["student_id", "timestamp"], kind="stable").reset_index(drop=True)


def load_logs(path: str | Path) -> pd.DataFrame:
    """Read a CSV activity log and validate it with :func:`validate_logs`."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"log file not found: {path}")
    return validate_logs(pd.read_csv(path))


@dataclass(frozen=True)
class SimulationConfig:
    """Parameters of the synthetic data generator."""

    n_students: int = 200
    n_skills: int = 5
    attempts_per_skill: int = 12
    dropout_share: float = 0.25
    course_days: int = 56
    start: str = "2026-09-01"


def simulate_logs(
    config: SimulationConfig | None = None,
    seed: int | None = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate a synthetic course log with a known ground truth.

    Each skill follows a Bayesian Knowledge Tracing process with its own
    parameters. A share of students (``dropout_share``) disengages: they study
    less often and stop partway through the course. Nothing personal is
    generated, so the data can be shared and committed freely.

    Returns
    -------
    logs : DataFrame
        Activity log in the schema described in the module docstring.
    students : DataFrame
        Ground truth per student: ``student_id``, ``group`` and ``dropped``.
    """
    cfg = config or SimulationConfig()
    if cfg.n_students < 1 or cfg.n_skills < 1 or cfg.attempts_per_skill < 1:
        raise ValueError("n_students, n_skills and attempts_per_skill must be positive")
    if not 0.0 <= cfg.dropout_share <= 1.0:
        raise ValueError("dropout_share must be between 0 and 1")

    rng = np.random.default_rng(seed)
    skills = [f"skill_{k + 1}" for k in range(cfg.n_skills)]
    skill_params = {
        s: (
            rng.uniform(0.1, 0.4),  # p_init
            rng.uniform(0.08, 0.25),  # p_learn
            rng.uniform(0.1, 0.25),  # p_guess
            rng.uniform(0.05, 0.15),  # p_slip
        )
        for s in skills
    }
    start = pd.Timestamp(cfg.start)
    total_attempts = cfg.n_skills * cfg.attempts_per_skill

    rows: list[tuple[str, pd.Timestamp, str, int, str]] = []
    truth: list[tuple[str, str, int]] = []
    for i in range(cfg.n_students):
        sid = f"S{i + 1:04d}"
        group = "urban" if rng.random() < 0.6 else "rural"
        dropped = bool(rng.random() < cfg.dropout_share)
        # Every student works through the skills in order. Disengaged students go
        # silent partway through the course; engaged ones stay active to the end.
        end_frac = rng.uniform(0.25, 0.95) if dropped else rng.uniform(0.7, 1.0)
        diligence = rng.uniform(0.5, 1.0) if dropped else rng.uniform(0.7, 1.0)
        n_done = max(1, round(total_attempts * end_frac * diligence))
        days = np.sort(rng.uniform(0.0, end_frac * cfg.course_days, size=n_done))
        truth.append((sid, group, int(dropped)))

        known = {s: rng.random() < skill_params[s][0] for s in skills}
        order = np.repeat(skills, cfg.attempts_per_skill)
        for skill, day in zip(order[:n_done], days, strict=True):
            _, p_learn, p_guess, p_slip = skill_params[skill]
            p_correct = 1 - p_slip if known[skill] else p_guess
            correct = int(rng.random() < p_correct)
            stamp = (start + pd.Timedelta(days=float(day))).floor("s")
            rows.append((sid, stamp, skill, correct, group))
            if not known[skill] and rng.random() < p_learn:
                known[skill] = True

    logs = pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))
    students = pd.DataFrame(truth, columns=["student_id", "group", "dropped"])
    return validate_logs(logs), students
