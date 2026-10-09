import pytest

from learner_analytics.data import SimulationConfig, simulate_logs


@pytest.fixture(scope="session")
def small_course():
    """A small, deterministic synthetic course shared by several tests."""
    return simulate_logs(
        SimulationConfig(n_students=60, n_skills=3, attempts_per_skill=10), seed=42
    )
