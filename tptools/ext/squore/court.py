from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import model_serializer

from tptools import Court


class SquoreCourt(Court):
    NAMEPOLICY: ClassVar[str] = "courtnamepolicy"

    @model_serializer(mode="plain")
    def return_just_id(self) -> int:
        return self.id

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> int: ...  # type: ignore[override]
