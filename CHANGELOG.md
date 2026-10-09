# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-10

### Added
- Synthetic, pseudonymised course-log generator with known ground truth.
- CSV log loader with schema validation.
- Bayesian Knowledge Tracing with vectorised grid-search fitting, per-skill models,
  mastery table and one-step-ahead predictions.
- Engagement features and a transparent dropout-risk score.
- Metrics: ROC AUC, accuracy, fairness gap between groups.
- Plots of mastery trajectories and risk distribution.
- `learner-analytics` command-line interface (`simulate`, `analyze`).
- Test suite (pytest) and GitHub Actions CI/CD pipeline.
