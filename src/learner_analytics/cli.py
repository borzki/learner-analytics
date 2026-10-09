"""Command-line interface: ``learner-analytics simulate`` and ``learner-analytics analyze``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from learner_analytics import __version__
from learner_analytics.bkt import fit_skills, mastery_table, next_step_predictions
from learner_analytics.data import SimulationConfig, load_logs, simulate_logs
from learner_analytics.metrics import fairness_gap, roc_auc
from learner_analytics.risk import dropout_risk, engagement_features
from learner_analytics.viz import plot_mastery, plot_risk


def _simulate(args: argparse.Namespace) -> int:
    cfg = SimulationConfig(
        n_students=args.students,
        n_skills=args.skills,
        attempts_per_skill=args.attempts,
        dropout_share=args.dropout_share,
    )
    logs, students = simulate_logs(cfg, seed=args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    logs.to_csv(out / "logs.csv", index=False)
    students.to_csv(out / "students.csv", index=False)
    print(f"Wrote {len(logs)} log rows for {len(students)} students to {out}/")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    logs = load_logs(args.logs)
    if args.skill:
        logs = logs[logs["skill"].isin(args.skill)]
        if logs.empty:
            print(f"error: none of the skills {args.skill} occur in the log", file=sys.stderr)
            return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    models = fit_skills(logs)
    preds = next_step_predictions(logs, models)
    mastery = mastery_table(logs, models)
    risk = dropout_risk(engagement_features(logs), threshold=args.threshold)

    mastery.to_csv(out / "mastery.csv", index=False)
    risk.to_csv(out / "risk.csv", index=False)
    most_active = str(logs["student_id"].value_counts().idxmax())
    plot_mastery(logs, models, most_active, out / "mastery.png")
    plot_risk(risk, out / "risk.png", threshold=args.threshold)

    summary: dict[str, object] = {
        "version": __version__,
        "n_students": int(logs["student_id"].nunique()),
        "n_answers": len(logs),
        "bkt_params": {s: vars(m.params) for s, m in models.items()},
        "bkt_next_answer_auc": round(roc_auc(preds["correct"], preds["p_correct"]), 4),
        "students_flagged": int(risk["at_risk"].sum()),
    }
    if args.truth:
        truth = pd.read_csv(args.truth)
        merged = risk.merge(truth[["student_id", "dropped"]], on="student_id")
        summary["dropout_auc"] = round(roc_auc(merged["dropped"], merged["risk"]), 4)
        fair = fairness_gap(merged["dropped"], merged["risk"], merged["group"])
        summary["dropout_fairness"] = {
            "auc_by_group": {
                k: None if v is None else round(v, 4) for k, v in fair["auc_by_group"].items()
            },
            "gap": round(fair["gap"], 4),
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learner-analytics",
        description="Knowledge tracing and dropout-risk analytics for course activity logs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="generate a synthetic course log")
    sim.add_argument("--students", type=int, default=200)
    sim.add_argument("--skills", type=int, default=5)
    sim.add_argument("--attempts", type=int, default=12, help="attempts per skill")
    sim.add_argument("--dropout-share", type=float, default=0.25)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--out", default="data", help="output folder")
    sim.set_defaults(func=_simulate)

    ana = sub.add_parser("analyze", help="fit BKT and compute dropout risk for a log")
    ana.add_argument("logs", help="CSV log file")
    ana.add_argument("--out", default="results", help="output folder")
    ana.add_argument("--truth", help="optional CSV with student_id,dropped for evaluation")
    ana.add_argument("--skill", action="append", help="analyse only this skill (repeatable)")
    ana.add_argument("--threshold", type=float, default=0.7, help="risk alert threshold")
    ana.set_defaults(func=_analyze)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
