# Multi-stage image for learner-analytics.
#   test    : package + dev tools + tests  -> used by CI to run ruff and pytest
#   build   : builds the wheel
#   runtime : small image with only the installed package (what gets deployed)
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg
WORKDIR /app

# ---------- test stage ----------
FROM base AS test
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install -e ".[dev]"
COPY tests ./tests
RUN mkdir -p reports
CMD ["pytest", "--junitxml=reports/junit.xml", "--cov=learner_analytics", \
     "--cov-report=term", "--cov-report=xml:reports/coverage.xml", "--cov-fail-under=90"]

# ---------- build stage ----------
FROM base AS build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip wheel --no-deps --wheel-dir /wheels .

# ---------- runtime stage ----------
FROM base AS runtime
ARG BUILD_NUMBER=dev
ARG GIT_COMMIT=unknown
LABEL org.opencontainers.image.title="learner-analytics" \
      org.opencontainers.image.description="Knowledge tracing and dropout-risk analytics for course logs" \
      org.opencontainers.image.source="https://github.com/borzki/learner-analytics" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${GIT_COMMIT}"
COPY --from=build /wheels /wheels
COPY deploy/serve_report.sh /usr/local/bin/serve-report
COPY deploy/make_index.py /usr/local/share/learner-analytics/make_index.py
RUN pip install /wheels/*.whl && rm -rf /wheels \
    && chmod 755 /usr/local/bin/serve-report \
    && useradd --create-home --uid 1000 analyst
ENV APP_BUILD=${BUILD_NUMBER} APP_COMMIT=${GIT_COMMIT}
USER analyst
WORKDIR /home/analyst
ENTRYPOINT ["learner-analytics"]
CMD ["--help"]
