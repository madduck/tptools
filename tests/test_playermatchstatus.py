import pytest

from tptools.sqlmodels import TPPlayerMatch


@pytest.mark.parametrize(
    "pmstatus", [TPPlayerMatch.Status.BYE, TPPlayerMatch.Status.PLAYER]
)
def test_player(pmstatus: TPPlayerMatch.Status) -> None:
    assert pmstatus.is_player


@pytest.mark.parametrize(
    "pmstatus",
    [
        TPPlayerMatch.Status.PENDING,
        TPPlayerMatch.Status.PLAYED,
        TPPlayerMatch.Status.NOTPLAYED,
    ],
)
def test_match(pmstatus: TPPlayerMatch.Status) -> None:
    assert pmstatus.is_match
