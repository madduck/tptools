from collections.abc import Mapping
from types import NoneType

import pytest

from tptools.sqlmodels import TPEntry, TPEvent, TPPlayer


def test_player1_has_id(tpentry1: TPEntry) -> None:
    assert tpentry1.player1


def test_player2_has_id(tpentry21: TPEntry) -> None:
    assert tpentry21.player2


def test_repr(tpentry1: TPEntry) -> None:
    assert repr(tpentry1) == (
        "TPEntry(id=1, event.name='Herren 1', player1.name='Martin Krafft')"
    )


def test_repr_double(tpentry12: TPEntry) -> None:
    assert repr(tpentry12) == (
        "TPEntry(id=12, event.name='Herren 1', "
        "player1.name='Martin Krafft', "
        "player2.name='Iddo Hoeve')"
    )


def test_str(tpentry1: TPEntry) -> None:
    assert str(tpentry1) == "Martin Krafft"


def test_double(tpentry12: TPEntry) -> None:
    assert str(tpentry12) == "Martin Krafft&Iddo Hoeve"


def test_eq(tpentry1: TPEntry, tpentry1copy: TPEntry) -> None:
    assert tpentry1 == tpentry1copy


def test_ne(tpentry1: TPEntry, tpentry2: TPEntry) -> None:
    assert tpentry1 != tpentry2


def test_lt(tpentry1: TPEntry, tpentry2: TPEntry) -> None:
    assert tpentry2 < tpentry1


def test_le(tpentry1: TPEntry, tpentry2: TPEntry, tpentry1copy: TPEntry) -> None:
    assert tpentry2 <= tpentry1 and tpentry1 <= tpentry1copy


def test_gt(tpentry1: TPEntry, tpentry2: TPEntry) -> None:
    assert tpentry1 > tpentry2


def test_ge(tpentry1: TPEntry, tpentry2: TPEntry, tpentry1copy: TPEntry) -> None:
    assert tpentry1 >= tpentry2 and tpentry1 >= tpentry1copy


def test_no_cmp(tpentry1: TPEntry) -> None:
    with pytest.raises(NotImplementedError):
        assert tpentry1 == object()


def test_players_must_differ(tpevent1: TPEvent, tpplayer1: TPPlayer) -> None:
    with pytest.raises(ValueError, match="player2 cannot be the same as player1"):
        TPEntry(id=123, event=tpevent1, player1=tpplayer1, player2=tpplayer1)


def test_eq_player_order_matters(tpentry12: TPEntry, tpentry21: TPEntry) -> None:
    assert tpentry12 != tpentry21


@pytest.mark.parametrize("rel", ["tpplayer1", "tpplayer2", "event"])
def test_model_dump_has_related_models(tpentry1: TPEntry, rel: str) -> None:
    md = tpentry1.model_dump()
    assert f"{rel}id_" not in md
    assert isinstance(md.get(rel), (Mapping, NoneType))
