import asyncio
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Callable

import click
from click_async_plugins import CliContext as _CliContext
from fastapi import FastAPI
from httpx import URL, AsyncClient, HTTPError, InvalidURL
from httpx import codes as status_codes
from pydantic import BaseModel

from ..filewatcher import FileWatcher

logger = logging.getLogger(__name__)


@dataclass()
class CliContext(_CliContext):
    api: FastAPI
    watcher: FileWatcher | None = None

    def __hash__(self) -> int:
        return hash(self.api)


pass_clictx = click.make_pass_decorator(CliContext)


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


class PostData[T: BaseModel](BaseModel):
    cookie: int
    data: T


async def post_data[T: BaseModel](
    url: URL,
    data: PostData[T],
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
