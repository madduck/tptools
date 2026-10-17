from datetime import datetime

import pytest

from tptools import Match

from .conftest import ScorePairFactoryType


def test_repr(match1: Match) -> None:
    assert repr(match1) == (
        "Match(id='1-14', matchnr=14, draw=Draw(id=1, name='Baum', "
        "stage.name='Qual', type=MONRAD, size=8), time=datetime(2025, 6, 1, 11, 30), "
        "court=Court(id=1, name='C01', location.name='Sports4You'), "
        "A=Entry(event.name='Herren 1', player1.name='Martin Krafft'), "
        "B=Entry(event.name='Herren 1', player1.name='Iddo Hoeve'), "
        "status=ready, starttime=None, endtime=None, winner=None, scores=-)"
    )


def test_str(match1: Match) -> None:
    assert str(match1) == "1-14 ready on C01 (Sports4You) @ 11:30"


def test_cmp_eq(match1: Match, match1copy: Match) -> None:
    assert match1 == match1copy


def test_cmp_ne(match1: Match, match2: Match) -> None:
    assert match1 != match2


def test_cmp_lt(match1: Match, match2: Match) -> None:
    assert match1 < match2


def test_cmp_le(match1: Match, match1copy: Match, match2: Match) -> None:
    assert match1 < match2 and match1 <= match1copy


def test_cmp_gt(match1: Match, match2: Match) -> None:
    assert match2 > match1


def test_cmp_ge(match1: Match, match1copy: Match, match2: Match) -> None:
    assert match2 > match1 and match1 >= match1copy


@pytest.mark.parametrize("attr", ["time", "starttime", "endtime"])
def test_match_timestamps_have_timezone(
    match1: Match, attr: str, now: datetime
) -> None:
    m = Match(**match1.model_dump() | {attr: now})  # pyright: ignore[reportArgumentType]
    assert getattr(m, attr).tzinfo is not None


def test_match_dump_includes_errors(ScorePairFactory: ScorePairFactoryType) -> None:
    """The generic Match dump carries the errors array."""
    match = Match.from_tpmatch(ScorePairFactory([(15, 11)]))
    assert match.errors
    assert match.model_dump()["errors"] == match.errors


@pytest.mark.parametrize(
    "scores",
    [
        [(11, 10)],
        [(11, 12)],
        [(15, 11)],
    ],
)
def test_match_errors_for_illegal_set_scores(
    ScorePairFactory: ScorePairFactoryType, scores: list[tuple[int, int]]
) -> None:
    """A Match built from an illegal TPMatch carries the recorded errors."""
    match = Match.from_tpmatch(ScorePairFactory(scores))
    assert match.errors


def test_match_errors_empty_for_legal_set_scores(
    ScorePairFactory: ScorePairFactoryType,
) -> None:
    """A Match built from a clean TPMatch has no errors."""
    match = Match.from_tpmatch(ScorePairFactory([(11, 5)]))
    assert match.errors == []


def test_match_from_tpmatch_shallow_copies_errors(
    ScorePairFactory: ScorePairFactoryType,
) -> None:
    """Match.from_tpmatch shallow-copies the TPMatch's errors.

    The Match must get a list of its own (same contents, distinct object), so
    that appending to one model's errors does not affect the other's.
    """
    tpmatch = ScorePairFactory([(15, 11)])
    tpmatch.errors.append("invented")
    match = Match.from_tpmatch(tpmatch)
    assert match.errors == tpmatch.errors
    assert match.errors is not tpmatch.errors
    match.errors.append("only on the match")
    assert "only on the match" not in tpmatch.errors


def test_match_errors_default_is_not_shared(
    ScorePairFactory: ScorePairFactoryType,
) -> None:
    """The Match errors default must come from default_factory=list.

    A bare ``errors: list[str] = []`` default would be shared across all
    instances: mutating one match's errors would leak into every other match.
    """
    one = Match.from_tpmatch(ScorePairFactory([(11, 5)]))
    two = Match.from_tpmatch(ScorePairFactory([(11, 5)]))
    one.errors.append("marker")
    assert two.errors == []
