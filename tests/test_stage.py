from collections.abc import Mapping

import pytest

from tptools.sqlmodels import TPStage


def test_event_has_id(tpstage1: TPStage) -> None:
    assert tpstage1.eventid_


def test_repr(tpstage1: TPStage) -> None:
    assert repr(tpstage1) == "TPStage(id=1, name='Qual', event.name='Herren 1')"


def test_str(tpstage1: TPStage) -> None:
    assert str(tpstage1) == "Qual, Herren 1"


def test_eq(tpstage1: TPStage, tpstage1copy: TPStage) -> None:
    assert tpstage1 == tpstage1copy


def test_ne(tpstage1: TPStage, tpstage2: TPStage) -> None:
    assert tpstage1 != tpstage2


def test_lt(tpstage1: TPStage, tpstage2: TPStage) -> None:
    assert tpstage2 < tpstage1


def test_le(tpstage1: TPStage, tpstage2: TPStage, tpstage1copy: TPStage) -> None:
    assert tpstage2 <= tpstage1 and tpstage1 <= tpstage1copy


def test_gt(tpstage1: TPStage, tpstage2: TPStage) -> None:
    assert tpstage1 > tpstage2


def test_ge(tpstage1: TPStage, tpstage2: TPStage, tpstage1copy: TPStage) -> None:
    assert tpstage1 >= tpstage2 and tpstage1 >= tpstage1copy


def test_no_cmp(tpstage1: TPStage) -> None:
    with pytest.raises(NotImplementedError):
        assert tpstage1 == object()


def test_stage_model_dump_has_event(tpstage1: TPStage) -> None:
    md = tpstage1.model_dump()
    assert "eventid_" not in md
    assert isinstance(md.get("event"), Mapping)
