from collections.abc import Callable

import pytest

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
    assert pmbye.status == TPPlayerMatch.Status.BYE


def test_default_status_entry_means_player(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpentry1: TPEntry
) -> None:
    pm = TPPlayerMatchFactory(entry=tpentry1)
    assert pm.status == TPPlayerMatch.Status.PLAYER


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
    "useentry,winner,scorestatus,status",
    [
        # no winner, scorestatus @ 0, so pending
        (True, None, 0, TPPlayerMatch.Status.PENDING),
        (False, None, 0, TPPlayerMatch.Status.PENDING),
        (True, None, None, TPPlayerMatch.Status.PENDING),
        (False, None, None, TPPlayerMatch.Status.PENDING),
        # yes winner, scorestatus @ 0, so played
        (True, 1, 0, TPPlayerMatch.Status.PLAYED),
        (True, 1, None, TPPlayerMatch.Status.PLAYED),
        # yes winner, scorestatus @ 0, but no entry, so not played
        # TODO: is this actually a useful indication? Needs a special case for group
        # draws if we think that a missing entry field with a winner != 0 means
        # notplayed. Shouldn't we just use scorestatus instead?
        (False, 1, 0, TPPlayerMatch.Status.NOTPLAYED),
        (False, 1, None, TPPlayerMatch.Status.NOTPLAYED),
        # walkover: scorestatus @ 1, not played (ignoring winner)
        (False, None, 1, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, 1, TPPlayerMatch.Status.NOTPLAYED),
        # TODO: the following two should not happen, no winner for walkover?
        (False, 1, 1, TPPlayerMatch.Status.NOTPLAYED),
        (False, 1, 1, TPPlayerMatch.Status.NOTPLAYED),
        # retired: scorestatus @ 2, played
        (False, None, 2, TPPlayerMatch.Status.PLAYED),
        (False, None, 2, TPPlayerMatch.Status.PLAYED),
        (False, 1, 2, TPPlayerMatch.Status.PLAYED),
        (False, 1, 2, TPPlayerMatch.Status.PLAYED),
        # disqualified: scorestatus @ 3, played
        (False, None, 3, TPPlayerMatch.Status.PLAYED),
        (False, None, 3, TPPlayerMatch.Status.PLAYED),
        (False, 1, 3, TPPlayerMatch.Status.PLAYED),
        (False, 1, 3, TPPlayerMatch.Status.PLAYED),
        # notplayed: scorestatus @ 9, notplayed
        (False, None, 9, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, 9, TPPlayerMatch.Status.NOTPLAYED),
        # TODO: the following two should not happen, no winner for walkover?
        (False, 1, 9, TPPlayerMatch.Status.NOTPLAYED),
        (False, 1, 9, TPPlayerMatch.Status.NOTPLAYED),
    ],
)
def test_status_not_group(
    pm1: TPPlayerMatch,
    tpentry1: TPEntry,
    useentry: bool,
    winner: None | int,
    scorestatus: None | int,
    status: TPPlayerMatch.Status,
) -> None:
    pm1 = pm1.model_copy(
        update={
            "winner": winner,
            "entry": tpentry1 if useentry else None,
            "scorestatus": scorestatus,
        }
    )
    assert pm1.status == status


@pytest.mark.parametrize(
    "useentry,wn,vn,winner,scorestatus,status",
    [
        # no winner, scorestatus @ 0, so pending
        (True, None, None, None, 0, TPPlayerMatch.Status.PENDING),
        (False, None, None, None, 0, TPPlayerMatch.Status.PENDING),
        (True, None, None, None, None, TPPlayerMatch.Status.PENDING),
        (False, None, None, None, None, TPPlayerMatch.Status.PENDING),
        # yes winner, scorestatus @ 0, so played
        (True, None, None, 1, 0, TPPlayerMatch.Status.PLAYED),
        (False, None, None, 1, 0, TPPlayerMatch.Status.PLAYED),
        (True, None, None, 1, None, TPPlayerMatch.Status.PLAYED),
        (False, None, None, 1, None, TPPlayerMatch.Status.PLAYED),
        # walkover: scorestatus @ 1, not played (ignoring winner)
        (False, 0, 0, None, 1, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, None, None, 1, TPPlayerMatch.Status.NOTPLAYED),
        # TODO: the following two should not happen, no winner for walkover?
        (False, 0, 0, 1, 1, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, None, 1, 1, TPPlayerMatch.Status.NOTPLAYED),
        # retired: scorestatus @ 2, played
        (False, 0, 0, None, 2, TPPlayerMatch.Status.PLAYED),
        (False, None, None, None, 2, TPPlayerMatch.Status.PLAYED),
        (False, 0, 0, 1, 2, TPPlayerMatch.Status.PLAYED),
        (False, None, None, 1, 2, TPPlayerMatch.Status.PLAYED),
        # disqualified: scorestatus @ 3, played
        (False, 0, 0, None, 3, TPPlayerMatch.Status.PLAYED),
        (False, None, None, None, 3, TPPlayerMatch.Status.PLAYED),
        (False, 0, 0, 1, 3, TPPlayerMatch.Status.PLAYED),
        (False, None, None, 1, 3, TPPlayerMatch.Status.PLAYED),
        # notplayed: scorestatus @ 9, notplayed
        (False, 0, 0, None, 9, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, None, None, 9, TPPlayerMatch.Status.NOTPLAYED),
        # TODO: the following two should not happen, no winner for walkover?
        (False, 0, 0, 1, 9, TPPlayerMatch.Status.NOTPLAYED),
        (False, None, None, 1, 9, TPPlayerMatch.Status.NOTPLAYED),
        # byes in a group. There is *nothing* to go by, *except* wn/vn are 0 for those,
        # while wv/vn are also 0 in other cases. So this should be a final check before
        # regarding a match with a bye as pending
        pytest.param(
            True,
            0,
            0,
            None,
            0,
            TPPlayerMatch.Status.NOTPLAYED,
            marks=pytest.mark.xfail(reason="No way to identify Byes in a group"),
        ),
        pytest.param(
            False,
            0,
            0,
            None,
            0,
            TPPlayerMatch.Status.NOTPLAYED,
            marks=pytest.mark.xfail(reason="No way to identify Byes in a group"),
        ),
        pytest.param(
            True,
            0,
            0,
            None,
            None,
            TPPlayerMatch.Status.NOTPLAYED,
            marks=pytest.mark.xfail(reason="No way to identify Byes in a group"),
        ),
        pytest.param(
            False,
            0,
            0,
            None,
            None,
            TPPlayerMatch.Status.NOTPLAYED,
            marks=pytest.mark.xfail(reason="No way to identify Byes in a group"),
        ),
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
    scorestatus: int,
    status: TPPlayerMatch.Status,
) -> None:
    pm1.draw = tpdraw2
    if useentry:
        pm1.entry = tpentry1
    pm1.wn, pm1.vn = wn, vn
    pm1.winner = winner
    pm1.scorestatus = scorestatus
    assert pm1.status == status


@pytest.mark.xfail
def test_winner0_is_not_played(pm: TPPlayerMatch) -> None:
    # This requires a custom type. There is no validation for model instances that are
    # read from the database, and `model_post_init` is also not called. We could map
    # the database column to `winner_` and provide a property that does the
    # `zero_to_none` translation, but that changes the constructor. Not sure how
    # relevant/problematic this actually is. But without any layer to turn 0 into None
    # on the way between assignment and access in the next two lines, this test must
    # fail. Custom types: https://github.com/fastapi/sqlmodel/discussions/1399
    pm.winner = 0
    assert pm.winner is None
    # assert pm.status != PlayerMatchStatus.PLAYED
