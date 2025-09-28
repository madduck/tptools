from contextlib import nullcontext
from typing import Any, ContextManager, cast

import pytest
from pydantic import ValidationError

from tptools.match import Match
from tptools.matchstatus import MatchStatus
from tptools.slot import Bye, Slot, Unknown
from tptools.sqlmodels import Entry, PlayerMatch

from .conftest import MatchFactoryType


def test_repr(match1: Match) -> None:
    assert repr(match1) == (
        "Match(id='1-14', draw.name='Baum', matchnr=14, "
        "time=datetime(2025, 6, 1, 11, 30), court='Sports4You, C01', "
        "slot1.name='Martin Krafft', slot2.name='Iddo Hoeve', "
        "planning=3001/5, van=4001/2, wnvn=2001/3,2005/7, status=ready)"
    )


def test_repr_explicit_entries(match1: Match, slot1: Slot, slot2: Slot) -> None:
    match1.set_slots(slot1, slot2)
    test_repr(match1)


def test_str(match1: Match) -> None:
    assert str(match1) == ("1-14 [Baum] [4001/2 → 3001/5 → 2001/3,2005/7] (ready)")


def test_eq(match1: Match, match1copy: Match) -> None:
    assert match1 == match1copy


def test_eq_reversed(match1: Match) -> None:
    assert match1 == Match(pm1=match1.pm2, pm2=match1.pm1)


def test_ne(match1: Match, match2: Match) -> None:
    assert match1 != match2


def test_lt(match1: Match, match2: Match) -> None:
    assert match1 < match2


def test_le(match1: Match, match2: Match, match1copy: Match) -> None:
    assert match1 <= match2 and match1 <= match1copy


def test_gt(match1: Match, match2: Match) -> None:
    assert match2 > match1


def test_ge(match1: Match, match2: Match, match1copy: Match) -> None:
    assert match2 >= match1 and match1 >= match1copy


def test_no_cmp(match1: Match) -> None:
    with pytest.raises(NotImplementedError):
        assert match1 == object()


def test_hash_equality(match1: Match, match1copy: Match) -> None:
    assert hash(match1) == hash(match1copy)


def test_hash_inequality(match1: Match, match2: Match) -> None:
    assert hash(match1) != hash(match2)


def test_van_properties(match1: Match) -> None:
    """Test property access since __repr__ is actually
    going at the PlayerMatch directly
    """
    assert len(match1.van) == 2


def test_assert_nonempty_van(match1: Match) -> None:
    pm1 = match1.pm1.model_copy(update={"van1": None, "van2": None})
    with pytest.raises(ValidationError, match="that are not players or byes"):
        _ = Match(pm1=pm1, pm2=match1.pm2)


@pytest.mark.parametrize("field", ("id", "entry", "wn", "vn"))
def test_differing_fields(match1: Match, field: str) -> None:
    pm1 = match1.pm1
    pm2 = match1.pm2.model_copy(update={field: getattr(pm1, field)})
    with pytest.raises(ValidationError, match=f"same value for '{field}'"):
        _ = Match(pm1=pm1, pm2=pm2)


@pytest.mark.parametrize("field", ("id", "entry", "wn", "vn"))
def test_differing_field_but_none(match1: Match, field: str) -> None:
    pm1 = match1.pm1
    pm2 = match1.pm2.model_copy(update={field: None})
    _ = Match(pm1=pm1, pm2=pm2)


def test_winner_consistent(match1: Match) -> None:
    pm1 = match1.pm1.model_copy(update={"winner": 1})
    pm2 = match1.pm2.model_copy(update={"winner": 1})
    with pytest.raises(ValidationError, match=r"winner fields: \d\+\d != 3"):
        _ = Match(pm1=pm1, pm2=pm2)


def test_winner_consistent_none(match1: Match) -> None:
    pm1 = match1.pm1.model_copy(update={"winner": None})
    pm2 = match1.pm2.model_copy(update={"winner": 1})
    with pytest.raises(ValidationError, match=r"winner fields inconsistent: .+ vs. .+"):
        _ = Match(pm1=pm1, pm2=pm2)


def test_status_finished(match1: Match) -> None:
    first = match1.pm1.model_copy(update={"winner": 1})
    second = match1.pm2.model_copy(update={"winner": 2})
    m = Match(pm1=first, pm2=second)
    assert m.status == MatchStatus.PLAYED


@pytest.mark.parametrize(
    "updict_1,updict_2,expected",
    [
        # an entry of None signifies a Bye.
        # it. TODO: assess if this should raise an exception!
        ({"winner": None, "entry": None}, None, nullcontext(MatchStatus.PENDING)),
        # if either entry is None, then we are not ready
        (
            {"winner": None, "entry": None},
            {"winner": None},
            nullcontext(MatchStatus.PENDING),
        ),
        (
            {"winner": None},
            {"winner": None, "entry": None},
            nullcontext(MatchStatus.PENDING),
        ),
        ({"winner": 1}, {"winner": 2}, nullcontext(MatchStatus.PLAYED)),
        (
            {"entry": None, "winner": 1},
            {"entry": None, "winner": 2},
            nullcontext(MatchStatus.NOTPLAYED),
        ),
        (
            {"entry": None, "winner": 1},
            {"winner": 2},
            nullcontext(MatchStatus.NOTPLAYED),
        ),
        ({"winner": 1}, {}, pytest.raises(ValueError)),
    ],
)
def test_other_statuses(
    match1: Match,
    updict_1: dict[str, Any],
    updict_2: dict[str, Any] | None,
    expected: ContextManager[None],
) -> None:
    first = match1.pm1.model_copy(update=updict_1)
    second = match1.pm2.model_copy(update=updict_1 if updict_2 is None else updict_2)

    with expected as e:
        m = Match(pm1=first, pm2=second)
        assert m.status == e


def test_set_entry_bye_status_override(match1: Match) -> None:
    match1.set_slots(Slot(content=Bye()), Slot(content=cast(Entry, match1.pm2.entry)))
    assert match1.status == MatchStatus.READY


def test_set_entry_knonwn_status_override(match1: Match) -> None:
    match1.set_slots(
        Slot(content=Unknown()), Slot(content=cast(Entry, match1.pm2.entry))
    )
    assert match1.status == MatchStatus.PENDING


def test_lower_planning_playermatch_first(
    pm1: PlayerMatch, MatchFactory: MatchFactoryType, entry2: Entry
) -> None:
    m = MatchFactory(pm1, entry2, lldiff=4)
    m = Match(pm1=m.pm2, pm2=m.pm1)  # reversed on purpose
    assert m.pm1 == pm1


def test_winner(match1: Match) -> None:
    pm1 = match1.pm1.model_copy(update={"winner": 1})
    pm2 = match1.pm2.model_copy(update={"winner": 2})
    m = Match(pm1=pm1, pm2=pm2)
    assert m.winner == pm1.entry


def test_winner_pms_reversed(match1: Match) -> None:
    pm1 = match1.pm1.model_copy(update={"winner": 1})
    pm2 = match1.pm2.model_copy(update={"winner": 2})
    m = Match(pm1=pm2, pm2=pm1)
    assert m.winner == pm1.entry
