import pytest

from engine import TrustEngine


@pytest.fixture(scope="session")
def eng():
    """Read-only engine: tests using it must not change state."""
    return TrustEngine()


@pytest.fixture(scope="session")
def mut():
    """Engine that tests may change (ingest, approvals, votes, profiles)."""
    e = TrustEngine()
    e.policy["auto_cleanup"] = False          # these tests keep their documents; the clean-up has its own engine
    return e


@pytest.fixture(scope="session")
def clean():
    """Engine for the clean-up tests, which remove documents."""
    e = TrustEngine()
    e.policy["auto_cleanup"] = False
    return e
