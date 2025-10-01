from collections.abc import Callable
from typing import cast

import pytest
from pytest_mock import AsyncMockType, MockerFixture, MockType

from tptools import Tournament, load_tournament
from tptools.court import Court
from tptools.draw import Draw
from tptools.entry import Entry
from tptools.match import Match
from tptools.sqlmodels import (
    TPCourt,
    TPDraw,
    TPEntry,
    TPEvent,
    TPPlayer,
    TPPlayerMatch,
    TPSetting,
)
from tptools.tpmatch import TPMatch
from tptools.tpmatch import TPMatchStatus as MatchStatus

from .conftest import TPMatchFactoryType, TPPlayerFactoryType, TPPlayerMatchFactoryType


def test_from_tournament(tournament1: Tournament) -> None:
    assert Tournament.from_tournament(tournament1) == tournament1


def test_repr_empty_noname() -> None:
    assert (
        repr(Tournament()) == "Tournament(nentries=0, ndraws=0, ncourts=0, nmatches=0)"
    )


def test_repr(tournament1: Tournament) -> None:
    assert (
        repr(tournament1)
        == "Tournament(name='Test 1', nentries=4, ndraws=2, ncourts=2, nmatches=2)"
    )


def test_str(tournament1: Tournament) -> None:
    assert str(tournament1) == "Test 1 (4 entries, 2 draws, 2 courts, 2 matches)"


def test_eq(tournament1: Tournament, tournament1copy: Tournament) -> None:
    assert tournament1 == tournament1copy


def test_ne(tournament1: Tournament, tournament2: Tournament) -> None:
    assert tournament1 != tournament2


def test_lt(tournament1: Tournament, tournament2: Tournament) -> None:
    assert tournament1 < tournament2


def test_le(
    tournament1: Tournament, tournament2: Tournament, tournament1copy: Tournament
) -> None:
    assert tournament1 <= tournament2 and tournament1 <= tournament1copy


def test_gt(tournament1: Tournament, tournament2: Tournament) -> None:
    assert tournament2 > tournament1


def test_ge(
    tournament1: Tournament, tournament2: Tournament, tournament1copy: Tournament
) -> None:
    assert tournament2 >= tournament1 and tournament1 >= tournament1copy


def test_no_cmp(tournament1: Tournament) -> None:
    with pytest.raises(NotImplementedError):
        assert tournament1 == object()


def test_add_duplicate_match(tournament1: Tournament, match1: Match) -> None:
    with pytest.raises(ValueError, match="already added"):
        tournament1.add_match(match1)


def test_add_duplicate_entry(tournament1: Tournament, entry1: Entry) -> None:
    with pytest.raises(ValueError, match="already added"):
        tournament1.add_entry(entry1)


def test_add_duplicate_draw(tournament1: Tournament, draw1: Draw) -> None:
    with pytest.raises(ValueError, match="already added"):
        tournament1.add_draw(draw1)


def test_add_duplicate_court(tournament1: Tournament, court1: Court) -> None:
    with pytest.raises(ValueError, match="already added"):
        tournament1.add_court(court1)


def test_get_matches(tournament2: Tournament, match1: Match) -> None:
    assert match1 in tournament2.get_matches()


@pytest.mark.parametrize(
    "include_played, include_not_ready, expected",
    [
        (True, True, (0, 1, 2, 3)),
        (True, False, (0, 2, 3)),
        (False, True, (0, 1)),
        (False, False, (0,)),
    ],
)
def test_get_matches_params(
    include_played: bool,
    include_not_ready: bool,
    expected: list[int],
    mocker: MockerFixture,
    tournament1: Tournament,
) -> None:
    matches: dict[int, Match] = {}
    for i, status in enumerate(MatchStatus):
        m = mocker.stub(f"Match {status}")
        m.status = status
        m.id = str(i)
        matches[i] = m

    t = tournament1.model_copy(update={"matches": matches})

    ret = t.get_matches(
        include_played=include_played, include_not_ready=include_not_ready
    )

    assert len(ret) == len(expected)
    for e in expected:
        assert matches[e] in ret


def test_get_entries(tournament2: Tournament, tpentry1: TPEntry) -> None:
    assert tpentry1 in tournament2.get_entries()


def test_get_matches_by_draw(
    tournament2: Tournament, match1: Match, match2: Match
) -> None:
    assert match1 in tournament2.get_matches_by_draw(match1.draw)
    assert match2 not in tournament2.get_matches_by_draw(match1.draw)


def test_get_draws(
    tournament1: Tournament, tpmatch1: TPMatch, tpmatch2: TPMatch
) -> None:
    draws = tournament1.get_draws()
    assert tpmatch1.draw in draws
    assert tpmatch2.draw in draws


def test_get_courts(
    tournament1: Tournament, tpcourt1: TPCourt, tpcourt2: TPCourt
) -> None:
    courts = tournament1.get_courts()
    assert tpcourt1 in courts
    assert tpcourt2 in courts


def test_model_dump(tournament1: Tournament) -> None:
    dump = tournament1.model_dump()
    assert "matches" in dump
    assert "entries" in dump
    assert "courts" in dump
    assert "draws" in dump


type MockSessionFactoryType = Callable[..., MockType]
type AsyncMockSessionFactoryType = Callable[..., AsyncMockType]


@pytest.fixture
def MockSessionFactory(
    mocker: MockerFixture,
    tpcourt1: TPCourt,
    tpcourt2: TPCourt,
    tpdraw1: TPDraw,
    tpdraw2: TPDraw,
) -> MockSessionFactoryType:
    def make_mock_session(
        *,
        tournament_name: str | None = None,
        entries: list[TPEntry] | None = None,
        playermatches: list[TPPlayerMatch] | None = None,
        courts: list[TPCourt] | None = None,
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
            draws or [tpdraw1, tpdraw2],
            courts or [tpcourt1, tpcourt2],
            playermatches or [],
        ]

        return cast(MockType, mock_session)  # cast required for mypy

    return make_mock_session


@pytest.mark.asyncio
async def test_load_tournament_elim4(
    MockSessionFactory: MockSessionFactoryType,
    TPPlayerFactory: TPPlayerFactoryType,
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
    TPMatchFactory: TPMatchFactoryType,
    tpevent1: TPEvent,
) -> None:
    entries: list[TPEntry] = []
    pms: list[TPPlayerMatch] = []
    for id, name, wnvn in (
        (1, "one", 1),
        (2, "two", 1),
        (3, "three", 2),
        (4, "four", 2),
    ):
        entry = TPEntry(
            id=id,
            player1=TPPlayer(id=id, lastname=name, firstname="test"),
            event=tpevent1,
        )
        entries.append(entry)
        pms.append(
            TPPlayerFactory(
                planning=3000 + id, wn=2000 + wnvn, vn=2002 + wnvn, entry=entry
            )
        )

    for base, id, matchnr, van1, wn in (
        (2000, 1, 1, 3001, 1001),
        (2000, 3, 2, 3003, 1001),
        (1000, 1, 3, 2001, None),
        (1000, 3, 4, 2003, None),
    ):
        pm = TPPlayerMatchFactory(
            planning=base + id,
            matchnr=matchnr,
            van1=van1,
            van2=van1 + 1,
            wn=wn,
            vn=wn + 1 if wn else None,
        )
        m = TPMatchFactory(pm, tpentry2=None, pldiff=1, lldiff=2)
        pms.append(m.pm1)
        pms.append(m.pm2)

    mock_session = MockSessionFactory(
        tournament_name="Test",
        entries=entries,
        playermatches=pms,
    )

    tournament = await load_tournament(mock_session)

    assert tournament.name == "Test"
    assert tournament.nentries == 4
    assert tournament.nmatches == 4


@pytest.mark.asyncio
async def test_load_tournament_group3(
    MockSessionFactory: MockSessionFactoryType,
    TPPlayerFactory: TPPlayerFactoryType,
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
    tpdraw2: TPDraw,
    tpevent1: TPEvent,
) -> None:
    entries: list[TPEntry] = []
    pms: list[TPPlayerMatch] = []
    for id, name in (
        (1, "one"),
        (2, "two"),
        (3, "three"),
    ):
        entry = TPEntry(
            id=id,
            event=tpevent1,
            player1=TPPlayer(id=id, lastname=name, firstname="test"),
        )
        entries.append(entry)
        pms.append(
            TPPlayerFactory(planning=id * 1000, wn=0, vn=0, entry=entry, draw=tpdraw2)
        )

    for matchnr, a, b in ((1, 3, 2), (2, 2, 1), (3, 3, 1)):
        pms.append(
            TPPlayerMatchFactory(
                draw=tpdraw2,
                planning=1000 * a + b,
                matchnr=matchnr,
                van1=a * 1000,
                van2=b * 1000,
                reversehomeaway=True,
            )
        )
        pms.append(
            TPPlayerMatchFactory(
                draw=tpdraw2,
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

    tournament = await load_tournament(mock_session)

    assert tournament.name == "Test"
    assert tournament.nentries == 3
    assert tournament.nmatches == 3


@pytest.mark.asyncio
async def test_load_tournament_with_player(
    MockSessionFactory: MockSessionFactoryType,
    pmplayer1: TPPlayerMatch,
    pmplayer2: TPPlayerMatch,
) -> None:
    mock_session = MockSessionFactory(
        playermatches=[pmplayer1, pmplayer2],
    )
    tournament = await load_tournament(mock_session)
    assert tournament.nmatches == 0


def test_resolve_entry(tournament1: Tournament, entry1: Entry) -> None:
    assert tournament1.resolve_entry_by_id(entry1.id) == entry1


def test_resolve_court(tournament1: Tournament, court1: Court) -> None:
    assert tournament1.resolve_court_by_id(court1.id) == court1


def test_resolve_draw(tournament1: Tournament, draw1: Draw) -> None:
    assert tournament1.resolve_draw_by_id(draw1.id) == draw1


def test_resolve_match(tournament1: Tournament, match1: Match) -> None:
    assert tournament1.resolve_match_by_id(match1.id) == match1
