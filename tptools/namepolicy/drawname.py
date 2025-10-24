from dataclasses import dataclass
from typing import overload

from ..draw import Draw
from ..paramsmodel import ParamsModel
from .policybase import NamePolicy


class DrawNamePolicyParams(ParamsModel):
    only_show_event: bool = False


# TODO: remove redundancy between these two classes
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class DrawNamePolicy(NamePolicy):
    only_show_event: bool = False

    @overload
    def __call__(self, draw: Draw) -> str: ...

    @overload
    def __call__(self, draw: None) -> None: ...

    def __call__(self, draw: Draw | None) -> str | None:
        if draw is None:
            return None

        text = str(draw.stage.event) if self.only_show_event else str(draw)
        return self._apply_regexps(text)
