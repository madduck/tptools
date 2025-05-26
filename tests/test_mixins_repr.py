from collections import namedtuple
from collections.abc import Callable
from typing import Any

import pytest

from tptools.mixins import ReprMixin


class Base:
    def __repr__(self) -> str:
        return "base"


class DummyClass(ReprMixin, Base):
    def __init__(
        self, string: str = "string", integer: int = 42, **kwargs: Any
    ) -> None:
        super().__init__()
        self.string = string
        self.integer = integer
        self.__dict__.update(kwargs)


def test_repr_base() -> None:
    assert repr(DummyClass()) == "base"


type DummyClassType = type[DummyClass]
type DummyClassFactoryType = Callable[..., DummyClassType]


@pytest.fixture
def DummyClassFactory() -> DummyClassFactoryType:
    def class_maker(*, reprfields: list[str] | None = None) -> DummyClassType:
        DummyClass.__repr_fields__ = reprfields
        return DummyClass

    return class_maker


type DataType = dict[str, int]


def test_repr_fields(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["string", "integer"])
    assert repr(DummyClass()) == "DummyClass(string='string', integer=42)"


def test_repr_fields_order(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["integer", "string"])
    assert repr(DummyClass()) == "DummyClass(integer=42, string='string')"


def test_repr_fields_empty(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=[])
    assert repr(DummyClass()) == "DummyClass()"


def test_repr_fields_inherit(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["integer", "string", "boolean"])
    assert (
        repr(DummyClass(boolean=True))
        == "DummyClass(integer=42, string='string', boolean=True)"
    )


def test_repr_fields_optional_none(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["optional?"])
    assert repr(DummyClass(optional=None)) == "DummyClass()"


def test_repr_fields_optional_not_none(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["optional?"])
    assert repr(DummyClass(optional=3.14)) == "DummyClass(optional=3.14)"


NameAttr = namedtuple("NameAttr", "name", defaults=(None,))


def test_repr_fields_attribute(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr.name"])
    assert (
        repr(DummyClass(attr=NameAttr(name="the name")))
        == "DummyClass(attr.name='the name')"
    )


def test_repr_fields_attribute_optional_value_none(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr.name"])
    assert repr(DummyClass(attr=NameAttr(name=None))) == "DummyClass(attr.name=None)"


def test_repr_fields_attribute_optional_value_notnone(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr?.name"])
    assert (
        repr(DummyClass(attr=NameAttr(name="the name")))
        == "DummyClass(attr.name='the name')"
    )


def test_repr_fields_attribute_optional_value_optional_notnone(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr?.name?"])
    assert (
        repr(DummyClass(attr=NameAttr(name="the name")))
        == "DummyClass(attr.name='the name')"
    )


def test_repr_fields_attribute_optional_value_optional_none(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr?.name?"])
    assert repr(DummyClass(attr=NameAttr(name=None))) == "DummyClass()"


def test_repr_fields_none_in_path(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr.name"])
    with pytest.raises(AttributeError, match="has no attribute 'name'"):
        assert repr(DummyClass(attr=None)) == "DummyClass()"


def test_repr_fields_none_in_path_optional(
    DummyClassFactory: DummyClassFactoryType,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr?.name"])
    assert repr(DummyClass(attr=None)) == "DummyClass()"


@pytest.mark.parametrize(
    "attrfn, norepr, value",
    [
        (lambda s: s.attr.upper(), True, "'SOMETHING'"),
        (lambda s: s.attr.upper(), False, "SOMETHING"),
        (lambda _: None, True, "None"),
        (lambda _: None, False, "None"),
        (lambda _: 42, False, "42"),
    ],
)
def test_repr_field_callable(
    DummyClassFactory: DummyClassFactoryType,
    attrfn: Callable[[DummyClass], str | None],
    norepr: bool,
    value: str,
) -> None:
    DummyClass = DummyClassFactory(reprfields=["attr", ("attrfn", attrfn, norepr)])
    assert (
        repr(DummyClass(attr="something"))
        == f"DummyClass(attr='something', attrfn={value})"
    )
