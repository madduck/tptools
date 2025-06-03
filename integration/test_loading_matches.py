from collections.abc import Iterable

import pytest
import pytest_subtests

from tptools.match import Match
from tptools.matchstatus import MatchStatus

type MatchIdTuple = tuple[int, int]


def test_loading_all_matches(all_matches: list[Match]) -> None:
    assert len(all_matches) == 68


@pytest.fixture
def matches_by_tuple(all_matches: Iterable[Match]) -> dict[MatchIdTuple, Match]:
    return {(m.draw.id, m.matchnr): m for m in all_matches}


@pytest.fixture
def expected_status_by_tuple() -> dict[MatchIdTuple, MatchStatus]:
    return {  # {{{
        (93, 1): MatchStatus.PLAYED,
        (93, 2): MatchStatus.PLAYED,
        (93, 3): MatchStatus.PLAYED,
        (94, 1): MatchStatus.PLAYED,
        (94, 2): MatchStatus.READY,
        (94, 3): MatchStatus.PLAYED,
        (95, 1): MatchStatus.PLAYED,
        (95, 2): MatchStatus.NOTPLAYED,  # byes in a group
        (95, 3): MatchStatus.NOTPLAYED,  # byes in a group
        (96, 1): MatchStatus.PLAYED,
        (96, 2): MatchStatus.PLAYED,
        (96, 3): MatchStatus.PLAYED,
        (97, 1): MatchStatus.PLAYED,
        (97, 2): MatchStatus.PENDING,  # players unknown or byes?
        (97, 3): MatchStatus.PENDING,  # players unknown or byes?
        (97, 4): MatchStatus.PENDING,  # players unknown or byes?
        (98, 1): MatchStatus.PENDING,  # players unknown or byes?
        (98, 2): MatchStatus.PENDING,  # players unknown or byes?
        (98, 3): MatchStatus.PENDING,  # players unknown or byes?
        (98, 4): MatchStatus.PENDING,  # players unknown or byes?
        (99, 1): MatchStatus.PLAYED,
        (99, 2): MatchStatus.NOTPLAYED,  # bye
        (99, 3): MatchStatus.NOTPLAYED,  # bye
        (99, 4): MatchStatus.PLAYED,
        (92, 10): MatchStatus.PLAYED,
        (92, 11): MatchStatus.PENDING,  # players unknown or byes?
        (92, 12): MatchStatus.PENDING,  # players unknown or byes?
        (92, 13): MatchStatus.PLAYED,
        (92, 14): MatchStatus.PLAYED,
        (92, 15): MatchStatus.NOTPLAYED,  # player 2 retired
        (92, 16): MatchStatus.PLAYED,
        (92, 17): MatchStatus.PENDING,  # players unknown or byes?
        (92, 18): MatchStatus.PENDING,  # players unknown or byes?
        (92, 19): MatchStatus.PENDING,  # players unknown or byes?
        (92, 1): MatchStatus.PLAYED,
        (92, 20): MatchStatus.PENDING,  # players unknown or byes?
        (92, 21): MatchStatus.NOTPLAYED,  # player 2 disqualified
        (92, 22): MatchStatus.NOTPLAYED,
        (92, 23): MatchStatus.PENDING,  # players unknown or byes?
        (92, 24): MatchStatus.PENDING,  # players unknown or byes?
        (92, 25): MatchStatus.PENDING,  # players unknown or byes?
        (92, 26): MatchStatus.PENDING,  # players unknown or byes?
        (92, 27): MatchStatus.PENDING,  # players unknown or byes?
        (92, 28): MatchStatus.PENDING,  # players unknown or byes?
        (92, 29): MatchStatus.PENDING,  # players unknown or byes?
        (92, 2): MatchStatus.PLAYED,
        (92, 30): MatchStatus.PENDING,  # players unknown or byes?
        (92, 31): MatchStatus.PENDING,  # players unknown or byes?
        (92, 32): MatchStatus.PENDING,  # players unknown or byes?
        (92, 3): MatchStatus.PLAYED,
        (92, 4): MatchStatus.PLAYED,
        (92, 5): MatchStatus.PLAYED,
        (92, 6): MatchStatus.PLAYED,
        (92, 7): MatchStatus.PLAYED,
        (92, 8): MatchStatus.PLAYED,
        (92, 9): MatchStatus.PENDING,  # players unknown or byes?
        (80, 10): MatchStatus.PENDING,  # players unknown or byes?
        (80, 11): MatchStatus.PLAYED,
        (80, 12): MatchStatus.PENDING,  # players unknown or byes?
        (80, 1): MatchStatus.NOTPLAYED,  # first round bye
        (80, 2): MatchStatus.PLAYED,
        (80, 3): MatchStatus.PLAYED,
        (80, 4): MatchStatus.PLAYED,
        (80, 5): MatchStatus.NOTPLAYED,
        (80, 6): MatchStatus.PENDING,  # players unknown or byes?
        (80, 7): MatchStatus.PLAYED,
        (80, 8): MatchStatus.PLAYED,
        (80, 9): MatchStatus.PENDING,  # players unknown or byes?
    }  # }}}


def test_match_status(
    matches_by_tuple: dict[MatchIdTuple, Match],
    expected_status_by_tuple: dict[MatchIdTuple, MatchStatus],
    subtests: pytest_subtests.SubTests,
) -> None:
    n = 0
    for idtuple, match in matches_by_tuple.items():
        n += 1
        with subtests.test(
            _=match,
            expected=(exp := expected_status_by_tuple[idtuple]).name.lower(),
            idtuple=idtuple,
        ):
            assert match.status == exp, (
                f"{match} not at expected status {exp} ({idtuple=})"
            )
    assert n == 68


# vim:fdm=marker:fdl=0
