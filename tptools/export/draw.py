import logging
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
)

from pydantic import (
    BaseModel,
    model_serializer,
)

from tptools.mixins import ReprMixin, StrMixin
from tptools.models import Draw as TPDraw

logger = logging.getLogger(__name__)


class DrawStruct(TypedDict, total=True):
    name: str
    stage: str
    event: str


class Draw(ReprMixin, StrMixin, BaseModel):
    tpdraw: TPDraw

    @property
    def id(self) -> int:
        return self.tpdraw.id

    @model_serializer(mode="plain")
    def _model_serializer(
        self,
    ) -> DrawStruct:
        draw = self.tpdraw
        return {
            "name": draw.name,
            "stage": draw.stage.name,
            "event": draw.stage.event.name,
        }

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> DrawStruct: ...

    __repr_fields__ = ("tpdraw",)
    __str_template__ = "{self.tpdraw}"
