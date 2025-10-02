from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import SerializationInfo, model_serializer

from tptools import Court


class SquoreCourt(Court):
    NAMEPOLICY: ClassVar[str] = "courtnamepolicy"

    @model_serializer(mode="plain")
    def apply_namepolicy(self, info: SerializationInfo) -> str:
        policy = self.get_policy_from_info(info, self.NAMEPOLICY, str)
        return policy(self)

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> str: ...  # type: ignore[override]
