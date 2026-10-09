"""Bayesian Knowledge Tracing (Corbett & Anderson, 1994).

BKT models each skill as a hidden binary state (known / not known) that a
student can move into after every practice opportunity. Four parameters
describe a skill:

* ``p_init``  - probability the skill is known before the first attempt;
* ``p_learn`` - probability of learning it after an attempt;
* ``p_guess`` - probability of a correct answer without knowing the skill;
* ``p_slip``  - probability of a wrong answer despite knowing it.

Parameters are fitted by maximising the log-likelihood over a grid. The
forward pass is vectorised over students *and* candidate parameter sets, so a
full grid search over ~2,000 candidates takes well under a second for a
typical course.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

_EPS = 1e-9

DEFAULT_GRID: dict[str, tuple[float, ...]] = {
    "p_init": (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
    "p_learn": (0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4),
    "p_guess": (0.05, 0.1, 0.15, 0.2, 0.25, 0.3),
    "p_slip": (0.02, 0.05, 0.1, 0.15, 0.2),
}


@dataclass(frozen=True)
class BKTParams:
    """The four BKT parameters of one skill."""

    p_init: float = 0.3
    p_learn: float = 0.1
    p_guess: float = 0.2
    p_slip: float = 0.1

    def __post_init__(self) -> None:
        for name in ("p_init", "p_learn", "p_guess", "p_slip"):
            value = getattr(self, name)
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be strictly between 0 and 1, got {value}")
        if self.p_guess + self.p_slip >= 1.0:
            raise ValueError("p_guess + p_slip must be below 1 (otherwise the model is degenerate)")

    def as_array(self) -> np.ndarray:
        return np.array([self.p_init, self.p_learn, self.p_guess, self.p_slip])


def _pad(sequences: list[np.ndarray]) -> np.ndarray:
    """Stack variable-length 0/1 sequences into a (n_seq, max_len) array padded with NaN."""
    if not sequences:
        raise ValueError("at least one response sequence is required")
    max_len = max(len(s) for s in sequences)
    out = np.full((len(sequences), max_len), np.nan)
    for i, seq in enumerate(sequences):
        out[i, : len(seq)] = seq
    return out


def _forward_loglik(responses: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Log-likelihood of padded ``responses`` (S, T) for each parameter row in ``params`` (G, 4)."""
    p_init, p_learn, p_guess, p_slip = (params[:, k : k + 1] for k in range(4))
    p_known = np.repeat(p_init, responses.shape[0], axis=1)  # (G, S)
    loglik = np.zeros(params.shape[0])
    for t in range(responses.shape[1]):
        obs = responses[:, t]
        mask = ~np.isnan(obs)
        if not mask.any():
            continue
        correct = obs == 1
        p_correct = p_known * (1 - p_slip) + (1 - p_known) * p_guess
        likelihood = np.where(correct, p_correct, 1 - p_correct)
        loglik += np.where(mask, np.log(np.clip(likelihood, _EPS, 1.0)), 0.0).sum(axis=1)
        posterior = np.where(
            correct,
            p_known * (1 - p_slip) / np.clip(p_correct, _EPS, None),
            p_known * p_slip / np.clip(1 - p_correct, _EPS, None),
        )
        updated = posterior + (1 - posterior) * p_learn
        p_known = np.where(mask, updated, p_known)
    return loglik


class BKT:
    """Bayesian Knowledge Tracing model for a single skill.

    Examples
    --------
    >>> model = BKT(BKTParams(p_init=0.2, p_learn=0.15, p_guess=0.2, p_slip=0.1))
    >>> mastery = model.trace([0, 1, 1, 1])
    >>> bool(mastery[-1] > mastery[0])
    True
    """

    def __init__(self, params: BKTParams | None = None) -> None:
        self.params = params or BKTParams()

    # -- inference ---------------------------------------------------------
    def predict_correct(self, p_known: float) -> float:
        """Probability of a correct answer given the current mastery estimate."""
        p = self.params
        return p_known * (1 - p.p_slip) + (1 - p_known) * p.p_guess

    def update(self, p_known: float, correct: int) -> float:
        """Mastery after observing one answer (Bayesian update, then learning step)."""
        p = self.params
        p_correct = self.predict_correct(p_known)
        if correct:
            posterior = p_known * (1 - p.p_slip) / max(p_correct, _EPS)
        else:
            posterior = p_known * p.p_slip / max(1 - p_correct, _EPS)
        return posterior + (1 - posterior) * p.p_learn

    def trace(self, responses: list[int] | np.ndarray) -> np.ndarray:
        """Mastery estimate *after* each answer in ``responses``."""
        p_known = self.params.p_init
        out = np.empty(len(responses))
        for i, r in enumerate(responses):
            p_known = self.update(p_known, int(r))
            out[i] = p_known
        return out

    def predict_sequence(self, responses: list[int] | np.ndarray) -> np.ndarray:
        """Predicted probability of a correct answer *before* each attempt.

        These one-step-ahead predictions are what AUC is computed on, because
        each prediction uses only answers given earlier.
        """
        p_known = self.params.p_init
        out = np.empty(len(responses))
        for i, r in enumerate(responses):
            out[i] = self.predict_correct(p_known)
            p_known = self.update(p_known, int(r))
        return out

    # -- learning ----------------------------------------------------------
    def log_likelihood(self, sequences: list[np.ndarray]) -> float:
        """Total log-likelihood of the response sequences under current parameters."""
        return float(_forward_loglik(_pad(sequences), self.params.as_array()[None, :])[0])

    def fit(
        self,
        sequences: list[np.ndarray],
        grid: dict[str, tuple[float, ...]] | None = None,
    ) -> BKT:
        """Choose the parameter set on ``grid`` with the highest log-likelihood."""
        grid = grid or DEFAULT_GRID
        candidates = np.array(
            [
                c
                for c in product(grid["p_init"], grid["p_learn"], grid["p_guess"], grid["p_slip"])
                if c[2] + c[3] < 1.0
            ]
        )
        loglik = _forward_loglik(_pad(sequences), candidates)
        best = candidates[int(np.argmax(loglik))]
        self.params = BKTParams(*(float(v) for v in best))
        return self


def sequences_by_skill(logs: pd.DataFrame) -> dict[str, list[np.ndarray]]:
    """Group a validated log into 0/1 answer sequences per skill and student."""
    out: dict[str, list[np.ndarray]] = {}
    for (skill, _), grp in logs.groupby(["skill", "student_id"], sort=True):
        out.setdefault(str(skill), []).append(grp["correct"].to_numpy(dtype=float))
    return out


def fit_skills(logs: pd.DataFrame) -> dict[str, BKT]:
    """Fit one BKT model per skill in ``logs``."""
    return {skill: BKT().fit(seqs) for skill, seqs in sequences_by_skill(logs).items()}


def mastery_table(logs: pd.DataFrame, models: dict[str, BKT]) -> pd.DataFrame:
    """Final mastery estimate per student and skill (wide table, one row per student)."""
    records = []
    for (sid, skill), grp in logs.groupby(["student_id", "skill"], sort=True):
        trace = models[str(skill)].trace(grp["correct"].to_numpy())
        records.append((sid, skill, float(trace[-1])))
    long = pd.DataFrame(records, columns=["student_id", "skill", "mastery"])
    return long.pivot(index="student_id", columns="skill", values="mastery").reset_index()


def next_step_predictions(logs: pd.DataFrame, models: dict[str, BKT]) -> pd.DataFrame:
    """One-step-ahead correctness predictions for every row of ``logs``."""
    parts = []
    for (_, skill), grp in logs.groupby(["student_id", "skill"], sort=False):
        pred = models[str(skill)].predict_sequence(grp["correct"].to_numpy())
        parts.append(grp.assign(p_correct=pred))
    return pd.concat(parts).sort_index()
