import pytest

from tptools.playermatchstatus import PlayerMatchStatus as PMS
from tptools.tpmatch import TPMatchStatus


@pytest.mark.parametrize("pmstatus", [s for s in PMS if s.is_player])
def test_player_invalid(pmstatus: PMS) -> None:
    with pytest.raises(ValueError, match="that are not players or byes"):
        _ = TPMatchStatus.from_playermatch_status_pair(pmstatus, pmstatus)


@pytest.mark.parametrize("pmstatus", [s for s in PMS if s.is_match])
def test_equal_status(pmstatus: PMS) -> None:
    assert TPMatchStatus.from_playermatch_status_pair(
        pmstatus, pmstatus
    ) == TPMatchStatus(pmstatus)


@pytest.mark.parametrize(
    "stat1,stat2,exp",
    [
        (PMS.PLAYED, PMS.PENDING, TPMatchStatus.PENDING),
        (PMS.PLAYED, PMS.PLAYED, TPMatchStatus.PLAYED),
        (PMS.PLAYED, PMS.NOTPLAYED, TPMatchStatus.NOTPLAYED),
        (PMS.PENDING, PMS.PENDING, TPMatchStatus.PENDING),
        (PMS.PENDING, PMS.PLAYED, TPMatchStatus.PENDING),
        (PMS.PENDING, PMS.NOTPLAYED, TPMatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.PENDING, TPMatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.PLAYED, TPMatchStatus.NOTPLAYED),
        (PMS.NOTPLAYED, PMS.NOTPLAYED, TPMatchStatus.NOTPLAYED),
    ],
)
def test_status_combinations(stat1: PMS, stat2: PMS, exp: TPMatchStatus) -> None:
    assert TPMatchStatus.from_playermatch_status_pair(stat1, stat2) == exp
