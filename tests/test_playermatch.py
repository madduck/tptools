from collections.abc import Callable

import pytest

from tptools.playermatchstatus import PlayerMatchStatus
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry, TPPlayerMatch

type TPPlayerMatchFactoryType = Callable[..., TPPlayerMatch]


def test_draw_has_id(pmplayer1: TPPlayerMatch) -> None:
    assert pmplayer1.drawid_


def test_repr(pm1: TPPlayerMatch) -> None:
    assert repr(pm1) == (
        "TPPlayerMatch(id=141, draw.name='Baum', matchnr=14, "
        "entry.players=(TPPlayer(id=1, lastname='Krafft', firstname='Martin', "
        "country.name='Deutschland', club.name='RSC'), None), "
        "time=datetime(2025, 6, 1, 11, 30), court.name='C01', winner=None, "
        "planning=3001, van=4001/2, wnvn=2001/3, status=pending)"
    )


def test_repr_with_court(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpcourt1: TPCourt
) -> None:
    assert repr(TPPlayerMatchFactory(matchnr=12, planning=2002, court=tpcourt1))


def test_repr_with_entry(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpentry1: TPEntry
) -> None:
    assert repr(TPPlayerMatchFactory(matchnr=12, planning=2002, entry=tpentry1))


def test_str(pm1: TPPlayerMatch) -> None:
    assert str(pm1) == (
        "141: [Baum:14] [4001/2 → 3001 → 2001/3] 'Martin Krafft' (pending)"
    )


def test_eq(pm1: TPPlayerMatch, pm1copy: TPPlayerMatch) -> None:
    assert pm1 == pm1copy


def test_ne(pm1: TPPlayerMatch, pm2: TPPlayerMatch) -> None:
    assert pm1 != pm2


def test_lt(pm1: TPPlayerMatch, pm2: TPPlayerMatch) -> None:
    assert pm1 < pm2


def test_le(pm1: TPPlayerMatch, pm2: TPPlayerMatch, pm1copy: TPPlayerMatch) -> None:
    assert pm1 <= pm2 and pm1 <= pm1copy


def test_gt(pm1: TPPlayerMatch, pm2: TPPlayerMatch) -> None:
    assert pm2 > pm1


def test_ge(pm1: TPPlayerMatch, pm2: TPPlayerMatch, pm1copy: TPPlayerMatch) -> None:
    assert pm2 >= pm1 and pm1 >= pm1copy


def test_no_cmp(pm1: TPPlayerMatch) -> None:
    with pytest.raises(NotImplementedError):
        assert pm1 == object()


def test_cmp_time_against_none(pm1: TPPlayerMatch) -> None:
    pm2 = pm1.model_copy(update={"time": None})
    assert pm1 < pm2


def test_default_status_bye(pmbye: TPPlayerMatch) -> None:
    assert pmbye.status == PlayerMatchStatus.BYE


def test_default_status_entry_means_player(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpentry1: TPEntry
) -> None:
    pm = TPPlayerMatchFactory(entry=tpentry1)
    assert pm.status == PlayerMatchStatus.PLAYER


def test_inconsistent_van(pmplayer1: TPPlayerMatch) -> None:
    pmplayer1.van2 = 2001
    with pytest.raises(AssertionError):
        _ = pmplayer1.status


def test_reversehomeaway(pm1: TPPlayerMatch) -> None:
    van1, van2 = pm1.van
    pm1 = pm1.model_copy(update={"reversehomeaway": True})
    assert pm1.van == (van2, van1)


def test_scheduled(pm1: TPPlayerMatch) -> None:
    assert pm1.scheduled


def test_unscheduled(pm2: TPPlayerMatch) -> None:
    assert not pm2.scheduled


@pytest.mark.parametrize(
    "useentry,winner,status",
    [
        (True, None, PlayerMatchStatus.PENDING),
        (False, None, PlayerMatchStatus.PENDING),
        (True, 1, PlayerMatchStatus.PLAYED),
        (False, 1, PlayerMatchStatus.NOTPLAYED),
    ],
)
def test_status_not_group(
    pm1: TPPlayerMatch,
    tpentry1: TPEntry,
    useentry: bool,
    winner: None | int,
    status: PlayerMatchStatus,
) -> None:
    pm1 = pm1.model_copy(
        update={"winner": winner, "entry": tpentry1 if useentry else None}
    )
    assert pm1.status == status


@pytest.mark.parametrize(
    "useentry,wn,vn,winner,status",
    [
        (True, None, None, None, PlayerMatchStatus.PENDING),
        (False, None, None, None, PlayerMatchStatus.PENDING),
        (True, None, None, 1, PlayerMatchStatus.PLAYED),
        (False, None, None, 1, PlayerMatchStatus.PLAYED),
        (False, 0, 0, None, PlayerMatchStatus.NOTPLAYED),
    ],
)
def test_status_group(
    pm1: TPPlayerMatch,
    tpentry1: TPEntry,
    tpdraw2: TPDraw,
    useentry: bool,
    wn: int | None,
    vn: int | None,
    winner: None | int,
    status: PlayerMatchStatus,
) -> None:
    pm1.draw = tpdraw2
    if useentry:
        pm1.entry = tpentry1
    pm1.wn, pm1.vn = wn, vn
    pm1.winner = winner
    assert pm1.status == status


@pytest.mark.xfail
def test_winner0_is_not_played(pm: TPPlayerMatch) -> None:
    # This requires a custom type. There is no validation for model instances that are
    # read from the database, and there is no `__post_init__`. We could map the database
    # column to `winner_` and provide a property that does the `zero_to_none`
    # translation, but that changes the constructor. Not sure how relevant/problematic
    # this actually is. But without any layer to turn 0 into None on the way between
    # assignment and access in the next two lines, this test must fail.
    # Custom types: https://github.com/fastapi/sqlmodel/discussions/1399
    pm.winner = 0
    assert pm.winner is None
    # assert pm.status != PlayerMatchStatus.PLAYED
