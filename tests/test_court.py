from collections.abc import Mapping

import pytest

from tptools.sqlmodels import TPCourt


def test_repr(tpcourt1: TPCourt) -> None:
    assert repr(tpcourt1) == "TPCourt(id=1, name='C01', location.name='Sports4You')"


def test_eq(tpcourt1: TPCourt, tpcourt1copy: TPCourt) -> None:
    assert tpcourt1 == tpcourt1copy


def test_ne(tpcourt1: TPCourt, tpcourt2: TPCourt) -> None:
    assert tpcourt1 != tpcourt2


def test_lt(tpcourt1: TPCourt, tpcourt2: TPCourt) -> None:
    assert tpcourt1 < tpcourt2


def test_le(tpcourt1: TPCourt, tpcourt2: TPCourt, tpcourt1copy: TPCourt) -> None:
    assert tpcourt1 <= tpcourt2 and tpcourt1 <= tpcourt1copy


def test_gt(tpcourt1: TPCourt, tpcourt2: TPCourt) -> None:
    assert tpcourt2 > tpcourt1


def test_ge(tpcourt1: TPCourt, tpcourt2: TPCourt, tpcourt1copy: TPCourt) -> None:
    assert tpcourt2 >= tpcourt1 and tpcourt1 >= tpcourt1copy


def test_no_cmp(tpcourt1: TPCourt) -> None:
    with pytest.raises(NotImplementedError):
        assert tpcourt1 == object()


def test_lt_sortorder(tpcourt1: TPCourt, tpcourt2: TPCourt) -> None:
    tpcourt1.sortorder = 3
    tpcourt2.sortorder = 2
    tpcourt2.location = tpcourt1.location
    assert tpcourt2 < tpcourt1


def test_model_dump_has_location(tpcourt1: TPCourt) -> None:
    md = tpcourt1.model_dump()
    assert "locationid_" not in md
    assert isinstance(md.get("location"), Mapping)
