from typing import TYPE_CHECKING, Any, ClassVar, TypedDict

from pydantic import (
    SerializationInfo,
    TypeAdapter,
    model_serializer,
)

from tptools import Draw
from tptools.namepolicy import DrawNamePolicy


class SquoreDrawStruct(TypedDict):
    event: str
    stage: str
    name: str


SquoreDrawStructValidator = TypeAdapter(SquoreDrawStruct)


class SquoreDrawNamePolicy(DrawNamePolicy):
    def __call__(self, draw: Draw) -> SquoreDrawStruct:  # type: ignore[override]
        return SquoreDrawStructValidator.validate_python(
            {
                "event": draw.stage.event.name,
                "stage": draw.stage.name,
                "name": draw.name,
            }
        )


class SquoreDraw(Draw):
    NAMEPOLICY: ClassVar[str] = "drawnamepolicy"

    @model_serializer(mode="plain")
    def apply_namepolicy(self, info: SerializationInfo) -> SquoreDrawStruct | str:
        policy = self.get_policy_from_info(
            info, self.NAMEPOLICY, SquoreDrawNamePolicy()
        )
        return policy(self)

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> SquoreDrawStruct | str: ...  # type: ignore[override]
