from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyBase(ABC):
    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def params(self) -> dict[str, Any]:
        return asdict(self)
