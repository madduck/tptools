import logging
from typing import (
    TYPE_CHECKING,
    Any,
)

from pydantic import (
    BaseModel,
    SerializationInfo,
    model_serializer,
)

from tptools.mixins import ReprMixin, StrMixin
from tptools.mixins.comparable import ComparableMixin
from tptools.namepolicy import (
    CourtNamePolicy,
)
from tptools.sqlmodels import Court as TPCourt
from tptools.sqlmodels import Location

logger = logging.getLogger(__name__)


class Court(ReprMixin, StrMixin, ComparableMixin, BaseModel):
    tpcourt: TPCourt

    @property
    def id(self) -> int:
        return self.tpcourt.id

    @property
    def name(self) -> str:
        return self.tpcourt.name

    @property
    def location(self) -> Location:
        return self.tpcourt.location

    @model_serializer(mode="plain")
    def _model_serializer(
        self,
        info: SerializationInfo,
    ) -> str | None:
        context = info.context or {}
        courtnamepolicy = context.get("courtnamepolicy") or CourtNamePolicy()
        return courtnamepolicy(self.tpcourt)

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> str | None: ...

    __repr_fields__ = ("tpcourt",)
    __str_template__ = "{self.tpcourt}"
    __eq_fields__ = ("tpcourt",)
