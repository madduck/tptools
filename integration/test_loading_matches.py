from collections.abc import Iterable

import pytest
import pytest_subtests

from tptools.tpmatch import TPMatch, TPMatchStatus
from tptools.util import ScoresType

type MatchIdTuple = tuple[int, int]


def test_loading_all_matches(all_tpmatches: list[TPMatch]) -> None:
    assert len(all_tpmatches) == 68


@pytest.fixture
def tpmatches_by_tuple(all_tpmatches: Iterable[TPMatch]) -> dict[MatchIdTuple, TPMatch]:
    return {(m.draw.id, m.matchnr): m for m in all_tpmatches}


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
        (95, 2): TPMatchStatus.READY,  # byes in a group cannot be identified
        (95, 3): TPMatchStatus.READY,  # byes in a group cannot be identified
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


@pytest.fixture
def expected_scores_by_tuple() -> dict[MatchIdTuple, ScoresType]:
    return {  # {{{
        (80, 10): [],  # players unknown or byes?
        (80, 11): [(11, 4), (11, 7), (13, 11)],
        (80, 12): [],  # players unknown or byes?
        (80, 1): [],  # first round bye
        (80, 2): [(11, 3), (3, 11), (6, 11), (6, 11)],
        (80, 3): [(2, 11), (5, 11), (4, 11)],
        (80, 4): [(6, 11), (11, 4), (5, 11), (8, 11)],
        (80, 5): [],
        (80, 6): [],
        (80, 7): [(11, 4), (11, 5), (11, 6)],
        (80, 8): [(3, 11), (4, 11), (5, 11)],
        (80, 9): [],  # players unknown or byes?
        (92, 10): [(4, 11), (3, 11), (9, 11)],
        (92, 1): [(3, 11), (4, 11), (5, 11)],
        (92, 11): [],  # players unknown or byes?
        (92, 12): [],  # players unknown or byes?
        (92, 13): [(11, 4), (11, 5), (11, 6)],
        (92, 14): [(3, 11), (4, 11), (5, 11)],
        (92, 15): [],  # player 2 retired
        (92, 16): [(3, 11), (11, 13), (1, 11)],
        (92, 17): [],  # players unknown or byes?
        (92, 18): [],  # players unknown or byes?
        (92, 19): [],  # players unknown or byes?
        (92, 20): [],  # players unknown or byes?
        (92, 2): [(11, 5), (11, 4), (3, 11), (11, 4)],
        (92, 21): [(5, 11), (5, 11), (3, 6)],
        (92, 22): [],
        (92, 23): [],  # players unknown or byes?
        (92, 24): [],  # players unknown or byes?
        (92, 25): [],  # players unknown or byes?
        (92, 26): [],  # players unknown or byes?
        (92, 27): [],  # players unknown or byes?
        (92, 28): [],  # players unknown or byes?
        (92, 29): [],  # players unknown or byes?
        (92, 30): [],  # players unknown or byes?
        (92, 3): [(10, 12), (11, 13), (4, 11)],
        (92, 31): [],  # players unknown or byes?
        (92, 32): [],  # players unknown or byes?
        (92, 4): [(11, 5), (11, 4), (11, 7)],
        (92, 5): [(4, 11), (11, 6), (5, 11), (11, 3), (9, 11)],
        (92, 6): [(4, 11), (5, 11), (6, 11)],
        (92, 7): [(12, 14), (12, 14), (12, 14)],
        (92, 8): [(4, 11), (6, 11), (7, 11)],
        (92, 9): [],  # players unknown or byes?
        (93, 1): [(11, 9), (11, 8), (7, 11), (11, 5)],
        (93, 2): [(11, 3), (11, 4), (11, 1)],
        (93, 3): [(11, 7), (11, 4), (11, 9)],
        (94, 1): [(11, 6), (9, 11), (11, 13), (11, 2), (11, 9)],
        (94, 2): [],
        (94, 3): [(11, 2), (11, 4), (11, 3)],
        (95, 1): [(6, 11), (11, 4), (11, 5), (11, 9)],
        (95, 2): [],  # byes in a group cannot be identified
        (95, 3): [],  # byes in a group cannot be identified
        (96, 1): [(11, 5), (11, 6), (11, 7)],
        (96, 2): [(6, 11), (9, 11), (4, 11)],
        (96, 3): [(11, 3), (11, 2), (11, 1)],
        (97, 1): [(7, 11), (11, 8), (11, 6), (4, 11), (11, 13)],
        (97, 2): [],  # players unknown or byes?
        (97, 3): [],  # players unknown or byes?
        (97, 4): [],  # players unknown or byes?
        (98, 1): [],  # players unknown or byes?
        (98, 2): [],  # players unknown or byes?
        (98, 3): [],  # players unknown or byes?
        (98, 4): [],  # players unknown or byes?
        (99, 1): [(11, 4), (11, 3), (11, 2)],
        (99, 2): [],  # bye
        (99, 3): [],  # bye
        (99, 4): [(5, 11), (4, 11), (6, 11)],
    }  # }}}


def test_match_status(
    tpmatches_by_tuple: dict[MatchIdTuple, TPMatch],
    expected_status_by_tuple: dict[MatchIdTuple, TPMatchStatus],
    subtests: pytest_subtests.SubTests,
) -> None:
    n = 0
    for idtuple, match in tpmatches_by_tuple.items():
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


def test_match_scores(
    tpmatches_by_tuple: dict[MatchIdTuple, TPMatch],
    expected_scores_by_tuple: dict[MatchIdTuple, ScoresType],
    subtests: pytest_subtests.SubTests,
) -> None:
    n = 0
    for idtuple, match in tpmatches_by_tuple.items():
        n += 1
        with subtests.test(
            _=match,
            expected=(exp := expected_scores_by_tuple[idtuple]),
            idtuple=idtuple,
        ):
            assert match.scores == exp, (
                f"{match} does not have expected score {exp} ({idtuple=})"
            )
    assert n == 68


# vim:fdm=marker:fdl=0
