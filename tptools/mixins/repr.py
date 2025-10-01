from collections.abc import Callable, Iterable
from typing import Any

type ReprFieldCallableType = Callable[[Any], Any]
type ReprFieldTupleType = (
    tuple[str, ReprFieldCallableType, bool] | tuple[str, ReprFieldCallableType]
)
type FieldsType = Iterable[str | ReprFieldTupleType]
type ReprFieldsType = FieldsType | None


class ReprMixin:
    __repr_fields__: ReprFieldsType = None

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init_subclass__(*args, **kwargs)

    def _class_name(self) -> str:
        return self.__class__.__name__

    def _class_template(self) -> str:
        return self._class_name() + "({})"

    def __repr__(self) -> str:
        fields = getattr(self, "__repr_fields__", None)
        if fields is None:
            return super().__repr__()
        else:
            pairs = []
            for f in fields:
                if isinstance(f, (tuple, list)):
                    dorepr = True
                    if len(f) == 3:
                        name, fn, dorepr = f
                    else:
                        name, fn = f

                    value = fn(self)
                    pairs.append(
                        (name, repr(value) if (dorepr or value is None) else str(value))
                    )
                    continue

                obj = self
                path = []
                opt = False  # "obj is possibly unbound" except it's not…
                # … split always returns len>0
                for attrname in f.split("."):
                    opt = False
                    if attrname.endswith("?"):
                        attrname = attrname[:-1]
                        opt = True

                    path.append(attrname)

                    if (obj := getattr(obj, attrname)) is None and opt:
                        break

                if obj is None and opt:  # type: ignore[unreachable]
                    # this is not unreachable, as mypy claims. opt may well be True,
                    # because the for loop above will always be entered, but mypy
                    # seems to think it might be skipped.
                    # But: len (anystring'.split('anything')) > 0
                    continue  # type: ignore[unreachable]

                pairs.append((".".join(path), repr(obj)))

            return self._class_template().format(
                ", ".join(["=".join(p) for p in pairs])
            )
