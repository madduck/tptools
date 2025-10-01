# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from functools import singledispatchmethod
from typing import TYPE_CHECKING, Any, Never, Self, overload

from pydantic import BaseModel as PydanticBaseModel
from pydantic import SerializationInfo

from .mixins import ComparableMixin, ReprMixin, StrMixin
from .sqlmodels import TPModel

if TYPE_CHECKING:
    from .namepolicy.policybase import PolicyCallable
    from .paramsmodel import ParamsModel


class BaseModel[T: TPModel | None](
    ComparableMixin, ReprMixin, StrMixin, PydanticBaseModel
):
    @singledispatchmethod
    @classmethod
    def from_tp_model(cls, tpmodel: T) -> Self | Never:
        if tpmodel is None:  # pragma: nocover
            # thanks to singledispatch, we should never reach this
            raise NotImplementedError("No TPModel to instantiate from")
        return cls.model_validate(tpmodel.model_dump())

    @from_tp_model.register
    @classmethod
    def _(cls, _: None) -> Never:
        raise NotImplementedError("No TPModel to instantiate from")

    @overload
    @staticmethod
    def get_policy_from_info[PolicyT: PolicyCallable[Any]](
        info: SerializationInfo, name: str, default: PolicyT
    ) -> PolicyT: ...

    @overload
    @staticmethod
    def get_policy_from_info(
        info: SerializationInfo, name: str, default: None
    ) -> PolicyCallable[Any] | None: ...

    @staticmethod
    def get_policy_from_info(
        info: SerializationInfo, name: str, default: None | PolicyCallable[Any]
    ) -> PolicyCallable[Any] | None:
        ctx = info.context or {}
        return ctx.get(name) or default

    @overload
    @staticmethod
    def get_params_from_info(
        info: SerializationInfo, name: str, default: None
    ) -> ParamsModel | None: ...

    @overload
    @staticmethod
    def get_params_from_info[ParamsModelT](
        info: SerializationInfo, name: str, default: ParamsModelT
    ) -> ParamsModelT: ...

    @staticmethod
    def get_params_from_info[ParamsModelT](
        info: SerializationInfo, name: str, default: ParamsModelT | None
    ) -> ParamsModelT | None:
        ctx = info.context or {}
        return ctx.get(name) or default
