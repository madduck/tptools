import pytest

from tptools.sqlmodels import TPSetting


@pytest.fixture
def setting1() -> TPSetting:
    return TPSetting(id=1, name="setting1", value="value")


@pytest.fixture
def setting2() -> TPSetting:
    return TPSetting(id=2, name="setting2", value=None)


setting1copy = setting1


def test_repr(setting1: TPSetting) -> None:
    assert repr(setting1) == "TPSetting(id=1, name='setting1', value='value')"


def test_repr_none(setting2: TPSetting) -> None:
    assert repr(setting2) == "TPSetting(id=2, name='setting2', value=None)"


def test_str(setting1: TPSetting) -> None:
    assert str(setting1) == "setting1='value'"


def test_str_none(setting2: TPSetting) -> None:
    assert str(setting2) == "setting2=None"


def test_eq(setting1: TPSetting, setting1copy: TPSetting) -> None:
    assert setting1 == setting1copy


def test_ne(setting1: TPSetting, setting2: TPSetting) -> None:
    assert setting2 != setting1


def test_lt(setting1: TPSetting, setting2: TPSetting) -> None:
    assert setting1 < setting2


def test_le(setting1: TPSetting, setting2: TPSetting, setting1copy: TPSetting) -> None:
    assert setting1 <= setting2 and setting1 <= setting1copy


def test_gt(setting1: TPSetting, setting2: TPSetting) -> None:
    assert setting2 > setting1


def test_ge(setting1: TPSetting, setting2: TPSetting, setting1copy: TPSetting) -> None:
    assert setting2 >= setting1 and setting1 >= setting1copy


def test_no_cmp(setting1: TPSetting) -> None:
    with pytest.raises(NotImplementedError):
        assert setting1 == object()
