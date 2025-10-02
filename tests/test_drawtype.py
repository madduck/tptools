import pytest

from tptools.drawtype import DrawType

GROUP_TYPES = dict.fromkeys(DrawType, False)
GROUP_TYPES.update(
    dict.fromkeys(
        (
            DrawType.GROUP,
            # DrawType.RRHOMEAWAY,
        ),
        True,
    )
)


@pytest.mark.parametrize("type, exp", [(k, v) for k, v in GROUP_TYPES.items()])
def test_group_property(type: DrawType, exp: bool) -> None:
    assert DrawType(type).is_group_draw is exp
    assert DrawType(type).is_tree_draw is not exp


@pytest.mark.parametrize("type, exp", [(k, not v) for k, v in GROUP_TYPES.items()])
def test_tree_property(type: DrawType, exp: bool) -> None:
    assert DrawType(type).is_tree_draw is exp
    assert DrawType(type).is_group_draw is not exp
