import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Any, Protocol, Self


@dataclass(frozen=True)
class PolicyBase(ABC):
    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def params(self) -> dict[str, Any]:
        return asdict(self)

    def with_(self, **updates: Any) -> Self:
        return replace(self, **updates)


class PolicyCallable[ReturnT](Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> ReturnT: ...


@dataclass
class RegexpSubstTuple:
    pattern: re.Pattern[str] | str
    repl: str | Callable[[re.Match[str]], str]
    count: int = 0
    flags: re.RegexFlag | int | None = None


@dataclass(frozen=True)
class NamePolicy(PolicyBase):
    regexps: list[RegexpSubstTuple] | None = None

    def _apply_regexps(self, instr: str) -> str:
        if self.regexps is None:
            return instr

        for regexp in self.regexps:
            instr = re.sub(
                regexp.pattern,
                regexp.repl,
                instr,
                count=regexp.count,
                flags=regexp.flags or 0,
            )
        return instr

    def params(self) -> dict[str, Any]:
        ret = super().params()
        del ret["regexps"]
        return ret
