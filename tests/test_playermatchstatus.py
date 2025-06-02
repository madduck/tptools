import pytest

from tptools.playermatchstatus import PlayerMatchStatus


@pytest.mark.parametrize("pmstatus", [PlayerMatchStatus.BYE, PlayerMatchStatus.PLAYER])
def test_player(pmstatus: PlayerMatchStatus) -> None:
    assert pmstatus.is_player


@pytest.mark.parametrize(
    "pmstatus",
    [
        PlayerMatchStatus.PENDING,
        PlayerMatchStatus.READY,
        PlayerMatchStatus.PLAYED,
        PlayerMatchStatus.NOTPLAYED,
    ],
)
def test_match(pmstatus: PlayerMatchStatus) -> None:
    assert pmstatus.is_match
