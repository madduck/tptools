import pytest

from tptools.matchstatus import MatchStatus
from tptools.playermatchstatus import PlayerMatchStatus as PMS


@pytest.mark.parametrize("pmstatus", [s for s in PMS if s.is_player])
def test_player_invalid(pmstatus: PMS) -> None:
    with pytest.raises(ValueError, match="that are not players or byes"):
        _ = MatchStatus.from_playermatch_status_pair(pmstatus, pmstatus)


@pytest.mark.parametrize("pmstatus", [s for s in PMS if s.is_match])
def test_equal_status(pmstatus: PMS) -> None:
    assert MatchStatus.from_playermatch_status_pair(pmstatus, pmstatus) == MatchStatus(
        pmstatus
    )


@pytest.mark.parametrize(
    "stat1,stat2,exp",
    [
        (PMS.PLAYED, PMS.PENDING, MatchStatus.PENDING),
        (PMS.PLAYED, PMS.PLAYED, MatchStatus.PLAYED),
        (PMS.PLAYED, PMS.NOTPLAYED, MatchStatus.NOTPLAYED),
        (PMS.PENDING, PMS.PENDING, MatchStatus.PENDING),
        (PMS.PENDING, PMS.PLAYED, MatchStatus.PENDING),
        (PMS.PENDING, PMS.NOTPLAYED, MatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.PENDING, MatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.PLAYED, MatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.NOTPLAYED, MatchStatus.NOTPLAYED),
    ],
)
def test_status_combinations(stat1: PMS, stat2: PMS, exp: MatchStatus) -> None:
    assert MatchStatus.from_playermatch_status_pair(stat1, stat2) == exp
