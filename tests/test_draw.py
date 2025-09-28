from collections.abc import Mapping
from typing import cast

import pytest

from tptools.drawtype import DrawType
from tptools.sqlmodels import TPDraw, TPStage


def test_stage_has_id(draw1: TPDraw) -> None:
    assert draw1.stageid_


def test_repr(draw1: TPDraw) -> None:
    assert (
        repr(draw1)
        == "TPDraw(id=1, name='Baum', stage.name='Qual', type=MONRAD, size=8)"
    )


def test_str(draw1: TPDraw) -> None:
    assert str(draw1) == "Baum, Qual, Herren 1"


def test_eq(draw1: TPDraw, draw1copy: TPDraw) -> None:
    assert draw1 == draw1copy


def test_ne(draw1: TPDraw, draw2: TPDraw) -> None:
    assert draw1 != draw2


def test_lt(draw1: TPDraw, draw2: TPDraw) -> None:
    assert draw2 < draw1


def test_le(draw1: TPDraw, draw2: TPDraw, draw1copy: TPDraw) -> None:
    assert draw2 <= draw1 and draw1 <= draw1copy


def test_gt(draw1: TPDraw, draw2: TPDraw) -> None:
    assert draw1 > draw2


def test_ge(draw1: TPDraw, draw2: TPDraw, draw1copy: TPDraw) -> None:
    assert draw1 >= draw2 and draw1 >= draw1copy


def test_no_cmp(draw1: TPDraw) -> None:
    with pytest.raises(NotImplementedError):
        assert draw1 == object()


def test_drawtype_enum(draw1: TPDraw) -> None:
    assert draw1.type == DrawType.MONRAD
    assert type(draw1.type) is type(DrawType.MONRAD)


def test_drawtype_from_int(stage1: TPStage) -> None:
    draw = TPDraw.model_validate(
        {
            "id": 1,
            "name": "name",
            "type": cast(DrawType, int(DrawType.MONRAD)),
            "size": 8,
            "stage": stage1,
        }
    )
    assert draw.type == DrawType.MONRAD


def test_draw_model_dump_has_stage(draw1: TPDraw) -> None:
    md = draw1.model_dump()
    assert "stageid_" not in md
    assert isinstance(md.get("stage"), Mapping)
