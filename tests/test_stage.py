from collections.abc import Mapping

import pytest

from tptools.sqlmodels import TPStage


def test_event_has_id(stage1: TPStage) -> None:
    assert stage1.eventid_


def test_repr(stage1: TPStage) -> None:
    assert repr(stage1) == "TPStage(id=1, name='Qual', event.name='Herren 1')"


def test_str(stage1: TPStage) -> None:
    assert str(stage1) == "Qual, Herren 1"


def test_eq(stage1: TPStage, stage1copy: TPStage) -> None:
    assert stage1 == stage1copy


def test_ne(stage1: TPStage, stage2: TPStage) -> None:
    assert stage1 != stage2


def test_lt(stage1: TPStage, stage2: TPStage) -> None:
    assert stage2 < stage1


def test_le(stage1: TPStage, stage2: TPStage, stage1copy: TPStage) -> None:
    assert stage2 <= stage1 and stage1 <= stage1copy


def test_gt(stage1: TPStage, stage2: TPStage) -> None:
    assert stage1 > stage2


def test_ge(stage1: TPStage, stage2: TPStage, stage1copy: TPStage) -> None:
    assert stage1 >= stage2 and stage1 >= stage1copy


def test_no_cmp(stage1: TPStage) -> None:
    with pytest.raises(NotImplementedError):
        assert stage1 == object()


def test_stage_model_dump_has_event(stage1: TPStage) -> None:
    md = stage1.model_dump()
    assert "eventid_" not in md
    assert isinstance(md.get("event"), Mapping)
