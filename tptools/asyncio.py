import asyncio
import functools
from collections.abc import Callable, Coroutine
from typing import Any, Never, Protocol, cast, runtime_checkable

type LoopFactoryType = Callable[[], asyncio.AbstractEventLoop]


@runtime_checkable
class AsyncRunner[T](Protocol):
    @staticmethod
    def __call__(  # pragma: no cover
        main: Coroutine[Any, Any, T],
        *,
        loop_factory: LoopFactoryType | None = asyncio.new_event_loop,
        debug: bool | None = None,
    ) -> T: ...


def _make_wrapper[T, **P](
    *,
    runner: AsyncRunner[T] = asyncio.run,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def outer(fn: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(fn)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return runner(cast(Coroutine[Any, Any, Never], fn(*args, **kwargs)))

        return inner

    return outer


def asyncio_run[T, **P](
    *args: Callable[P, T], **kwargs: dict[str, Callable[P, T]]
) -> Callable[[Callable[P, T]], Callable[P, T] | Never] | Callable[P, T]:
    if callable(runner := kwargs.get("runner")):

        def wrapper(fn: Callable[P, T]) -> Callable[P, T]:  # type: ignore[unreachable]
            return _make_wrapper(runner=runner)(fn)

        return wrapper

    else:
        return _make_wrapper()(args[0])  # type: ignore[arg-type]
