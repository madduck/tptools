# {{{ Globals

import dataclasses
import importlib.resources
import json
import logging
import pathlib
import re
import tomllib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from operator import attrgetter
from typing import Annotated, Any, Never, cast
from warnings import warn

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.status import (
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_308_PERMANENT_REDIRECT,
    HTTP_404_NOT_FOUND,
    HTTP_424_FAILED_DEPENDENCY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from yarl import URL

from tptools import (
    Court,
    CourtSelectionParams,
    DeviceCourtMap,
    Draw,
    Entry,
    MatchSelectionParams,
    Tournament,
)
from tptools.ext.squore import (
    Config,
    ConfigValidator,
    MatchesFeed,
    MatchesInFeedSelectionParams,
    SquoreTournament,
)
from tptools.ext.squore.court import SquoreCourt
from tptools.ext.squore.draw import SquoreDraw
from tptools.ext.squore.entry import SquoreEntry
from tptools.namepolicy import (
    ClubNamePolicy,
    CountryNamePolicy,
    CountryNamePolicyParams,
    CourtNamePolicy,
    CourtNamePolicyParams,
    PairCombinePolicy,
    PairCombinePolicyParams,
    PlayerNamePolicy,
    PlayerNamePolicyParams,
)
from tptools.namepolicy.policybase import RegexpSubstTuple
from tptools.util import (
    normalise_dict_values_for_query_string,
    silence_logger,
)

from .util import CliContext, pass_clictx

with importlib.resources.path("tptools", "ext", "squore", "assets") as assets_path:
    SETTINGS_JSON_PATH = assets_path / "settings.json"
    CONFIG_TOML_PATH = assets_path / "config.toml"
    # save to exit the context manager here as no temporary files are needed

DEVMAP_TOML_PATH = pathlib.Path("Squore.dev_court_map.toml")
SQUORE_PATH_VERSION = "v1"
API_MOUNTPOINT = "/squore"

# }}}

# {{{ Logging

logger = logging.getLogger(__name__)


silence_logger("tptools.ext.squore.feed", level=logging.INFO)

# }}}

# {{{ Dependencies and parameters


# {{{ SquoreDevQueryParams


class SquoreDevQueryParams(BaseModel):
    cc: str | None = None
    version: int | None = None
    ip: str | None = None
    device_id: str | None = None


def get_squoredevqueryparams(
    squoredev: Annotated[SquoreDevQueryParams, Query()],
) -> SquoreDevQueryParams:
    return squoredev


# }}}

# {{{ Player name policies


class PlayersPolicyParams(PlayerNamePolicyParams, PairCombinePolicyParams): ...


def get_playernamepolicy(
    policyparams: Annotated[PlayerNamePolicyParams, Query()],
) -> PlayerNamePolicy:
    return PlayerNamePolicy(**PlayerNamePolicyParams.extract_subset(policyparams))


def get_paircombinepolicy(
    policyparams: Annotated[PairCombinePolicyParams, Query()],
) -> PairCombinePolicy:
    return PairCombinePolicy(**PairCombinePolicyParams.extract_subset(policyparams))


# }}}

# {{{ Court, club, country name policies


def get_courtnamepolicy(
    policyparams: Annotated[CourtNamePolicyParams, Query()],
) -> CourtNamePolicy:
    c_to_court_subst = RegexpSubstTuple(r"^[cC]0?(?P<nr>\d+)", r"Court \g<nr>")
    return CourtNamePolicy(
        regexps=[c_to_court_subst], **CourtNamePolicyParams.extract_subset(policyparams)
    )


def get_clubnamepolicy() -> ClubNamePolicy:
    vereinslos_is_none = RegexpSubstTuple("vereinslos", "", re.IGNORECASE)
    return ClubNamePolicy(regexps=[vereinslos_is_none])


class CountryNamePolicyParamsDefaultsCountryCode(CountryNamePolicyParams):
    use_country_code: bool = True
    titlecase: bool = False


def get_countrynamepolicy(
    policyparams: Annotated[CountryNamePolicyParamsDefaultsCountryCode, Query()],
) -> CountryNamePolicy:
    return CountryNamePolicy(
        **CountryNamePolicyParamsDefaultsCountryCode.extract_subset(policyparams)
    )


# }}}

# {{{ Policies combined for the match context


class MatchesPolicyParams(
    PlayersPolicyParams,
    CountryNamePolicyParamsDefaultsCountryCode,
    CourtNamePolicyParams,
): ...


def get_matchpolicyparams(
    policyparams: Annotated[MatchesPolicyParams, Query()],
) -> MatchesPolicyParams:
    return MatchesPolicyParams.make_from_parameter_superset(policyparams)


# }}}

# {{{ Tournament data dependencies


def get_tournament(request: Request) -> SquoreTournament | Never:
    if (tournament := getattr(request.app.state, "tournament", None)) is None:
        raise HTTPException(
            status_code=HTTP_424_FAILED_DEPENDENCY,
            detail="Tournament not loaded",
        )
    return cast(SquoreTournament, tournament)


def get_tournament_name(
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
) -> str:
    return tournament.name or "tptools Tournament"


def get_courts(
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
) -> list[SquoreCourt]:
    return tournament.get_courts()


def get_draws(
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
) -> list[SquoreDraw]:
    return tournament.get_draws()


def get_entries(
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
) -> list[SquoreEntry]:
    return tournament.get_entries()


def get_players_list(
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    entries: Annotated[list[Entry], Depends(get_entries)],
) -> list[dict[str, Any]]:
    return [
        e.model_dump(
            context={
                "playernamepolicy": playernamepolicy,
                "paircombinepolicy": paircombinepolicy,
            }
        )
        for e in sorted(entries, key=attrgetter("player1", "player2"))
    ]


# }}}

# {{{ Match selection (by match status)


class MatchSelectionParamsDefaultsOnlyReady(MatchSelectionParams):
    include_played: bool = False
    include_not_ready: bool = False


def get_matchselectionparams(
    policyparams: Annotated[MatchSelectionParamsDefaultsOnlyReady, Query()],
) -> MatchSelectionParamsDefaultsOnlyReady:
    return MatchSelectionParamsDefaultsOnlyReady.make_from_parameter_superset(
        policyparams
    )


# }}}

# {{{ Match selection (by court, and count limit)


def get_courtselectionparams(
    policyparams: Annotated[MatchesPolicyParams, Query()],
) -> CourtSelectionParams:
    return CourtSelectionParams.make_from_parameter_superset(policyparams)


def get_matchesinfeedselectionparams(
    policyparams: Annotated[MatchesInFeedSelectionParams, Query()],
) -> MatchesInFeedSelectionParams:
    return MatchesInFeedSelectionParams.make_from_parameter_superset(policyparams)


# }}}

# {{{ Command-line params


class CommandLineParams(MatchesInFeedSelectionParams):
    include_feeds: bool = True
    kiosk_mode: bool = False


def get_commandlineparams(request: Request) -> CommandLineParams:
    try:
        return cast(CommandLineParams, request.app.state.squore["commandlineparams"])

    except (AttributeError, KeyError) as err:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="App state does not include squore.commandlineparams",
        ) from err


# }}}

# {{{ Request related dependencies


def get_remote(request: Request) -> str | None:
    return request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else None
    )


def get_url(request: Request) -> URL:
    # Prefer to work with yarl.URL over starlette.datastructures.URL, so must go via
    # str():
    return URL(str(request.url))


# }}}

# {{{ Setting, config, devmap


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


def _relative_to_absolute_urls(urls_per_line: str, myurl: URL) -> str:
    urls: list[str] = []
    for urlstr in urls_per_line.splitlines():
        if URL(urlstr).is_absolute():
            continue
        urls.append(str(myurl.with_path(urlstr, encoded=True)))
    return "\n".join(urls)


def get_settings(
    path: Annotated[pathlib.Path, Depends(get_settings_path)],
    myurl: Annotated[URL, Depends(get_url)],
) -> dict[str, Any] | Never:
    try:
        with open(path, "rb") as f:
            # TODO:cache. There should be a file-like class that caches the output,
            # ideally even the output of a callable on the data, and on every
            # subsequent access, check the original file's mtime to decide whether
            # to serve the cache, or relaod.

            settings: dict[str, Any] = json.load(f)

            for setting in ("FlagsURLs",):
                if setting in settings:
                    settings[setting] = _relative_to_absolute_urls(
                        settings[setting], myurl
                    )
            settings.pop("_COMMENT", None)
            return settings

    except FileNotFoundError as err:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Squore settings file not found at {path}",
        ) from err


def get_config(
    path: Annotated[pathlib.Path, Depends(get_config_path)],
    myurl: Annotated[URL, Depends(get_url)],
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

    for setting in ("PostResult",):
        if setting in config:
            config[setting] = _relative_to_absolute_urls(config[setting], myurl)

    return config


def get_dev_map(
    path: Annotated[pathlib.Path, Depends(get_devmap_path)],
) -> DeviceCourtMap:
    try:
        with open(path, "rb") as f:
            return DeviceCourtMap(f)

    except FileNotFoundError:
        logger.warning(f"Squore device to court map not found at {path}, ignoring…")

    return DeviceCourtMap()


# }}}

# {{{ Court name to dev/mirror


def get_court_for_dev(
    dev_map: Annotated[DeviceCourtMap, Depends(get_dev_map)],
    courts: Annotated[list[Court], Depends(get_courts)],
    clientip: Annotated[str, Depends(get_remote)],
) -> Court | None:
    return dev_map.find_court_for_ip(clientip, courts=courts)


def get_mirror_for_dev(
    dev_map: Annotated[DeviceCourtMap, Depends(get_dev_map)],
    clientip: Annotated[str, Depends(get_remote)],
) -> str | None:
    othername = None
    if (othername := dev_map.find_match_for_ip(clientip)) is not None and re.fullmatch(
        r"\w{6}-\d+-.+", othername := str(othername)
    ):
        logger.debug(f"Device at IP {clientip} wants to be mirror for {othername}")
        return othername

    logger.debug(f"No mirror device found in devmap for device with IP {clientip}")
    return None


# }}}

# {{{ Per-court feed data


class CourtFeedData(BaseModel):
    Section: str
    Name: str
    FeedMatches: str
    FeedPlayers: str
    PostResult: str
    CourtID: int


def get_feed_data_for_all_courts(
    urlbase: Annotated[URL, Depends(get_url)],
    tournament_name: Annotated[str, Depends(get_tournament_name)],
    courts: Annotated[list[Court], Depends(get_courts)],
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    countrynamepolicy: Annotated[CountryNamePolicy, Depends(get_countrynamepolicy)],
    courtnamepolicy: Annotated[CourtNamePolicy, Depends(get_courtnamepolicy)],
    matchselectionparams: Annotated[
        MatchSelectionParamsDefaultsOnlyReady, Depends(get_matchselectionparams)
    ],
    config: Annotated[Config, Depends(get_config)],
) -> list[CourtFeedData]:
    ret: list[CourtFeedData] = []
    playerpolicyparams = playernamepolicy.params() | paircombinepolicy.params()
    playersurl = (urlbase / ".." / "players").with_query(
        **normalise_dict_values_for_query_string(
            playerpolicyparams
            | {
                "lnamefirst": True,
                "namejoinstr": ", ",
                "include_club": True,
                "include_country": True,
            }
        )
    )
    resultsurl = config.get("PostResult", urlbase / ".." / "result")

    courtparams = (
        matchselectionparams.model_dump()
        | courtnamepolicy.params()
        | countrynamepolicy.params()
        | playerpolicyparams
    )
    for court in sorted(courts):
        courtparams["court"] = court.id

        matchesurl = (urlbase / ".." / "matches").with_query(
            **normalise_dict_values_for_query_string(courtparams)
        )

        ret.append(
            CourtFeedData(
                Section=tournament_name,
                Name=courtnamepolicy(court) or "",
                FeedPlayers=str(playersurl),
                FeedMatches=str(matchesurl),
                PostResult=str(resultsurl),
                CourtID=court.id,
            )
        )

    return ret


# }}}


# }}}


# {{{ Routes


squoreapp = FastAPI()

# {{{ GET /matches


def get_matches_feed_dict(
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
    config: Annotated[Config, Depends(get_config)],
    playernamepolicy: Annotated[PlayerNamePolicy, Depends(get_playernamepolicy)],
    paircombinepolicy: Annotated[PairCombinePolicy, Depends(get_paircombinepolicy)],
    countrynamepolicy: Annotated[CountryNamePolicy, Depends(get_countrynamepolicy)],
    clubnamepolicy: Annotated[ClubNamePolicy, Depends(get_clubnamepolicy)],
    courtnamepolicy: Annotated[CourtNamePolicy, Depends(get_courtnamepolicy)],
    matchselectionparams: Annotated[
        MatchSelectionParamsDefaultsOnlyReady, Depends(get_matchselectionparams)
    ],
    matchesinfeedselectionparams: Annotated[
        MatchesInFeedSelectionParams, Depends(get_matchesinfeedselectionparams)
    ],
    court_for_dev: Annotated[Court | None, Depends(get_court_for_dev)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
    commandlineparams: Annotated[CommandLineParams, Depends(get_commandlineparams)],
) -> dict[str, Any]:
    if matchesinfeedselectionparams.court is None and court_for_dev:
        matchesinfeedselectionparams.court = court_for_dev.id
        logger.info(
            f"Expand section for court {court_for_dev} for device {squoredev.device_id}"
        )

    matchesinfeedselectionparams = MatchesInFeedSelectionParams(
        **commandlineparams.model_dump()
        | matchesinfeedselectionparams.model_dump(exclude_defaults=True)
    )

    if not countrynamepolicy.use_country_code:
        logger.warning("Overriding CountryNamePolicy.use_country_code = True")

    countrynamepolicy = dataclasses.replace(
        countrynamepolicy, use_country_code=True, titlecase=False
    )

    logger.info(
        f"Making MatchesFeed ({matchselectionparams}, {matchesinfeedselectionparams})"
    )

    return MatchesFeed(tournament=tournament, config=config).model_dump(
        context={
            "courtnamepolicy": courtnamepolicy,
            "paircombinepolicy": paircombinepolicy,
            "playernamepolicy": playernamepolicy,
            "clubnamepolicy": clubnamepolicy,
            "countrynamepolicy": countrynamepolicy,
            "matchselectionparams": matchselectionparams,
            "matchesinfeedselectionparams": matchesinfeedselectionparams,
        }
    )


@squoreapp.get("/matches")
async def matches(
    remote: Annotated[str, Depends(get_remote)],
    matchpolicyparams: Annotated[MatchesPolicyParams, Depends(get_matchpolicyparams)],
    matchfeedparams: Annotated[
        MatchesInFeedSelectionParams, Depends(get_matchesinfeedselectionparams)
    ],
    matches_feed_dict: Annotated[dict[str, Any], Depends(get_matches_feed_dict)],
) -> dict[str, Any]:
    logger.info(
        f"Returning {matches_feed_dict['nummatches']} matches in response to "
        f"request from {remote} "
        f"(policyparams=({matchpolicyparams}) feedparams=({matchfeedparams}))"
    )
    # we cannot return a MatchesFeed as there is currently no way to pass data into the
    # model_dump context with FastAPI: https://github.com/fastapi/fastapi/pull/13475
    return matches_feed_dict


# }}}

# {{{ GET /players


@squoreapp.get("/players")
async def players(
    remote: Annotated[str, Depends(get_remote)],
    policyparams: Annotated[PlayersPolicyParams, Query()],
    players: Annotated[list[dict[str, Any]], Depends(get_players_list)],
) -> PlainTextResponse:
    logger.info(
        f"Returning {len(players)} players in response to request from {remote} "
        f"({policyparams})"
    )
    return PlainTextResponse("\n".join([p["name"] for p in players]))


# }}}

# {{{ GET /tournament


@squoreapp.get("/tournament")
async def tournament(
    remote: Annotated[str, Depends(get_remote)],
    tournament: Annotated[SquoreTournament, Depends(get_tournament)],
) -> SquoreTournament:
    logger.info(f"Returning tournament name in response to request from {remote}")
    return tournament


# }}}

# {{{ GET /courts


class CourtInfo(BaseModel):
    id: int
    name: str
    location: str


@squoreapp.get("/courts")
async def courts(
    remote: Annotated[str, Depends(get_remote)],
    courts: Annotated[list[Court], Depends(get_courts)],
) -> list[Court]:
    logger.info(f"Returning {len(courts)} courts in response to request from {remote}")
    return courts


# }}}

# {{{ GET /draws


@squoreapp.get("/draws")
async def draws(
    remote: Annotated[str, Depends(get_remote)],
    draws: Annotated[list[Draw], Depends(get_draws)],
) -> list[Draw]:
    logger.info(f"Returning {len(draws)} draws in response to request from {remote}")
    return draws


# }}}

# {{{ GET /feeds


@squoreapp.get("/feeds")
async def feeds(
    remote: Annotated[str, Depends(get_remote)],
    policyparams: Annotated[MatchesPolicyParams, Query()],
    court_feeds: Annotated[list[CourtFeedData], Depends(get_feed_data_for_all_courts)],
) -> list[CourtFeedData]:
    logger.info(
        f"Returning {len(court_feeds)} feeds in response to "
        f"request from remote {remote} ({policyparams})"
    )
    return court_feeds


# }}}

# {{{ GET /init


@squoreapp.get("/init")
async def init(
    myurl: Annotated[URL, Depends(get_url)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
) -> RedirectResponse:
    redirect_url = (
        myurl
        / ".."
        / "settings"
        % normalise_dict_values_for_query_string(squoredev.model_dump())
    )
    return RedirectResponse(str(redirect_url), HTTP_307_TEMPORARY_REDIRECT)


# }}}

# {{{ GET /settings


@squoreapp.get("/settings")
async def settings(
    myurl: Annotated[URL, Depends(get_url)],
    remote: Annotated[str, Depends(get_remote)],
    settings: Annotated[dict[str, Any], Depends(get_settings)],
    court_feeds: Annotated[list[CourtFeedData], Depends(get_feed_data_for_all_courts)],
    court_for_dev: Annotated[Court | None, Depends(get_court_for_dev)],
    mirror_for_dev: Annotated[str | None, Depends(get_mirror_for_dev)],
    squoredev: Annotated[SquoreDevQueryParams, Depends(get_squoredevqueryparams)],
    commandlineparams: Annotated[CommandLineParams, Depends(get_commandlineparams)],
) -> dict[str, Any]:
    logger.info(
        f"App settings request from remote {remote} "
        f"for device {squoredev.device_id or '(no ID)'} "
        f"(ip={squoredev.ip}, cc={squoredev.cc}, v={squoredev.version})"
    )

    settings["RemoteSettingsURL"] = (initurl := str(myurl / ".." / "init"))
    settings["RemoteSettingsURL_Default"] = initurl

    if mirror_for_dev is not None:
        logger.info(f"Client at {remote} set up to MQTT-mirror device {mirror_for_dev}")
        settings.pop("StartupAction", None)
        return settings | {
            "useShareFeature": "DoNotUse",
            "useVibrationNotificationInTimer": False,
            "autoSuggestToPostResult": False,
            "showDetailsAtEndOfGamEAutomatically": True,
            "feedPostUrls": None,
            "postEveryChangeToSupportLiveScore": False,
            "BackKeyBehaviour": "PressTwiceToExit",
            "hapticFeedbackOnGameEnd": False,
            "hapticFeedbackPerPoint": False,
            "MQTTOtherDeviceId": mirror_for_dev,
            "MQTTDisableInputWhenSlave": True,
            "liveScoreDeviceId_customSuffix": f"-mirror-{mirror_for_dev}",
        }

    if commandlineparams.include_feeds:
        feeds: list[str] = []
        courtorder: dict[int, tuple[int, str]] = {}
        for idx, courtfeed in enumerate(court_feeds, 0):
            feeds.append(
                f"Name={courtfeed.Section} {courtfeed.Name}\n"
                f"FeedPlayers={courtfeed.FeedPlayers}\n"
                f"FeedMatches={courtfeed.FeedMatches}\n"
                f"PostResult={courtfeed.PostResult}\n"
            )
            courtorder[courtfeed.CourtID] = idx, courtfeed.Name

        settings["feedPostUrls"] = ("\n".join(feeds)).strip()
        if commandlineparams.kiosk_mode:
            settings["kioskMode"] = "MatchesFromSingleFeed_1"
        else:
            settings["kioskMode"] = "NotUsed"

        if court_for_dev is not None:
            try:
                idx, name = courtorder[court_for_dev.id]
                settings["feedPostUrl"] = idx
                logger.info(
                    f"Pre-selected feed {idx} ({name}) "
                    f"for device {squoredev.device_id or '(no device ID)'}"
                )

            except KeyError:
                logger.warning(f"There is no feed for a {court_for_dev!r}")

    if court_for_dev is not None:
        c = court_for_dev
        courtname = (
            f"{c.location.id if c.location else 0}-"
            f"{re.sub(r'\W', '_', c.name, count=0, flags=re.ASCII)}"
        )
        settings["liveScoreDeviceId_customSuffix"] = f"-{courtname}"

    # logger.debug(
    #     f"Settings for device {squoredev.device_id or '(no ID)'}: "
    #     + json.dumps(settings)
    # )
    return settings


# }}}

# {{{ Deprecated routes

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


# }}}

# }}}


@asynccontextmanager
async def setup_for_squore(
    *,
    clictx: CliContext,
    kiosk_mode: bool = False,
    only_this_court: bool = False,
    max_matches_per_court: int | None = None,
    include_feeds: bool = True,
    api_mount_point: str = API_MOUNTPOINT,
    settings_json: pathlib.Path = SETTINGS_JSON_PATH,
    config_toml: pathlib.Path = CONFIG_TOML_PATH,
    devmap_toml: pathlib.Path = DEVMAP_TOML_PATH,
) -> PluginLifespan:
    api_path = "/".join((api_mount_point, SQUORE_PATH_VERSION))

    logger.debug("Starting squoresrv configuration…")

    logger.info(f"Serving app settings from {settings_json}")
    logger.info(f"Reading tournament & match config from {config_toml}")
    if devmap_toml.exists():
        logger.info(f"Reading device to court map from {devmap_toml}")

    squoreapp.state.squore = {
        "settings": settings_json,
        "config": config_toml,
        "devmap": devmap_toml,
        "commandlineparams": CommandLineParams(
            only_this_court=only_this_court,
            max_matches_per_court=max_matches_per_court,
            kiosk_mode=kiosk_mode,
            include_feeds=include_feeds,
        ),
    }
    squoreapp.mount(
        "/flags",
        StaticFiles(directory=assets_path / "flags", html=True),
        name="flags",
    )

    clictx.api.mount(path=api_path, app=squoreapp, name="squore")
    clictx.api.include_router(deprecated_routes, prefix=api_mount_point)
    logger.info(f"Configured the app to serve to Squore from {api_path}")

    async def callback(tournament: Tournament) -> None:
        logger.info("Received new tournament data, making MatchesFeed")
        squoreapp.state.tournament = (
            sqt := SquoreTournament.from_tournament(tournament)
        )
        clictx.itc.set("sqtournament", sqt)

    updates_gen = cast(AsyncGenerator[Tournament], clictx.itc.updates("tournament"))
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--kiosk-mode",
    "-k",
    is_flag=True,
    help="Configure clients to use kiosk-mode and restrict the UI",
)
@click.option(
    "--only-this-court",
    "-o",
    is_flag=True,
    help="Configure clients to only show matches for the selected court",
)
@click.option(
    "--max-matches-per-court",
    "-m",
    type=click.IntRange(min=1),
    default=None,
    help="Limit the number of matches to include in a court feed",
)
@click.option(
    "--no-feeds",
    "-n",
    is_flag=True,
    help="Do not include match feed URLs in settings",
)
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
@pass_clictx
async def squoresrv(
    clictx: CliContext,
    kiosk_mode: bool,
    only_this_court: bool,
    max_matches_per_court: int | None,
    no_feeds: bool,
    api_mount_point: str,
    settings_json: pathlib.Path,
    config_toml: pathlib.Path,
    devmap_toml: pathlib.Path,
) -> PluginLifespan:
    """Mount endpoints to serve data for Squore"""

    async with setup_for_squore(
        clictx=clictx,
        kiosk_mode=kiosk_mode,
        only_this_court=only_this_court,
        max_matches_per_court=max_matches_per_court,
        include_feeds=not no_feeds,
        api_mount_point=api_mount_point,
        settings_json=settings_json,
        config_toml=config_toml,
        devmap_toml=devmap_toml,
    ) as task:
        yield task


# vim:fdm=marker:fdl=0
