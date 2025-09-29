from collections.abc import Mapping
from typing import cast

import pytest

from tptools.drawtype import DrawType
from tptools.sqlmodels import TPDraw, TPStage


def test_stage_has_id(tpdraw1: TPDraw) -> None:
    assert tpdraw1.stageid_


def test_repr(tpdraw1: TPDraw) -> None:
    assert (
        repr(tpdraw1)
        == "TPDraw(id=1, name='Baum', stage.name='Qual', type=MONRAD, size=8)"
    )


def test_str(tpdraw1: TPDraw) -> None:
    assert str(tpdraw1) == "Baum, Qual, Herren 1"


def test_eq(tpdraw1: TPDraw, tpdraw1copy: TPDraw) -> None:
    assert tpdraw1 == tpdraw1copy


def test_ne(tpdraw1: TPDraw, tpdraw2: TPDraw) -> None:
    assert tpdraw1 != tpdraw2


def test_lt(tpdraw1: TPDraw, tpdraw2: TPDraw) -> None:
    assert tpdraw2 < tpdraw1


def test_le(tpdraw1: TPDraw, tpdraw2: TPDraw, tpdraw1copy: TPDraw) -> None:
    assert tpdraw2 <= tpdraw1 and tpdraw1 <= tpdraw1copy


def test_gt(tpdraw1: TPDraw, tpdraw2: TPDraw) -> None:
    assert tpdraw1 > tpdraw2


def test_ge(tpdraw1: TPDraw, tpdraw2: TPDraw, tpdraw1copy: TPDraw) -> None:
    assert tpdraw1 >= tpdraw2 and tpdraw1 >= tpdraw1copy


def test_no_cmp(tpdraw1: TPDraw) -> None:
    with pytest.raises(NotImplementedError):
        assert tpdraw1 == object()


def test_drawtype_enum(tpdraw1: TPDraw) -> None:
    assert tpdraw1.type == DrawType.MONRAD
    assert type(tpdraw1.type) is type(DrawType.MONRAD)


def test_drawtype_from_int(tpstage1: TPStage) -> None:
    draw = TPDraw.model_validate(
        {
            "id": 1,
            "name": "name",
            "type": cast(DrawType, int(DrawType.MONRAD)),
            "size": 8,
            "stage": tpstage1,
        }
    )
    assert draw.type == DrawType.MONRAD


def test_draw_model_dump_has_stage(tpdraw1: TPDraw) -> None:
    md = tpdraw1.model_dump()
    assert "stageid_" not in md
    assert isinstance(md.get("stage"), Mapping)
