import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

import click
from click_async_plugins import PluginLifespan, plugin
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from httpx import URL
from pydantic import ValidationError
from starlette.status import HTTP_508_LOOP_DETECTED

from tptools import Tournament

from .util import (
    CliContext,
    PostData,
    get_clictx,
    get_peer,
    get_tournament,
    http_request,
    pass_clictx,
    validate_url,
)

TPRECV_PATH_VERSION = "v1"
API_MOUNTPOINT = "/tptools"

logger = logging.getLogger(__name__)


recvapp = FastAPI()


@recvapp.post("/tournament")
async def receive_tournament(request: Request) -> dict[str, Any]:
    body = await request.body()
    data = PostData[Tournament].model_validate_json(body)
    clictx: CliContext = request.app.state.clictx
    if data.cookie == hash(clictx):
        raise HTTPException(
            status_code=HTTP_508_LOOP_DETECTED,
            detail="Won't receive my own data",
        )
    tournament = data.data
    logger.info(f"Received tournament from tptools: {tournament}")
    clictx.itc.set("tournament", tournament)
    return {"status": f"Received tournament: {tournament}"}


@recvapp.get("/tournament")
async def serve_tournament(
    peer: Annotated[str, Depends(get_peer)],
    tournament: Annotated[Tournament, Depends(get_tournament)],
) -> Tournament:
    # TODO: this may not belong here, as this is tp_recv, and we are technically
    # serving, but there is also no other use-case right now for this endpoint, so…
    logger.debug(
        f"Returning in response to tournament request from {peer}: {tournament}"
    )
    return tournament


@asynccontextmanager
async def setup_to_receive_tournament_post(
    clictx: CliContext,
    url: URL | None = None,
    api_mount_point: str = API_MOUNTPOINT,
) -> PluginLifespan:
    api_path = "/".join((api_mount_point, TPRECV_PATH_VERSION))

    logger.debug("Starting squoresrv configuration…")
    recvapp.state.clictx = clictx
    clictx.api.mount(path=api_path, app=recvapp, name="squore")
    logger.info(f"Configured the app to receive tptools data at {api_path}")

    if url is not None:
        tdata = await http_request("GET", url)

        try:
            if tdata is not None:
                tournament = Tournament.model_validate(tdata)
                logger.info(f"Fetched initial tournament from {url}: {tournament}")
                clictx.itc.set("tournament", tournament)

            else:
                logger.warning(f"Failed to fetch initial tournament from {url}")

        except ValidationError as exc:
            logger.warning(
                f"Fetched initial tournament from {url} does not validate: {exc}"
            )

    yield None


# TODO: option to load data initially from a remote endpoint


@plugin
@click.option(
    "--api-mount-point",
    metavar="MOUNTPOINT",
    default=API_MOUNTPOINT,
    show_default=True,
    help="API mount point for Squore endpoints",
)
@click.option(
    "--load-from-url",
    "-u",
    metavar="URL",
    callback=validate_url,
    help=("On startup, try to GET tournament from this URL"),
)
@pass_clictx
async def tp_recv(
    clictx: CliContext,
    api_mount_point: str,
    load_from_url: URL | None,
) -> PluginLifespan:
    """Mount endpoints to receive tournament data from tptools.post"""

    async with setup_to_receive_tournament_post(
        clictx, load_from_url, api_mount_point
    ) as task:
        yield task
