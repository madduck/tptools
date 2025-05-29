from collections.abc import Callable
from typing import Any

import pytest

from tptools.mixins import StrMixin


class Base:
    def __str__(self) -> str:
        return "base"


class DummyClass(StrMixin, Base):
    def __init__(
        self, string: str = "string", integer: int = 42, **kwargs: Any
    ) -> None:
        super().__init__()
        self.string = string
        self.integer = integer
        self.__dict__.update(kwargs)


def test_str_base() -> None:
    assert str(DummyClass()) == "base"


type DummyClassType = type[DummyClass]
type DummyClassFactoryType = Callable[..., DummyClassType]


@pytest.fixture
def DummyClassFactory() -> DummyClassFactoryType:
    def class_maker(
        *, strtemplate: str | None = None, **classvars: Any
    ) -> DummyClassType:
        DummyClass.__str_template__ = strtemplate
        for k, v in classvars.items():
            setattr(DummyClass, k, v)
        return DummyClass

    return class_maker


type DataType = dict[str, int]


def test_str_static(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(strtemplate="static")
    assert str(DummyClass()) == "static"


def test_str_instance_attr(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(strtemplate="+{self.string}+")
    assert str(DummyClass(string="foo")) == "+foo+"


def test_str_class_attr(DummyClassFactory: DummyClassFactoryType) -> None:
    DummyClass = DummyClassFactory(strtemplate="+{self.classvar}+", classvar="foo")
    assert str(DummyClass()) == "+foo+"
