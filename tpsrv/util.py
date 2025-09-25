# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from dataclasses import dataclass
from json import JSONDecodeError
from typing import AsyncGenerator, Callable

import click
from click_async_plugins import ITC
from fastapi import FastAPI
from httpx import URL, AsyncClient, HTTPError, InvalidURL
from httpx import codes as status_codes
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass()
class TpsrvContext:
    api: FastAPI
    itc: ITC


pass_tpsrv = click.make_pass_decorator(TpsrvContext)


def validate_urls(
    ctx: click.Context,
    param: str,
    value: tuple[str | None],
) -> list[URL]:
    _ = ctx, param
    ret = []
    for urlstr in value:
        if urlstr is None:
            continue

        try:
            url = URL(urlstr)

        except TypeError as err:
            raise click.BadParameter(
                f"URL must be a string, not '{type(urlstr).__name__}': {value}"
            ) from err

        except InvalidURL as err:  # pragma: nocover TODO: how do I test for this?
            raise click.BadParameter(f"{urlstr} is invalid: {err}") from err

        else:
            if not url.is_absolute_url:
                raise click.BadParameter(f"URL is not absolute: {urlstr}")
            ret.append(url)

    return ret


async def post_data(
    url: URL,
    data: BaseModel,
    *,
    retries: int = 3,
    sleep: float = 1,
    to_json_fn: Callable[..., str] | None = None,
) -> None:
    to_json_fn = to_json_fn or type(data).model_dump_json
    logger.debug(f"Posting '{data}' to {url}")
    while True:
        try:
            async with AsyncClient() as client:
                json = to_json_fn(data)
                resp = await client.post(
                    url, content=json, headers={"Content-Type": "application/json"}
                )

                try:
                    rt = resp.json()
                except JSONDecodeError:
                    rt = {}

                if resp.status_code == status_codes.OK:
                    logger.info(
                        f"Posted '{data}' to {url} "
                        f"({len(resp.request.content)} bytes): {rt}"
                    )

                else:
                    logger.error(
                        f"Posting '{data}' to {url} resulted "
                        f"in status code {resp.status_code}, {resp.reason_phrase}: "
                        f"{rt}"
                    )

                break

        except HTTPError as err:
            if retries > 0:
                retries -= 1
                logger.warning(f"Problem posting to {url}: {err}, retrying…")
                await asyncio.sleep(sleep)
                continue

            else:
                logger.error(f"Giving up posting to {url}: {err}")
                break


async def react_to_data_update[T](
    updates_gen: AsyncGenerator[T],
    *,
    callback: Callable[[T], Coroutine[None, None, None]],
) -> None:
    try:
        async for update in updates_gen:
            if update is not None:
                await callback(update)

    except asyncio.CancelledError:
        pass
