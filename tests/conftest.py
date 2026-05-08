import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _zero_simulated_latency():
    os.environ["AI_CAPABILITY_SIMULATED_LATENCY_MS"] = "0"
    yield
