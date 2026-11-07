#!/bin/sh
# Staging deployment of learner-analytics:
# simulate a course, analyse it and serve the resulting report over HTTP.
set -eu

PORT="${PORT:-8000}"
STUDENTS="${STUDENTS:-200}"
SEED="${SEED:-0}"
WORK="${WORK_DIR:-/tmp/learner-analytics}"

learner-analytics simulate --students "$STUDENTS" --seed "$SEED" --out "$WORK/data"
learner-analytics analyze "$WORK/data/logs.csv" --truth "$WORK/data/students.csv" \
    --out "$WORK/report" > /dev/null
python /usr/local/share/learner-analytics/make_index.py "$WORK/report"

echo "Serving report on port $PORT"
exec python -m http.server "$PORT" --directory "$WORK/report"
