from collections.abc import Callable
from contextlib import nullcontext
from typing import ContextManager

import pytest

from tptools.mixins import ComparableMixin


class DummyClass(ComparableMixin):
    def __init__(
        self, a: int | None = None, b: int | None = None, c: int | None = None
    ) -> None:
        self.a = a
        self.b = b
        self.c = c


type DummyClassType = type[DummyClass]
type DummyClassFactoryType = Callable[..., DummyClassType]


@pytest.fixture
def DummyClassFactory() -> DummyClassFactoryType:
    def class_maker(
        *,
        eqfields: list[str] | None = None,
        cmpfields: list[str] | None = None,
        none_sorts_last: bool | None = None,
    ) -> DummyClassType:
        DummyClass.__eq_fields__ = eqfields  # type: ignore[misc,unused-ignore]
        DummyClass.__cmp_fields__ = cmpfields  # type: ignore[misc,unused-ignore]
        DummyClass.__none_sorts_last__ = none_sorts_last  # type: ignore[misc,unused-ignore]
        return DummyClass

    return class_maker


type DataType = dict[str, int]


@pytest.fixture
def data() -> DataType:
    return {"a": 1, "b": 2, "c": 3}


def test_eq_default(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory()
    assert DummyClass(**data) == DummyClass(**data)


def test_cmp_default(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory()
    assert DummyClass(**data) < DummyClass(**data | {"b": data["b"] + 1})


def test_eq(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) == DummyClass(**data)


def test_ne(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) != DummyClass(**data | {"a": 2})


def test_reduced_eq(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b"])
    del data["c"]
    assert DummyClass(c=1, **data) == DummyClass(c=2, **data)


def test_reduced_ne(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b"])
    del data["c"]
    assert DummyClass(c=1, **data) != DummyClass(c=1, **data | {"a": 2})


def test_lt(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) < DummyClass(**{k: 2 * v for k, v in data.items()})


@pytest.mark.parametrize(
    "none_sorts_last, expectation",
    [
        (True, nullcontext(True)),
        (False, nullcontext(False)),
        (None, pytest.raises(TypeError)),
    ],
)
def test_lt_none(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
    expectation: ContextManager[None],
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    with expectation as e:
        assert (DummyClass(**data) < DummyClass(**dict.fromkeys(data.keys()))) is e


@pytest.mark.parametrize("none_sorts_last", [True, False, None])
def test_lt_between_nones(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    assert not (
        DummyClass(**dict.fromkeys(data.keys()))
        < DummyClass(**dict.fromkeys(data.keys()))
    )


def test_le(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) <= DummyClass(**data)
    assert DummyClass(**data) <= DummyClass(**{k: 2 * v for k, v in data.items()})


@pytest.mark.parametrize(
    "none_sorts_last, expectation",
    [
        (True, nullcontext(True)),
        (False, nullcontext(False)),
        (None, pytest.raises(TypeError)),
    ],
)
def test_le_none(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
    expectation: ContextManager[None],
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    with expectation as e:
        assert (DummyClass(**data) <= DummyClass(**dict.fromkeys(data.keys()))) is e


@pytest.mark.parametrize("none_sorts_last", [True, False, None])
def test_le_between_nones(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    assert DummyClass(**dict.fromkeys(data.keys())) <= DummyClass(
        **dict.fromkeys(data.keys())
    )


def test_gt(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) > DummyClass(**{k: v - 1 for k, v in data.items()})


@pytest.mark.parametrize(
    "none_sorts_last, expectation",
    [
        (True, nullcontext(False)),
        (False, nullcontext(True)),
        (None, pytest.raises(TypeError)),
    ],
)
def test_gt_none(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
    expectation: ContextManager[None],
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    with expectation as e:
        assert (DummyClass(**data) > DummyClass(**dict.fromkeys(data.keys()))) is e


@pytest.mark.parametrize("none_sorts_last", [True, False, None])
def test_gt_between_nones(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    assert not (
        DummyClass(**dict.fromkeys(data.keys()))
        > DummyClass(**dict.fromkeys(data.keys()))
    )


def test_ge(DummyClassFactory: DummyClassFactoryType, data: DataType) -> None:
    DummyClass = DummyClassFactory(eqfields=["a", "b", "c"])
    assert DummyClass(**data) >= DummyClass(**data)
    assert DummyClass(**data) >= DummyClass(**{k: v - 1 for k, v in data.items()})


@pytest.mark.parametrize(
    "none_sorts_last, expectation",
    [
        (True, nullcontext(False)),
        (False, nullcontext(True)),
        (None, pytest.raises(TypeError)),
    ],
)
def test_ge_none(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
    expectation: ContextManager[None],
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    with expectation as e:
        assert (DummyClass(**data) >= DummyClass(**dict.fromkeys(data.keys()))) is e


@pytest.mark.parametrize("none_sorts_last", [True, False, None])
def test_ge_between_nones(
    DummyClassFactory: DummyClassFactoryType,
    data: DataType,
    none_sorts_last: bool | None,
) -> None:
    DummyClass = DummyClassFactory(
        eqfields=["a", "b", "c"], none_sorts_last=none_sorts_last
    )
    assert DummyClass(**dict.fromkeys(data.keys())) >= DummyClass(
        **dict.fromkeys(data.keys())
    )


def test_lt_ordered(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(eqfields=["b", "a"])
    assert DummyClass(a=2, b=1) < DummyClass(a=1, b=2)


def test_cmp_overrides_eq(DummyClassFactory: DummyClassFactoryType) -> None:
    eqfields = ["a", "b"]
    DummyClass = DummyClassFactory(eqfields=eqfields, cmpfields=eqfields[::-1])
    assert DummyClass(a=2, b=1) < DummyClass(a=1, b=2)


def test_eq_with_none(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory()
    assert DummyClass() != None  # noqa: E711
    assert not DummyClass() == None  # noqa: E711


def test_no_cmp(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory()
    with pytest.raises(NotImplementedError):
        assert DummyClass() == object()


def test_callable_eq(DummyClassFactory: DummyClassFactoryType) -> None:
    def eqsum(self: "DummyClass") -> int:
        return (self.a or 0) + (self.b or 0) + (self.c or 0)

    DummyClass = DummyClassFactory(eqfields=(eqsum,))
    assert DummyClass(a=1, b=2, c=3) == DummyClass(a=3, b=2, c=1)


def test_callable_ne(DummyClassFactory: DummyClassFactoryType) -> None:
    def eqsum(self: "DummyClass") -> int:
        return (self.a or 0) + (self.b or 0) + (self.c or 0)

    DummyClass = DummyClassFactory(eqfields=(eqsum,))
    assert DummyClass(a=2, b=2, c=3) != DummyClass(a=3, b=2, c=1)


def test_callable_lt(DummyClassFactory: DummyClassFactoryType) -> None:
    def eqsum(self: "DummyClass") -> int:
        return self.a or 0

    DummyClass = DummyClassFactory(eqfields=(eqsum,))
    assert DummyClass(a=1) < DummyClass(a=2)


def test_hash(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(eqfields=["b", "a"])
    assert hash(DummyClass(a=1, b=2)) == hash(DummyClass(a=1, b=2))


def test_hash_different(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(eqfields=["b", "a"])
    assert hash(DummyClass(a=2, b=1)) != hash(DummyClass(a=1, b=2))


def test_callable_hash(DummyClassFactory: DummyClassFactoryType) -> None:
    def eqsum(self: "DummyClass") -> int:
        return (self.a or 0) + (self.b or 0) + (self.c or 0)

    DummyClass = DummyClassFactory(eqfields=(eqsum,))
    assert hash(DummyClass(a=1, b=2, c=3)) == hash(DummyClass(a=3, b=2, c=1))


def test_callable_hash_unequal(DummyClassFactory: DummyClassFactoryType) -> None:
    def eqsum(self: "DummyClass") -> int:
        return (self.a or 0) + (self.b or 0) + (self.c or 0)

    DummyClass = DummyClassFactory(eqfields=(eqsum,))
    assert hash(DummyClass(a=2, b=2, c=3)) != hash(DummyClass(a=3, b=2, c=1))


def test_cmp_no_fields(
    DummyClassFactory: DummyClassFactoryType, data: DataType
) -> None:
    DummyClass = DummyClassFactory(cmpfields=())
    assert DummyClass(**data) >= DummyClass(**data)


def test_cmp_fields_none(
    DummyClassFactory: DummyClassFactoryType, data: DataType
) -> None:
    DummyClass = DummyClassFactory(cmpfields=None)
    assert DummyClass(**data) >= DummyClass(**data)
