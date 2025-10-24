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


def test_only_show_event(policy: DrawNamePolicy, draw1: Draw) -> None:
    dnp = policy.with_(only_show_event=True)
    assert dnp(draw1) == "Herren 1"
