import pytest

from tptools.slot import Bye, Playceholder, Slot, SlotContent, SlotType, Unknown
from tptools.sqlmodels import TPEntry


def test_slot_type_invalid() -> None:
    with pytest.raises(ValueError, match="is not valid for Slot"):
        _ = SlotType.from_instance(object())  # type: ignore[arg-type]


@pytest.mark.parametrize("kls", [TPEntry, Bye, Unknown, Playceholder])
def test_slot_type_value(kls: type[TPEntry | SlotContent]) -> None:
    assert SlotType.from_class(kls).value == kls.__name__


@pytest.mark.parametrize("kls", [TPEntry, Bye, Unknown, Playceholder])
def test_slot_type_repr(kls: type[TPEntry | SlotContent]) -> None:
    assert repr(SlotType.from_class(kls)) == f"SlotType({kls.__name__})"


def test_bye_slottype(bye: Bye) -> None:
    s = SlotType.from_instance(bye)
    assert s == SlotType.BYE


def test_bye_repr(bye: Bye) -> None:
    assert repr(bye) == "Bye()"


def test_bye_str(bye: Bye) -> None:
    assert str(bye) == "Bye"


def test_playceholder_slottype(winner: Playceholder) -> None:
    s = SlotType.from_instance(winner)
    assert s == SlotType.PLAYCEHOLDER


def test_playceholder_repr_winner(winner: Playceholder) -> None:
    assert repr(winner) == "Playceholder(matchnr=14, winner=True)"


def test_playceholder_str_winner(winner: Playceholder) -> None:
    assert str(winner) == "Winner of match #14"


def test_playceholder_repr_loser(loser: Playceholder) -> None:
    assert repr(loser) == "Playceholder(matchnr=14, winner=False)"


def test_playceholder_str_loser(loser: Playceholder) -> None:
    assert str(loser) == "Loser of match #14"


def test_unknown_slottype(unknown: Unknown) -> None:
    s = SlotType.from_instance(unknown)
    assert s == SlotType.UNKNOWN


def test_unknown_repr(unknown: Unknown) -> None:
    assert repr(unknown) == "Unknown()"


def test_unknown_str(unknown: Unknown) -> None:
    assert str(unknown) == "Unknown"


def test_entry_slottype(tpentry1: TPEntry) -> None:
    s = SlotType.from_instance(tpentry1)
    assert s == SlotType.ENTRY


def test_slot_default_is_unknown() -> None:
    assert Slot().model_dump() == "Unknown"


def test_slot_unknown(unknown: Unknown) -> None:
    assert Slot(content=unknown).model_dump() == "Unknown"


def test_slot_unknown_id(unknown: Unknown) -> None:
    assert Slot(content=unknown).id is None


def test_slot_bye(bye: Bye) -> None:
    assert Slot(content=bye).model_dump() == "Bye"


def test_slot_bye_id(bye: Unknown) -> None:
    assert Slot(content=bye).id is None


def test_slot_playceholder(winner: Playceholder) -> None:
    assert Slot(content=winner).model_dump() == "Winner of match #14"


def test_slot_playceholder_id(winner: Playceholder) -> None:
    assert Slot(content=winner).id is None


def test_slot_entry(tpentry1: TPEntry) -> None:
    assert Slot(content=tpentry1).model_dump() == tpentry1.model_dump()


def test_slot_entry_id(tpentry1: TPEntry) -> None:
    assert Slot(content=tpentry1).id == tpentry1.id
