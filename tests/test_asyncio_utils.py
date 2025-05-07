import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from pytest_mock import MockerFixture

from tptools.asyncio import asyncio_run


def test_run_decorator() -> None:
    async def coro() -> None:
        pass

    main = asyncio_run(coro)

    assert main is not coro
    assert isinstance(main, type(coro))
    assert callable(main)
    assert not asyncio.iscoroutine(main)


@pytest.mark.asyncio
async def test_run_decorator_with_runner(mocker: MockerFixture) -> None:
    async def coro() -> None:
        pass

    runstub = mocker.stub("runner")

    def sideeffect(coro: Coroutine[Any, Any, Any]) -> None:
        asyncio.create_task(coro)

    runstub.side_effect = sideeffect
    main = asyncio_run(runner=runstub)(coro)  # type: ignore[arg-type,var-annotated]
    main()
    assert isinstance(runstub.call_args[0][0], Coroutine)
