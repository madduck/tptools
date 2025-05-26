from collections.abc import Callable, Iterable
from typing import Any, Self, cast

type CmpCallableType = Callable[[Any, Any], bool]
type FieldCallableType[T] = Callable[[T], Any]
type FieldsType[T] = Iterable[str | FieldCallableType[T]]
type CmpFieldsType[T] = FieldsType[T] | None
type EqFieldsType[T] = FieldsType[T] | None
type FieldsSrcType[T] = Iterable[FieldsType[T] | None]


class ComparableMixin:
    __cmp_fields__: CmpFieldsType[Self] = None
    __eq_fields__: EqFieldsType[Self] | None = None
    __none_sorts_last__: bool | None = None

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs

    def _cmp(
        self,
        other: Any,
        meth: CmpCallableType,
        fieldssrcs: FieldsSrcType[Self],
    ) -> bool:
        try:
            for f in next(f for f in fieldssrcs if f is not None):
                a = f(self) if callable(f) else getattr(self, f)
                b = f(other) if callable(f) else getattr(other, f)
                if a == b:
                    continue

                return meth(a, b)

            else:
                try:
                    _ = a, b  # pyright: ignore[reportPossiblyUnboundVariable]
                except UnboundLocalError:
                    return meth(None, None)
                else:
                    return meth(a, b)  # pyright: ignore[reportPossiblyUnboundVariable]

        except AttributeError as err:
            raise NotImplementedError(
                f"Instances of types {type(self).__qualname__} "
                f"and {type(other).__qualname__} are not comparable."
            ) from err

    def __lt__(self, other: Any) -> bool:
        def lt(a: Any, b: Any) -> bool:
            if a is None and b is None:
                return False
            elif (a is not None and b is not None) or self.__none_sorts_last__ is None:
                return cast(bool, a < b)
            else:
                return (a is None) ^ (self.__none_sorts_last__ is True)

        return self._cmp(
            other,
            lt,
            (self.__cmp_fields__, self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __gt__(self, other: Any) -> bool:
        def gt(a: Any, b: Any) -> bool:
            if a is None and b is None:
                return False
            elif (a is not None and b is not None) or self.__none_sorts_last__ is None:
                return cast(bool, a > b)
            else:
                return (a is None) ^ (self.__none_sorts_last__ is False)

        return self._cmp(
            other,
            gt,
            (self.__cmp_fields__, self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __le__(self, other: Any) -> bool:
        def le(a: Any, b: Any) -> bool:
            if a is None and b is None:
                return True
            elif (a is not None and b is not None) or self.__none_sorts_last__ is None:
                return cast(bool, a <= b)
            else:
                return (a is None) ^ (self.__none_sorts_last__ is True)

        return self._cmp(
            other,
            le,
            (self.__cmp_fields__, self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __ge__(self, other: Any) -> bool:
        def ge(a: Any, b: Any) -> bool:
            if a is None and b is None:
                return True
            elif (a is not None and b is not None) or self.__none_sorts_last__ is None:
                return cast(bool, a >= b)
            else:
                return (a is None) ^ (self.__none_sorts_last__ is False)

        return self._cmp(
            other,
            ge,
            (self.__cmp_fields__, self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        return self._cmp(
            other,
            lambda a, b: a == b,
            (self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __ne__(self, other: Any) -> bool:
        if other is None:
            return True
        return self._cmp(
            other,
            lambda a, b: a != b,
            (self.__eq_fields__, tuple(self.__dict__.keys())),  # type: ignore[arg-type]
        )

    def __hash__(self) -> int:
        return hash(
            tuple(
                f(self) if callable(f) else getattr(self, f)
                for f in cast(
                    FieldsType["ComparableMixin"],
                    self.__eq_fields__ or self.__dict__.keys(),
                )
            )
        )
