import logging
from contextlib import asynccontextmanager
from typing import Any

import click
from click_async_plugins import PluginLifespan, plugin
from fastapi import FastAPI, HTTPException, Request
from starlette.status import HTTP_508_LOOP_DETECTED

from tptools import Tournament

from .util import CliContext, PostData, pass_clictx

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


@asynccontextmanager
async def setup_to_receive_tournament_post(
    clictx: CliContext,
    api_mount_point: str = API_MOUNTPOINT,
) -> PluginLifespan:
    api_path = "/".join((api_mount_point, TPRECV_PATH_VERSION))

    logger.debug("Starting squoresrv configuration…")
    recvapp.state.clictx = clictx
    clictx.api.mount(path=api_path, app=recvapp, name="squore")
    logger.info(f"Configured the app to receive tptools data at {api_path}")

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
@pass_clictx
async def tp_recv(
    clictx: CliContext,
    api_mount_point: str,
) -> PluginLifespan:
    """Mount endpoints to receive tournament data from tptools.post"""

    async with setup_to_receive_tournament_post(clictx, api_mount_point) as task:
        yield task
