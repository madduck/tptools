from collections.abc import Mapping
from types import NoneType

import pytest

from tptools.sqlmodels import TPEntry, TPEvent, TPPlayer


def test_player1_has_id(entry1: TPEntry) -> None:
    assert entry1.player1


def test_player2_has_id(entry21: TPEntry) -> None:
    assert entry21.player2


def test_repr(entry1: TPEntry) -> None:
    assert repr(entry1) == (
        "TPEntry(id=1, event.name='Herren 1', player1.name='Martin Krafft')"
    )


def test_repr_double(entry12: TPEntry) -> None:
    assert repr(entry12) == (
        "TPEntry(id=12, event.name='Herren 1', "
        "player1.name='Martin Krafft', "
        "player2.name='Iddo Hoeve')"
    )


def test_str(entry1: TPEntry) -> None:
    assert str(entry1) == "Martin Krafft"


def test_double(entry12: TPEntry) -> None:
    assert str(entry12) == "Martin Krafft&Iddo Hoeve"


def test_eq(entry1: TPEntry, entry1copy: TPEntry) -> None:
    assert entry1 == entry1copy


def test_ne(entry1: TPEntry, entry2: TPEntry) -> None:
    assert entry1 != entry2


def test_lt(entry1: TPEntry, entry2: TPEntry) -> None:
    assert entry2 < entry1


def test_le(entry1: TPEntry, entry2: TPEntry, entry1copy: TPEntry) -> None:
    assert entry2 <= entry1 and entry1 <= entry1copy


def test_gt(entry1: TPEntry, entry2: TPEntry) -> None:
    assert entry1 > entry2


def test_ge(entry1: TPEntry, entry2: TPEntry, entry1copy: TPEntry) -> None:
    assert entry1 >= entry2 and entry1 >= entry1copy


def test_no_cmp(entry1: TPEntry) -> None:
    with pytest.raises(NotImplementedError):
        assert entry1 == object()


def test_players_must_differ(event1: TPEvent, player1: TPPlayer) -> None:
    with pytest.raises(ValueError, match="player2 cannot be the same as player1"):
        TPEntry(id=123, event=event1, player1=player1, player2=player1)


def test_eq_player_order_matters(entry12: TPEntry, entry21: TPEntry) -> None:
    assert entry12 != entry21


@pytest.mark.parametrize("rel", ["player1", "player2", "event"])
def test_model_dump_has_related_models(entry1: TPEntry, rel: str) -> None:
    md = entry1.model_dump()
    assert f"{rel}id_" not in md
    assert isinstance(md.get(rel), (Mapping, NoneType))
