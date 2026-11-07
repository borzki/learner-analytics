"""Write index.html for the staging report from summary.json."""

import html
import json
import os
import sys
from pathlib import Path

report = Path(sys.argv[1])
s = json.loads((report / "summary.json").read_text())
fair = s.get("dropout_fairness", {})
rows = [
    ("Package version", s["version"]),
    ("Jenkins build", os.environ.get("APP_BUILD", "dev")),
    ("Git commit", os.environ.get("APP_COMMIT", "unknown")),
    ("Students / answers", f"{s['n_students']} / {s['n_answers']}"),
    ("Next-answer AUC (BKT)", s["bkt_next_answer_auc"]),
    ("Dropout-risk AUC", s.get("dropout_auc", "n/a")),
    ("Fairness gap", fair.get("gap", "n/a")),
    ("Students flagged", s["students_flagged"]),
]
table = "\n".join(
    f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows
)
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>learner-analytics staging report</title>
<style>
body {{ font-family: sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
table {{ border-collapse: collapse; margin-bottom: 1.5rem; }}
th, td {{ border: 1px solid #000; padding: .35rem .8rem; text-align: left; }}
img {{ max-width: 100%; border: 1px solid #ccc; margin-bottom: 1rem; }}
</style></head><body>
<h1>learner-analytics: staging report</h1>
<p>Deployed automatically by the Jenkins CD stage on a simulated course.</p>
<table>{table}</table>
<h2>Mastery trajectories</h2><img src="mastery.png" alt="Mastery plot">
<h2>Dropout-risk distribution</h2><img src="risk.png" alt="Risk plot">
<p>Raw files: <a href="summary.json">summary.json</a>, <a href="mastery.csv">mastery.csv</a>,
<a href="risk.csv">risk.csv</a></p>
</body></html>
"""
(report / "index.html").write_text(page, encoding="utf-8")
print(f"Wrote {report / 'index.html'}")
