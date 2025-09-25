# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import json
import logging
import pathlib
import tomllib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from operator import attrgetter
from typing import Annotated, Any, Never, cast
from warnings import warn

import click
from click_async_plugins import PluginLifespan, plugin
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.status import (
    HTTP_308_PERMANENT_REDIRECT,
    HTTP_404_NOT_FOUND,
    HTTP_424_FAILED_DEPENDENCY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from yarl import URL

from tptools.export import (
    Court,
    Entry,
    EntryStruct,
    MatchStatusSelectionParams,
    Tournament,
)
from tptools.ext.squore import (
    Config,
    ConfigValidator,
    CourtSelectionParams,
    MatchesFeed,
)
from tptools.namepolicy import (
    ClubNamePolicy,
    CountryNamePolicy,
    CourtNamePolicy,
    CourtNamePolicyParams,
    PairCombinePolicy,
    PairCombinePolicyParams,
    PlayerNamePolicy,
    PlayerNamePolicyParams,
)
from tptools.util import dict_value_replace_bool_with_int

from .util import TpsrvContext, react_to_data_update

SETTINGS_JSON_PATH = (
    pathlib.Path(__file__).parent.parent.parent / "ext" / "Squore.settings.json"
).relative_to(pathlib.Path.cwd(), walk_up=True)
CONFIG_TOML_PATH = (
    pathlib.Path(__file__).parent.parent.parent / "ext" / "Squore.config.toml"
).relative_to(pathlib.Path.cwd(), walk_up=True)
DEVMAP_TOML_PATH = pathlib.Path("Squore.dev_court_map.toml")
SQUORE_PATH_VERSION = "v1"
API_MOUNTPOINT = "/squore"

logger = logging.getLogger(__name__)


class SquoreDevQueryParams(BaseModel):
    cc: str | None = None
    version: int | None = None
    ip: str | None = None
    device_id: str | None = None


class PlayersPolicyParams(PlayerNamePolicyParams, PairCombinePolicyParams): ...


class MatchesPolicyParams(
    PlayersPolicyParams,
    CourtNamePolicyParams,
    CourtSelectionParams,
    MatchStatusSelectionParams,
): ...


def get_squoredevqueryparams(
    squoredev: Annotated[SquoreDevQueryParams, Query()],
) -> SquoreDevQueryParams:
    return squoredev


def get_playernamepolicy(
    policyparams: Annotated[PlayersPolicyParams, Query()],
) -> PlayerNamePolicy:
    return PlayerNamePolicy(**PlayerNamePolicyParams.extract_subset(policyparams))


def get_paircombinepolicy(
    policyparams: Annotated[PlayersPolicyParams, Query()],
) -> PairCombinePolicy:
    return PairCombinePolicy(**PairCombinePolicyParams.extract_subset(policyparams))


def get_courtnamepolicy(
    policyparams: Annotated[MatchesPolicyParams, Query()],
) -> CourtNamePolicy:
    return CourtNamePolicy(**CourtNamePolicyParams.extract_subset(policyparams))


def get_courtselectionparams(
    policyparams: Annotated[MatchesPolicyParams, Query()],
) -> CourtSelectionParams:
    return CourtSelectionParams.make_from_parameter_superset(policyparams)


def get_matchstatusselectionparams(
    policyparams: Annotated[MatchesPolicyParams, Query()],
) -> MatchStatusSelectionParams:
    return MatchStatusSelectionParams.make_from_parameter_superset(policyparams)


def get_remote(request: Request) -> str | None:
    return request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else None
    )


def get_url(request: Request) -> URL:
    return URL(str(request.url))


def get_settings_path(request: Request) -> pathlib.Path | Never:
    try:
        return cast(pathlib.Path, request.app.state.squore["settings"])

    except (AttributeError, KeyError) as err:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="App state does not include squore.settings",
        ) from err


def get_config_path(request: Request) -> pathlib.Path | Never:
    try:
        return cast(pathlib.Path, request.app.state.squore["config"])

    except (AttributeError, KeyError) as err:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="App state does not include squore.config",
        ) from err


def get_devmap_path(request: Request) -> pathlib.Path | Never:
    try:
        return cast(pathlib.Path, request.app.state.squore["devmap"])

    except (AttributeError, KeyError) as err:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="App state does not include squore.devmap",
        ) from err


def get_settings(
    path: Annotated[pathlib.Path, Depends(get_settings_path)],
) -> dict[str, Any] | Never:
    try:
        with open(path, "rb") as f:
            # TODO:cache. There should be a file-like class that caches the output,
            # ideally even the output of a callable on the data, and on every
            # subsequent access, check the original file's mtime to decide whether
            # to serve the cache, or relaod.
            return cast(dict[str, Any], json.load(f))

    except FileNotFoundError as err:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Squore settings file not found at {path}",
        ) from err


def get_config(
    path: Annotated[pathlib.Path, Depends(get_config_path)],
) -> Config | Never:
    config: Config = {}

    try:
        with open(path, "rb") as f:
            # TODO:cache. There should be a file-like class that caches the output,
            # ideally even the output of a callable on the data, and on every
            # subsequent access, check the original file's mtime to decide whether
            # to serve the cache, or relaod.
            tomlconfig = tomllib.load(f)

    except FileNotFoundError:
        logger.warning(f"Squore config file not found at {path}, ignoring…")

    else:
        config = ConfigValidator.validate_python(tomlconfig, strict=True)

        for key in tomlconfig:
            if key not in config:
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid key in config file {path}: {key}",
                )

    return config


def get_dev_courtid_map(
    path: Annotated[pathlib.Path, Depends(get_devmap_path)],
) -> dict[str, int] | Never:
    devmap: dict[str, int] = {}

    try:
        with open(path, "rb") as f:
            # TODO:cache. There should be a file-like class that caches the output,
            # ideally even the output of a callable on the data, and on every
            # subsequent access, check the original file's mtime to decide whether
            # to serve the cache, or relaod.
            devmap |= tomllib.load(f)

    except FileNotFoundError:
        logger.warning(f"Squore device to court map not found at {path}, ignoring…")

    return devmap


def get_courtid_for_dev(
    dev_court_map: Annotated[dict[str, int], Depends(get_dev_courtid_map)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
) -> int | None:
    return dev_court_map.get(squoredev.device_id) if squoredev.device_id else None


def get_tournament(request: Request) -> Tournament | Never:
    if (tournament := getattr(request.app.state, "tournament", None)) is None:
        raise HTTPException(
            status_code=HTTP_424_FAILED_DEPENDENCY,
            detail="Tournament not loaded",
        )
    return cast(Tournament, tournament)


def get_tournament_name(
    tournament: Annotated[Tournament, Depends(get_tournament)],
) -> str:
    return tournament.name or "tptools Tournament"


def get_courts(
    tournament: Annotated[Tournament, Depends(get_tournament)],
) -> list[Court]:
    return list(tournament.get_courts().values())


def get_entries(
    tournament: Annotated[Tournament, Depends(get_tournament)],
) -> list[Entry]:
    return list(tournament.get_entries().values())


def get_players_list(
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    entries: Annotated[list[Entry], Depends(get_entries)],
) -> list[EntryStruct]:
    return [
        e.model_dump(
            context={
                "playernamepolicy": playernamepolicy,
                "paircombinepolicy": paircombinepolicy,
            }
        )
        for e in sorted(entries, key=attrgetter("tpentry.player1", "tpentry.player2"))
    ]


def get_matches_feed_dict(
    tournament: Annotated[Tournament, Depends(get_tournament)],
    config: Annotated[Config, Depends(get_config)],
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    courtnamepolicy: Annotated[CourtNamePolicy, Depends(get_courtnamepolicy)],
    courtselectionparams: Annotated[
        CourtSelectionParams, Depends(get_courtselectionparams)
    ],
    matchstatusselectionparams: Annotated[
        MatchStatusSelectionParams, Depends(get_matchstatusselectionparams)
    ],
    court_for_dev: Annotated[int | None, Depends(get_courtid_for_dev)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
) -> dict[str, Any]:
    if courtselectionparams.court is None:
        # I actually don't think this branch will ever enter as the device ID is not
        # sent for matches. Oh well.
        courtselectionparams.court = court_for_dev
        logger.info(
            f"Expand section for court ID {court_for_dev} "
            f"for device {squoredev.device_id}"
        )

    return MatchesFeed(tournament=tournament, config=config).model_dump(
        context={
            "courtnamepolicy": courtnamepolicy,
            "paircombinepolicy": paircombinepolicy,
            "playernamepolicy": playernamepolicy,
            "clubnamepolicy": ClubNamePolicy(),
            "countrynamepolicy": CountryNamePolicy(),
            "courtselectionparams": courtselectionparams,
            "matchstatusselectionparams": matchstatusselectionparams,
        }
    )


class Feed(BaseModel):
    Section: str
    Name: str
    FeedMatches: str
    FeedPlayers: str
    PostResult: str | None
    CourtID: int


def get_court_feeds_list(
    urlbase: Annotated[URL, Depends(get_url)],
    tournament_name: Annotated[str, Depends(get_tournament_name)],
    courts: Annotated[list[Court], Depends(get_courts)],
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    courtnamepolicy: Annotated[CourtNamePolicy, Depends(get_courtnamepolicy)],
    courtselectionparams: Annotated[
        CourtSelectionParams, Depends(get_courtselectionparams)
    ],
    matchstatusselectionparams: Annotated[
        MatchStatusSelectionParams, Depends(get_matchstatusselectionparams)
    ],
) -> list[Feed]:
    ret: list[Feed] = []
    playerpolicyparams = playernamepolicy.params() | paircombinepolicy.params()
    playersurl = (urlbase / ".." / "players").with_query(
        **dict_value_replace_bool_with_int(
            playerpolicyparams
            | {
                "lnamefirst": True,
                "playerjoinstr": ", ",
                "include_club": True,
                "include_country": True,
            }
        )
    )
    for court in sorted(courts):
        params = (
            courtselectionparams.model_dump()
            | matchstatusselectionparams.model_dump()
            | courtnamepolicy.params()
            | playerpolicyparams
            | {"court": court.id}
        )
        matchesurl = (urlbase / ".." / "matches").with_query(
            **dict_value_replace_bool_with_int(params)
        )

        ret.append(
            Feed(
                Section=tournament_name,
                Name=courtnamepolicy(court.tpcourt) or "",
                FeedPlayers=str(playersurl),
                FeedMatches=str(matchesurl),
                PostResult=None,
                CourtID=court.id,
            )
        )

    return ret


squoreapp = FastAPI()

squoreapp.mount(
    "/flags",
    StaticFiles(directory=pathlib.Path(__file__).parent.parent.parent / "flags"),
    name="flags",
)


@squoreapp.get("/matches")
async def matches(
    remote: Annotated[str, Depends(get_remote)],
    policyparams: Annotated[MatchesPolicyParams, Query()],
    matches_feed: Annotated[dict[str, Any], Depends(get_matches_feed_dict)],
) -> dict[str, Any]:
    logger.info(
        f"Returning {matches_feed['nummatches']} matches in response to "
        f"request from {remote} ({policyparams})"
    )
    # we cannot return a MatchesFeed as there is currently no way to pass data into the
    # model_dump context with FastAPI: https://github.com/fastapi/fastapi/pull/13475
    return matches_feed


@squoreapp.get("/players")
async def players(
    remote: Annotated[str, Depends(get_remote)],
    policyparams: Annotated[PlayersPolicyParams, Query()],
    players: Annotated[list[EntryStruct], Depends(get_players_list)],
) -> PlainTextResponse:
    logger.info(
        f"Returning {len(players)} players in response to request from {remote} "
        f"({policyparams})"
    )
    return PlainTextResponse("\n".join([p["name"] for p in players]))


class CourtInfo(BaseModel):
    id: int
    name: str
    location: str


@squoreapp.get("/courts")
async def courts(
    remote: Annotated[str, Depends(get_remote)],
    courts: Annotated[list[Court], Depends(get_courts)],
) -> list[CourtInfo]:
    logger.info(f"Returning {len(courts)} courts in response to request from {remote}")
    return [CourtInfo(id=c.id, name=c.name, location=c.location.name) for c in courts]


@squoreapp.get("/feeds")
async def feeds(
    remote: Annotated[str, Depends(get_remote)],
    policyparams: Annotated[MatchesPolicyParams, Query()],
    court_feeds: Annotated[list[Feed], Depends(get_court_feeds_list)],
) -> list[Feed]:
    logger.info(
        f"Returning {len(court_feeds)} feeds in response to "
        f"request from remote {remote} ({policyparams})"
    )
    return court_feeds


class SettingsQueryParams(BaseModel):
    include_feeds: bool = True


@squoreapp.get("/settings")
async def settings(
    remote: Annotated[str, Depends(get_remote)],
    settings: Annotated[dict[str, Any], Depends(get_settings)],
    court_feeds: Annotated[list[Feed], Depends(get_court_feeds_list)],
    courtid_for_dev: Annotated[int, Depends(get_courtid_for_dev)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
    params: Annotated[SettingsQueryParams, Query()],
) -> dict[str, Any]:
    logger.info(
        f"App settings request from remote {remote} "
        f"for device {squoredev.device_id or '(no ID)'} "
        f"(ip={squoredev.ip}, cc={squoredev.cc}, v={squoredev.version})"
    )
    if params.include_feeds:
        feeds: list[str] = []
        courtorder: dict[int, tuple[int, str]] = {}
        for idx, courtfeed in enumerate(court_feeds, 0):
            feeds.append(
                f"Name={courtfeed.Section} {courtfeed.Name}\n"
                f"FeedPlayers={courtfeed.FeedPlayers}\n"
                f"FeedMatches={courtfeed.FeedMatches}\n"
            )
            courtorder[courtfeed.CourtID] = idx, courtfeed.Name

        settings["feedPostUrls"] = "\n".join(feeds)

        if courtid_for_dev is not None:
            try:
                idx, name = courtorder[courtid_for_dev]
                settings["feedPostUrl"] = idx
                logger.info(
                    f"Pre-selected feed {idx} (court {name}) "
                    f"for device {squoredev.device_id}"
                )

            except KeyError:
                logger.warning(
                    f"There is no feed for a court with ID {courtid_for_dev}"
                )

    return settings


deprecated_routes = APIRouter()


@deprecated_routes.get("/feeds")
def deprecated_feeds(request: Request) -> RedirectResponse:
    depr_url = URL(str(request.url))
    url = depr_url / ".." / SQUORE_PATH_VERSION / depr_url.name
    warn(
        f"URL route {depr_url} is deprecated in favour or {url}",
        DeprecationWarning,
        stacklevel=2,
    )
    return RedirectResponse(str(url), HTTP_308_PERMANENT_REDIRECT)


@asynccontextmanager
async def setup_for_squore(
    tpsrv: TpsrvContext,
    api_mount_point: str = API_MOUNTPOINT,
    settings_json: pathlib.Path = SETTINGS_JSON_PATH,
    config_toml: pathlib.Path = CONFIG_TOML_PATH,
    devmap_toml: pathlib.Path = DEVMAP_TOML_PATH,
) -> PluginLifespan:
    api_path = "/".join((api_mount_point, SQUORE_PATH_VERSION))

    logger.debug("Starting squoresrv configuration…")
    if settings_json.exists():
        logger.info(f"Serving app settings from {settings_json}")
    if config_toml.exists():
        logger.info(f"Reading tournament & match config from {config_toml}")
    if devmap_toml.exists():
        logger.info(f"Reading device to court map from {devmap_toml}")
    squoreapp.state.squore = {
        "settings": settings_json,
        "config": config_toml,
        "devmap": devmap_toml,
    }
    tpsrv.api.mount(path=api_path, app=squoreapp, name="squore")
    tpsrv.api.include_router(deprecated_routes, prefix=api_mount_point)
    logger.info(f"Configured the app to serve to Squore from {api_path}")

    async def callback(tournament: Tournament) -> None:
        logger.info("Received new tournament data")
        squoreapp.state.tournament = tournament

    updates_gen = cast(AsyncGenerator[Tournament], tpsrv.itc.updates("tournament"))
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--api-mount-point",
    metavar="MOUNTPOINT",
    default=API_MOUNTPOINT,
    show_default=True,
    help="API mount point for Squore endpoints",
)
@click.option(
    "--settings-json",
    metavar="PATH",
    type=click.Path(path_type=pathlib.Path),
    default=SETTINGS_JSON_PATH,
    show_default=True,
    help="Path of file to serve when Squore requests app settings",
)
@click.option(
    "--config-toml",
    metavar="PATH",
    type=click.Path(path_type=pathlib.Path),
    default=CONFIG_TOML_PATH,
    show_default=True,
    help="Path of file to use for Squore tournament & match config",
)
@click.option(
    "--devmap-toml",
    metavar="PATH",
    type=click.Path(path_type=pathlib.Path),
    default=DEVMAP_TOML_PATH,
    show_default=True,
    help="Path of file to use for device to court mapping",
)
async def squoresrv(
    tpsrv: TpsrvContext,
    api_mount_point: str,
    settings_json: pathlib.Path,
    config_toml: pathlib.Path,
    devmap_toml: pathlib.Path,
) -> PluginLifespan:
    """Mount endpoints to serve data for Squore"""

    async with setup_for_squore(
        tpsrv, api_mount_point, settings_json, config_toml, devmap_toml
    ) as task:
        yield task
