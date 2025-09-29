from collections.abc import Iterable

import pytest
import pytest_subtests

from tptools.tpmatch import TPMatch, TPMatchStatus

type MatchIdTuple = tuple[int, int]


def test_loading_all_matches(all_matches: list[TPMatch]) -> None:
    assert len(all_matches) == 68


@pytest.fixture
def matches_by_tuple(all_matches: Iterable[TPMatch]) -> dict[MatchIdTuple, TPMatch]:
    return {(m.draw.id, m.matchnr): m for m in all_matches}


@pytest.fixture
def expected_status_by_tuple() -> dict[MatchIdTuple, TPMatchStatus]:
    return {  # {{{
        (93, 1): TPMatchStatus.PLAYED,
        (93, 2): TPMatchStatus.PLAYED,
        (93, 3): TPMatchStatus.PLAYED,
        (94, 1): TPMatchStatus.PLAYED,
        (94, 2): TPMatchStatus.READY,
        (94, 3): TPMatchStatus.PLAYED,
        (95, 1): TPMatchStatus.PLAYED,
        (95, 2): TPMatchStatus.NOTPLAYED,  # byes in a group
        (95, 3): TPMatchStatus.NOTPLAYED,  # byes in a group
        (96, 1): TPMatchStatus.PLAYED,
        (96, 2): TPMatchStatus.PLAYED,
        (96, 3): TPMatchStatus.PLAYED,
        (97, 1): TPMatchStatus.PLAYED,
        (97, 2): TPMatchStatus.PENDING,  # players unknown or byes?
        (97, 3): TPMatchStatus.PENDING,  # players unknown or byes?
        (97, 4): TPMatchStatus.PENDING,  # players unknown or byes?
        (98, 1): TPMatchStatus.PENDING,  # players unknown or byes?
        (98, 2): TPMatchStatus.PENDING,  # players unknown or byes?
        (98, 3): TPMatchStatus.PENDING,  # players unknown or byes?
        (98, 4): TPMatchStatus.PENDING,  # players unknown or byes?
        (99, 1): TPMatchStatus.PLAYED,
        (99, 2): TPMatchStatus.NOTPLAYED,  # bye
        (99, 3): TPMatchStatus.NOTPLAYED,  # bye
        (99, 4): TPMatchStatus.PLAYED,
        (92, 10): TPMatchStatus.PLAYED,
        (92, 11): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 12): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 13): TPMatchStatus.PLAYED,
        (92, 14): TPMatchStatus.PLAYED,
        (92, 15): TPMatchStatus.NOTPLAYED,  # player 2 retired
        (92, 16): TPMatchStatus.PLAYED,
        (92, 17): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 18): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 19): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 1): TPMatchStatus.PLAYED,
        (92, 20): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 21): TPMatchStatus.NOTPLAYED,  # player 2 disqualified
        (92, 22): TPMatchStatus.NOTPLAYED,
        (92, 23): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 24): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 25): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 26): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 27): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 28): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 29): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 2): TPMatchStatus.PLAYED,
        (92, 30): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 31): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 32): TPMatchStatus.PENDING,  # players unknown or byes?
        (92, 3): TPMatchStatus.PLAYED,
        (92, 4): TPMatchStatus.PLAYED,
        (92, 5): TPMatchStatus.PLAYED,
        (92, 6): TPMatchStatus.PLAYED,
        (92, 7): TPMatchStatus.PLAYED,
        (92, 8): TPMatchStatus.PLAYED,
        (92, 9): TPMatchStatus.PENDING,  # players unknown or byes?
        (80, 10): TPMatchStatus.PENDING,  # players unknown or byes?
        (80, 11): TPMatchStatus.PLAYED,
        (80, 12): TPMatchStatus.PENDING,  # players unknown or byes?
        (80, 1): TPMatchStatus.NOTPLAYED,  # first round bye
        (80, 2): TPMatchStatus.PLAYED,
        (80, 3): TPMatchStatus.PLAYED,
        (80, 4): TPMatchStatus.PLAYED,
        (80, 5): TPMatchStatus.NOTPLAYED,
        (80, 6): TPMatchStatus.PENDING,  # players unknown or byes?
        (80, 7): TPMatchStatus.PLAYED,
        (80, 8): TPMatchStatus.PLAYED,
        (80, 9): TPMatchStatus.PENDING,  # players unknown or byes?
    }  # }}}


def test_match_status(
    matches_by_tuple: dict[MatchIdTuple, TPMatch],
    expected_status_by_tuple: dict[MatchIdTuple, TPMatchStatus],
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
