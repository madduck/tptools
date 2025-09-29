from contextlib import nullcontext
from typing import Any, ContextManager, cast

import pytest
from pydantic import ValidationError

from tptools.slot import Bye, Slot, Unknown
from tptools.sqlmodels import TPEntry, TPPlayerMatch
from tptools.tpmatch import TPMatch
from tptools.tpmatchstatus import MatchStatus

from .conftest import TPMatchFactoryType


def test_repr(tpmatch1: TPMatch) -> None:
    assert repr(tpmatch1) == (
        "TPMatch(id='1-14', draw.name='Baum', matchnr=14, "
        "time=datetime(2025, 6, 1, 11, 30), court='Sports4You, C01', "
        "slot1.name='Martin Krafft', slot2.name='Iddo Hoeve', "
        "planning=3001/5, van=4001/2, wnvn=2001/3,2005/7, status=ready)"
    )


def test_repr_explicit_entries(tpmatch1: TPMatch, slot1: Slot, slot2: Slot) -> None:
    tpmatch1.set_slots(slot1, slot2)
    test_repr(tpmatch1)


def test_str(tpmatch1: TPMatch) -> None:
    assert str(tpmatch1) == ("1-14 [Baum] [4001/2 → 3001/5 → 2001/3,2005/7] (ready)")


def test_eq(tpmatch1: TPMatch, tpmatch1copy: TPMatch) -> None:
    assert tpmatch1 == tpmatch1copy


def test_eq_reversed(tpmatch1: TPMatch) -> None:
    assert tpmatch1 == TPMatch(pm1=tpmatch1.pm2, pm2=tpmatch1.pm1)


def test_ne(tpmatch1: TPMatch, tpmatch2: TPMatch) -> None:
    assert tpmatch1 != tpmatch2


def test_lt(tpmatch1: TPMatch, tpmatch2: TPMatch) -> None:
    assert tpmatch1 < tpmatch2


def test_le(tpmatch1: TPMatch, tpmatch2: TPMatch, tpmatch1copy: TPMatch) -> None:
    assert tpmatch1 <= tpmatch2 and tpmatch1 <= tpmatch1copy


def test_gt(tpmatch1: TPMatch, tpmatch2: TPMatch) -> None:
    assert tpmatch2 > tpmatch1


def test_ge(tpmatch1: TPMatch, tpmatch2: TPMatch, tpmatch1copy: TPMatch) -> None:
    assert tpmatch2 >= tpmatch1 and tpmatch1 >= tpmatch1copy


def test_no_cmp(tpmatch1: TPMatch) -> None:
    with pytest.raises(NotImplementedError):
        assert tpmatch1 == object()


def test_hash_equality(tpmatch1: TPMatch, tpmatch1copy: TPMatch) -> None:
    assert hash(tpmatch1) == hash(tpmatch1copy)


def test_hash_inequality(tpmatch1: TPMatch, tpmatch2: TPMatch) -> None:
    assert hash(tpmatch1) != hash(tpmatch2)


def test_van_properties(tpmatch1: TPMatch) -> None:
    """Test property access since __repr__ is actually
    going at the PlayerMatch directly
    """
    assert len(tpmatch1.van) == 2


def test_assert_nonempty_van(tpmatch1: TPMatch) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"van1": None, "van2": None})
    with pytest.raises(ValidationError, match="that are not players or byes"):
        _ = TPMatch(pm1=pm1, pm2=tpmatch1.pm2)


@pytest.mark.parametrize("field", ("id", "entry", "wn", "vn"))
def test_differing_fields(tpmatch1: TPMatch, field: str) -> None:
    pm1 = tpmatch1.pm1
    pm2 = tpmatch1.pm2.model_copy(update={field: getattr(pm1, field)})
    with pytest.raises(ValidationError, match=f"same value for '{field}'"):
        _ = TPMatch(pm1=pm1, pm2=pm2)


@pytest.mark.parametrize("field", ("id", "entry", "wn", "vn"))
def test_differing_field_but_none(tpmatch1: TPMatch, field: str) -> None:
    pm1 = tpmatch1.pm1
    pm2 = tpmatch1.pm2.model_copy(update={field: None})
    _ = TPMatch(pm1=pm1, pm2=pm2)


def test_winner_consistent(tpmatch1: TPMatch) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"winner": 1})
    pm2 = tpmatch1.pm2.model_copy(update={"winner": 1})
    with pytest.raises(ValidationError, match=r"winner fields: \d\+\d != 3"):
        _ = TPMatch(pm1=pm1, pm2=pm2)


def test_winner_consistent_none(tpmatch1: TPMatch) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"winner": None})
    pm2 = tpmatch1.pm2.model_copy(update={"winner": 1})
    with pytest.raises(ValidationError, match=r"winner fields inconsistent: .+ vs. .+"):
        _ = TPMatch(pm1=pm1, pm2=pm2)


def test_status_finished(tpmatch1: TPMatch) -> None:
    first = tpmatch1.pm1.model_copy(update={"winner": 1})
    second = tpmatch1.pm2.model_copy(update={"winner": 2})
    m = TPMatch(pm1=first, pm2=second)
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
    tpmatch1: TPMatch,
    updict_1: dict[str, Any],
    updict_2: dict[str, Any] | None,
    expected: ContextManager[None],
) -> None:
    first = tpmatch1.pm1.model_copy(update=updict_1)
    second = tpmatch1.pm2.model_copy(update=updict_1 if updict_2 is None else updict_2)

    with expected as e:
        m = TPMatch(pm1=first, pm2=second)
        assert m.status == e


def test_set_entry_bye_status_override(tpmatch1: TPMatch) -> None:
    tpmatch1.set_slots(
        Slot(content=Bye()), Slot(content=cast(TPEntry, tpmatch1.pm2.entry))
    )
    assert tpmatch1.status == MatchStatus.READY


def test_set_entry_knonwn_status_override(tpmatch1: TPMatch) -> None:
    tpmatch1.set_slots(
        Slot(content=Unknown()), Slot(content=cast(TPEntry, tpmatch1.pm2.entry))
    )
    assert tpmatch1.status == MatchStatus.PENDING


def test_lower_planning_playermatch_first(
    pm1: TPPlayerMatch, TPMatchFactory: TPMatchFactoryType, tpentry2: TPEntry
) -> None:
    m = TPMatchFactory(pm1, tpentry2, lldiff=4)
    m = TPMatch(pm1=m.pm2, pm2=m.pm1)  # reversed on purpose
    assert m.pm1 == pm1


def test_winner(tpmatch1: TPMatch) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"winner": 1})
    pm2 = tpmatch1.pm2.model_copy(update={"winner": 2})
    m = TPMatch(pm1=pm1, pm2=pm2)
    assert m.winner == pm1.entry


def test_winner_pms_reversed(tpmatch1: TPMatch) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"winner": 1})
    pm2 = tpmatch1.pm2.model_copy(update={"winner": 2})
    m = TPMatch(pm1=pm2, pm2=pm1)
    assert m.winner == pm1.entry
