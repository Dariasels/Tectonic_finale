import pytest

from engine import TrustEngine


@pytest.fixture(scope="session")
def eng():
    """Read-only engine: tests using it must not change state."""
    return TrustEngine()


@pytest.fixture(scope="session")
def mut():
    """Engine that tests may change (ingest, approvals, votes, profiles)."""
    return TrustEngine()
