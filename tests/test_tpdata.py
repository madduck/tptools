from collections.abc import Callable
from typing import cast

import pytest
from pytest_mock import AsyncMockType, MockerFixture, MockType

from tptools.match import Match
from tptools.matchstatus import MatchStatus
from tptools.sqlmodels import Court, Entry, Player, PlayerMatch, TPDraw, TPSetting
from tptools.tpdata import TPData, load_tournament

from .conftest import MatchFactoryType, PlayerFactoryType, PlayerMatchFactoryType


def test_repr_empty_noname() -> None:
    assert repr(TPData()) == "TPData(nentries=0, ndraws=0, ncourts=0, nmatches=0)"


def test_repr(tpdata1: TPData) -> None:
    assert (
        repr(tpdata1)
        == "TPData(name='Test 1', nentries=4, ndraws=2, ncourts=2, nmatches=2)"
    )


def test_str(tpdata1: TPData) -> None:
    assert str(tpdata1) == "Test 1 (4 entries, 2 draws, 2 courts, 2 matches)"


def test_eq(tpdata1: TPData, tpdata1copy: TPData) -> None:
    assert tpdata1 == tpdata1copy


def test_ne(tpdata1: TPData, tpdata2: TPData) -> None:
    assert tpdata1 != tpdata2


def test_lt(tpdata1: TPData, tpdata2: TPData) -> None:
    assert tpdata1 < tpdata2


def test_le(tpdata1: TPData, tpdata2: TPData, tpdata1copy: TPData) -> None:
    assert tpdata1 <= tpdata2 and tpdata1 <= tpdata1copy


def test_gt(tpdata1: TPData, tpdata2: TPData) -> None:
    assert tpdata2 > tpdata1


def test_ge(tpdata1: TPData, tpdata2: TPData, tpdata1copy: TPData) -> None:
    assert tpdata2 >= tpdata1 and tpdata1 >= tpdata1copy


def test_no_cmp(tpdata1: TPData) -> None:
    with pytest.raises(NotImplementedError):
        assert tpdata1 == object()


def test_add_duplicate_match(tpdata1: TPData, match1: Match) -> None:
    with pytest.raises(ValueError, match="already added"):
        tpdata1.add_match(match1)


def test_add_duplicate_entry(tpdata1: TPData, entry1: Entry) -> None:
    with pytest.raises(ValueError, match="already added"):
        tpdata1.add_entry(entry1)


def test_add_duplicate_draw(tpdata1: TPData, draw1: TPDraw) -> None:
    with pytest.raises(ValueError, match="already added"):
        tpdata1.add_draw(draw1)


def test_add_duplicate_court(tpdata1: TPData, court1: Court) -> None:
    with pytest.raises(ValueError, match="already added"):
        tpdata1.add_court(court1)


def test_get_matches(tpdata2: TPData, match1: Match) -> None:
    assert match1 in tpdata2.get_matches()


@pytest.mark.parametrize(
    "include_played, include_not_ready, expected",
    [
        (True, True, (0, 1, 2, 3)),
        (True, False, (0, 2, 3)),
        (False, True, (0, 1)),
        (False, False, (0,)),
    ],
)
def test_get_matches_with_played(
    include_played: bool,
    include_not_ready: bool,
    expected: list[int],
    mocker: MockerFixture,
    tpdata1: TPData,
) -> None:
    matches = []
    for status in MatchStatus:
        m = mocker.stub(f"Match {status}")
        m.status = status
        matches.append(m)

    t = tpdata1.model_copy(update={"matches": matches})

    ret = t.get_matches(
        include_played=include_played, include_not_ready=include_not_ready
    )

    assert len(ret) == len(expected)
    for e in expected:
        assert matches[e] in ret


def test_get_entries(tpdata2: TPData, entry1: Entry) -> None:
    assert entry1 in tpdata2.get_entries()


def test_get_matches_by_draw(tpdata2: TPData, match1: Match, match2: Match) -> None:
    assert match1 in tpdata2.get_matches_by_draw(match1.draw)
    assert match2 not in tpdata2.get_matches_by_draw(match1.draw)


def test_get_draws(tpdata1: TPData, match1: Match, match2: Match) -> None:
    draws = tpdata1.get_draws()
    assert match1.draw in draws
    assert match2.draw in draws


def test_get_courts(tpdata1: TPData, court1: Court, court2: Court) -> None:
    courts = tpdata1.get_courts()
    assert court1 in courts
    assert court2 in courts


def test_model_dump(tpdata1: TPData) -> None:
    dump = tpdata1.model_dump()
    assert "matches" in dump
    assert "entries" in dump


type MockSessionFactoryType = Callable[..., MockType]
type AsyncMockSessionFactoryType = Callable[..., AsyncMockType]


@pytest.fixture
def MockSessionFactory(
    mocker: MockerFixture,
    court1: Court,
    court2: Court,
    draw1: TPDraw,
    draw2: TPDraw,
) -> MockSessionFactoryType:
    def make_mock_session(
        *,
        tournament_name: str | None = None,
        entries: list[Entry] | None = None,
        playermatches: list[PlayerMatch] | None = None,
        courts: list[Court] | None = None,
        draws: list[TPDraw] | None = None,
    ) -> MockType:
        mock_session = mocker.Mock()
        tname_setting = mocker.Mock()

        tname_setting.one_or_none.return_value = TPSetting(
            id=1, name="Tournament", value=tournament_name
        )

        mock_session.exec.side_effect = [
            tname_setting,
            entries or [],
            draws or [draw1, draw2],
            courts or [court1, court2],
            playermatches or [],
        ]

        return cast(MockType, mock_session)  # cast required for mypy

    return make_mock_session


@pytest.mark.asyncio
async def test_load_tournament_elim4(
    MockSessionFactory: MockSessionFactoryType,
    PlayerFactory: PlayerFactoryType,
    PlayerMatchFactory: PlayerMatchFactoryType,
    MatchFactory: MatchFactoryType,
) -> None:
    entries: list[Entry] = []
    pms: list[PlayerMatch] = []
    for id, name, wnvn in (
        (1, "one", 1),
        (2, "two", 1),
        (3, "three", 2),
        (4, "four", 2),
    ):
        entry = Entry(player1=Player(id=id, lastname=name, firstname="test"))
        entries.append(entry)
        pms.append(
            PlayerFactory(
                planning=3000 + id, wn=2000 + wnvn, vn=2002 + wnvn, entry=entry
            )
        )

    for base, id, matchnr, van1, wn in (
        (2000, 1, 1, 3001, 1001),
        (2000, 3, 2, 3003, 1001),
        (1000, 1, 3, 2001, None),
        (1000, 3, 4, 2003, None),
    ):
        pm = PlayerMatchFactory(
            planning=base + id,
            matchnr=matchnr,
            van1=van1,
            van2=van1 + 1,
            wn=wn,
            vn=wn + 1 if wn else None,
        )
        m = MatchFactory(pm, entry2=None, pldiff=1, lldiff=2)
        pms.append(m.pm1)
        pms.append(m.pm2)

    mock_session = MockSessionFactory(
        tournament_name="Test",
        entries=entries,
        playermatches=pms,
    )

    tpdata = await load_tournament(mock_session)

    assert tpdata.name == "Test"
    assert tpdata.nentries == 4
    assert tpdata.nmatches == 4


@pytest.mark.asyncio
async def test_load_tournament_group3(
    MockSessionFactory: MockSessionFactoryType,
    PlayerFactory: PlayerFactoryType,
    PlayerMatchFactory: PlayerMatchFactoryType,
    draw2: TPDraw,
) -> None:
    entries: list[Entry] = []
    pms: list[PlayerMatch] = []
    for id, name in (
        (1, "one"),
        (2, "two"),
        (3, "three"),
    ):
        entry = Entry(player1=Player(id=id, lastname=name, firstname="test"))
        entries.append(entry)
        pms.append(
            PlayerFactory(planning=id * 1000, wn=0, vn=0, entry=entry, draw=draw2)
        )

    for matchnr, a, b in ((1, 3, 2), (2, 2, 1), (3, 3, 1)):
        pms.append(
            PlayerMatchFactory(
                draw=draw2,
                planning=1000 * a + b,
                matchnr=matchnr,
                van1=a * 1000,
                van2=b * 1000,
                reversehomeaway=True,
            )
        )
        pms.append(
            PlayerMatchFactory(
                draw=draw2,
                planning=1000 * b + a,
                matchnr=matchnr,
                van1=b * 1000,
                van2=a * 1000,
            )
        )

    mock_session = MockSessionFactory(
        tournament_name="Test",
        entries=entries,
        playermatches=pms,
    )

    tpdata = await load_tournament(mock_session)

    assert tpdata.name == "Test"
    assert tpdata.nentries == 3
    assert tpdata.nmatches == 3


@pytest.mark.asyncio
async def test_load_tournament_with_player(
    MockSessionFactory: MockSessionFactoryType,
    pmplayer1: PlayerMatch,
    pmplayer2: PlayerMatch,
) -> None:
    mock_session = MockSessionFactory(
        playermatches=[pmplayer1, pmplayer2],
    )
    tpdata = await load_tournament(mock_session)
    assert tpdata.nmatches == 0
