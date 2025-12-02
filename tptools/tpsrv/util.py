import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Annotated, Any, Callable, cast

import click
from click_async_plugins import CliContext as _CliContext
from fastapi import Depends, FastAPI, HTTPException
from fastapi.requests import HTTPConnection
from httpx import URL, AsyncClient, HTTPError, InvalidURL
from httpx import codes as status_codes
from pydantic import BaseModel
from starlette.status import HTTP_424_FAILED_DEPENDENCY

from ..filewatcher import FileWatcher
from ..tournament import Tournament

logger = logging.getLogger(__name__)


@dataclass()
class CliContext(_CliContext):
    api: FastAPI
    watcher: FileWatcher | None = None

    def __hash__(self) -> int:
        return hash(self.api)


pass_clictx = click.make_pass_decorator(CliContext)


def get_clictx(httpcon: HTTPConnection) -> CliContext:
    return cast(CliContext, httpcon.app.state.clictx)


def get_tournament(clictx: Annotated[CliContext, Depends(get_clictx)]) -> Tournament:
    if (tournament := clictx.itc.get("tournament")) is None:
        raise HTTPException(
            status_code=HTTP_424_FAILED_DEPENDENCY,
            detail="Tournament not loaded",
        )
    return cast(Tournament, tournament)


def get_peer(httpcon: HTTPConnection) -> str:
    if httpcon.client is None:
        return "(unknown)"

    host = httpcon.headers.get(
        "X-Forwarded-For",
        httpcon.client.host,
    )

    return f"{host}:{httpcon.client.port}"


def validate_url(
    ctx: click.Context,
    param: str,
    value: str | None,
) -> URL | None:
    _ = ctx, param

    if value is None:
        return None

    try:
        url = URL(value)

    except TypeError as err:
        raise click.BadParameter(
            f"URL must be a string, not '{type(value).__name__}': {value}"
        ) from err

    except InvalidURL as err:  # pragma: nocover TODO: how do I test for this?
        raise click.BadParameter(f"{value} is invalid: {err}") from err

    else:
        if not url.is_absolute_url:
            raise click.BadParameter(f"URL is not absolute: {value}")

        return url


def validate_urls(
    ctx: click.Context,
    param: str,
    value: tuple[str | None],
) -> list[URL]:
    _ = ctx, param
    ret = []
    for urlstr in value:
        if (url := validate_url(ctx, param, urlstr)) is not None:
            ret.append(url)

    return ret


class PostData[T: BaseModel](BaseModel):
    cookie: int
    data: T


async def http_request(
    method: str,
    url: URL,
    *,
    data: BaseModel | None = None,
    retries: int = 3,
    sleep: float = 1,
    to_json_fn: Callable[..., str] | None = None,
) -> dict[str, Any] | None:
    request_args = {"method": method, "url": url, "content": None, "headers": {}}
    if data is not None:
        to_json_fn = to_json_fn or (
            type(data).model_dump_json if data is not None else json.dumps
        )
        logger.debug(f"Posting JSON of '{data}' to {url}")
        request_args["content"] = to_json_fn(data)
        request_args["headers"] = {"Content-Type": "application/json"}

    while True:
        try:
            async with AsyncClient() as client:
                resp = await client.request(**request_args)
                rt: dict[str, Any] = resp.json()

                if resp.status_code == status_codes.OK:
                    logger.info(
                        f"{method} request with "
                        f"{len(resp.request.content)} bytes of data "
                        f"yielded a response of {len(resp.content)} bytes"
                    )

                else:
                    logger.info(
                        f"{method} request with "
                        f"{len(resp.request.content)} bytes of data "
                        f"yielded status {resp.status_code}, {resp.reason_phrase}"
                    )

                return rt

        except json.JSONDecodeError as err:
            logger.warning(
                f"{method} request to {url} yielded an invalid JSON response: {err}."
            )
            return None

        except HTTPError as err:
            if retries > 0:
                retries -= 1
                logger.warning(
                    f"Problem with {method} request to {url}: {err}, retrying…"
                )
                await asyncio.sleep(sleep)
                continue

            else:
                logger.error(f"Giving up {method} request to {url}: {err}")
                break

    return None
