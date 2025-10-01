import pytest

from tptools.draw import Draw
from tptools.namepolicy import DrawNamePolicy


@pytest.fixture
def policy() -> DrawNamePolicy:
    return DrawNamePolicy()


def test_constructor(policy: DrawNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: DrawNamePolicy, draw1: Draw) -> None:
    assert policy(draw1) == "Baum, Qual, Herren 1"


def test_no_draw(policy: DrawNamePolicy) -> None:
    _ = policy(None)
