"""Plots for mastery trajectories and dropout risk."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: works on servers and in CI
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from learner_analytics.bkt import BKT  # noqa: E402


def plot_mastery(
    logs: pd.DataFrame, models: dict[str, BKT], student_id: str, path: str | Path
) -> Path:
    """Plot how a student's estimated mastery of each skill changes with practice."""
    data = logs[logs["student_id"] == student_id]
    if data.empty:
        raise ValueError(f"student {student_id!r} not found in log")
    fig, ax = plt.subplots(figsize=(7, 4))
    for skill, grp in data.groupby("skill", sort=True):
        trace = models[str(skill)].trace(grp["correct"].to_numpy())
        ax.plot(range(1, len(trace) + 1), trace, marker="o", ms=3, lw=1.5, label=str(skill))
    ax.axhline(0.95, color="grey", ls="--", lw=1)
    ax.text(0.5, 0.955, "mastery threshold (0.95)", fontsize=8, color="grey", va="bottom")
    ax.set(xlabel="Practice opportunity", ylabel="P(skill known)", ylim=(0, 1.05))
    ax.set_title(f"Estimated mastery - student {student_id}")
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, path)


def plot_risk(risk: pd.DataFrame, path: str | Path, threshold: float = 0.7) -> Path:
    """Histogram of dropout-risk scores with the alert threshold marked."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(risk["risk"], bins=20, range=(0, 1), color="#2a78d6", edgecolor="white")
    ax.axvline(threshold, color="#e34948", lw=1.5)
    n_flag = int(risk["at_risk"].sum())
    ax.text(threshold + 0.01, ax.get_ylim()[1] * 0.92, f"{n_flag} students flagged", fontsize=9)
    ax.set(xlabel="Dropout-risk score", ylabel="Number of students")
    ax.set_title("Distribution of dropout-risk scores")
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, path)


def _save(fig: plt.Figure, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
