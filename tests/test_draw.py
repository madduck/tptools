import pytest

from tptools import Draw
from tptools.draw import Event, InvalidDrawType
from tptools.sqlmodels import TPEvent


def test_repr(draw1: Draw) -> None:
    assert (
        repr(draw1) == "Draw(id=1, name='Baum', stage.name='Qual', type=MONRAD, size=8)"
    )


def test_event_repr_noabbr(tpevent1: TPEvent) -> None:
    event = Event.from_tp_model(tpevent1.model_copy(update={"abbreviation": None}))
    assert repr(event) == "Event(id=1, name='Herren 1', gender=2)"


def test_event_repr(tpevent1: TPEvent) -> None:
    event = Event.from_tp_model(tpevent1)
    assert repr(event) == "Event(id=1, name='H1', gender=2)"


def test_str(draw1: Draw) -> None:
    assert str(draw1) == "Baum, Qual, Herren 1"


def test_cmp_eq(draw1: Draw, draw1copy: Draw) -> None:
    assert draw1 == draw1copy


def test_cmp_ne(draw1: Draw, draw2: Draw) -> None:
    assert draw1 != draw2


def test_cmp_lt(draw1: Draw, draw2: Draw) -> None:
    assert draw2 < draw1


def test_cmp_le(draw1: Draw, draw1copy: Draw, draw2: Draw) -> None:
    assert draw2 < draw1 and draw1 <= draw1copy


def test_cmp_gt(draw1: Draw, draw2: Draw) -> None:
    assert draw1 > draw2


def test_cmp_ge(draw1: Draw, draw1copy: Draw, draw2: Draw) -> None:
    assert draw1 > draw2 and draw1 >= draw1copy


def test_invalid_draw_exception() -> None:
    with pytest.raises(InvalidDrawType, match="Unable to handle draw type with ID 42"):
        raise InvalidDrawType(42)
