import asyncio
import json
import logging
import pathlib
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager
from typing import Any

import click
import pytest
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture
from starlette.requests import Request

from tptools import Entry, Match, Tournament
from tptools.court import Court, CourtSelectionParams
from tptools.draw import Draw
from tptools.ext.squore import SquoreTournament
from tptools.tpsrv import squoresrv as sq
from tptools.tpsrv.squoresrv import (
    API_MOUNTPOINT,
    CONFIG_TOML_PATH,
    DEVMAP_TOML_PATH,
    SETTINGS_JSON_PATH,
    CommandLineParams,
    get_remote,
    setup_for_squore,
    squoreapp,
    squoresrv,
)
from tptools.tpsrv.util import CliContext

from .conftest import InvokePlugin, MakeFactory, running, wait_for

LOGGER = sq.logger.name
NBSP = "\N{NO-BREAK SPACE}"


# fixtures


@pytest.fixture
def sqtournament(
    match1: Match,
    match2: Match,
    match_won_by_B: Match,
    entry1: Entry,
    entry2: Entry,
    court1: Court,
    court2: Court,
    draw1: Draw,
    draw2: Draw,
) -> SquoreTournament:
    """A tournament with two courts and only singles entries

    (the entries are limited because of the problem documented in
    test_players_with_singles_and_doubles_entries_of_the_same_player)
    """
    t = Tournament(name="Sq Test")
    for match in (match1, match2, match_won_by_B):
        t.add_match(match)
    t.add_entries([entry1, entry2])
    t.add_court(court1)
    t.add_court(court2)
    t.add_draw(draw1)
    t.add_draw(draw2)
    return SquoreTournament.from_tournament(t)


@pytest.fixture
def squore_state(
    monkeypatch: MonkeyPatch, tmp_path: pathlib.Path, sqtournament: SquoreTournament
) -> dict[str, Any]:
    """Configure the (module-global) squoreapp like setup_for_squore() would

    The returned dict is the live app state, so tests can alter it. Everything
    is undone after the test.
    """
    state: dict[str, Any] = {
        "settings": SETTINGS_JSON_PATH,
        "config": CONFIG_TOML_PATH,
        "devmap": tmp_path / "no-such-devmap.toml",
        "commandlineparams": CommandLineParams(),
    }
    monkeypatch.setattr(squoreapp.state, "tournament", sqtournament, raising=False)
    monkeypatch.setattr(squoreapp.state, "squore", state, raising=False)
    return state


@pytest.fixture
def client(squore_state: dict[str, Any]) -> TestClient:
    return TestClient(squoreapp, raise_server_exceptions=False)


@pytest.fixture
def write_file(tmp_path: pathlib.Path) -> Callable[[str, str], pathlib.Path]:
    def write(name: str, content: str) -> pathlib.Path:
        path = tmp_path / name
        path.write_text(content)
        return path

    return write


@pytest.fixture
def devmap(
    squore_state: dict[str, Any], write_file: Callable[[str, str], pathlib.Path]
) -> pathlib.Path:
    path = write_file(
        "devmap.toml",
        '"192.0.2.1" = "C1"\n'  # court by name, matches C01 in Sports4You
        '"192.0.2.2" = 2\n'  # court by ID
        '"192.0.2.3" = "abcdef-12-xyz"\n'  # another device to mirror
        '"192.0.2.4" = "whatever"\n',  # neither
    )
    squore_state["devmap"] = path
    return path


@pytest.fixture
def restore_squoreapp(monkeypatch: MonkeyPatch) -> Generator[None]:
    """setup_for_squore() mounts onto, and sets state of, the global squoreapp"""
    routes = list(squoreapp.router.routes)
    monkeypatch.setattr(squoreapp.state, "squore", None, raising=False)
    monkeypatch.setattr(squoreapp.state, "tournament", None, raising=False)
    yield
    squoreapp.router.routes[:] = routes


def device(ip: str) -> dict[str, str]:
    return {"X-Forwarded-For": ip}


# services without a tournament, or with a broken set-up


@pytest.mark.parametrize(
    "path", ["/matches", "/players", "/tournament", "/courts", "/draws", "/feeds"]
)
def test_424_without_tournament(
    client: TestClient, monkeypatch: MonkeyPatch, path: str
) -> None:
    monkeypatch.delattr(squoreapp.state, "tournament")
    resp = client.get(path)
    assert resp.status_code == 424
    assert resp.json() == {"detail": "Tournament not loaded"}


@pytest.mark.parametrize(
    "missing, path",
    [
        ("settings", "/settings"),
        ("config", "/matches"),
        ("config", "/feeds"),
        ("devmap", "/matches"),
        ("commandlineparams", "/matches"),
        ("commandlineparams", "/settings"),
    ],
)
def test_500_if_app_state_is_incomplete(
    client: TestClient, squore_state: dict[str, Any], missing: str, path: str
) -> None:
    del squore_state[missing]
    resp = client.get(path)
    assert resp.status_code == 500
    assert resp.json() == {"detail": f"App state does not include squore.{missing}"}


def test_500_if_app_state_is_missing_altogether(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.delattr(squoreapp.state, "squore")
    resp = client.get("/matches")
    assert resp.status_code == 500
    assert "App state does not include" in resp.json()["detail"]


def test_get_courtselectionparams() -> None:
    # not used by any route (yet), but part of the module
    params = sq.get_courtselectionparams(sq.MatchesPolicyParams())
    assert isinstance(params, CourtSelectionParams)


def test_get_remote_without_client() -> None:
    request = Request({"type": "http", "headers": [], "client": None})
    assert get_remote(request) is None


# GET /tournament, /courts, /draws


def test_tournament(client: TestClient) -> None:
    resp = client.get("/tournament")
    assert resp.status_code == 200
    data = resp.json()
    # Not round-trippable: the models serialise to what Squore expects
    assert data["name"] == "Sq Test"
    assert len(data["entries"]) == 2
    assert len(data["courts"]) == 2
    assert len(data["draws"]) == 2
    assert len(data["matches"]) == 3


def test_courts(client: TestClient) -> None:
    resp = client.get("/courts")
    assert resp.status_code == 200
    assert sorted((c["id"], c["name"]) for c in resp.json()) == [
        (1, "C01"),
        (2, "C07"),
    ]


def test_draws(client: TestClient) -> None:
    resp = client.get("/draws")
    assert resp.status_code == 200
    assert sorted((d["id"], d["name"]) for d in resp.json()) == [
        (1, "Baum"),
        (2, "Gruppe"),
    ]


def test_endpoints_log_the_remote(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        client.get("/courts", headers=device("192.0.2.77"))
        client.get("/draws", headers=device("192.0.2.78"))
    assert "Returning 2 courts in response to request from 192.0.2.77" in caplog.text
    assert "Returning 2 draws in response to request from 192.0.2.78" in caplog.text


# GET /players


def test_players(client: TestClient) -> None:
    resp = client.get("/players")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text == "Iddo Hoeve\nMartin Krafft"


def test_players_name_policy_from_query(client: TestClient) -> None:
    resp = client.get("/players", params={"lnamefirst": True, "namejoinstr": ", "})
    assert resp.text == "Hoeve, Iddo\nKrafft, Martin"


@pytest.mark.xfail(
    strict=True,
    reason="Sorting entries by (player1, player2) compares None with a Player if a "
    "singles and a doubles entry have the same player1, which raises "
    "NotImplementedError and thus gives a 500 response",
)
def test_players_with_singles_and_doubles_entries_of_the_same_player(
    client: TestClient,
    squore_state: dict[str, Any],
    entry1: Entry,
    entry12: Entry,
) -> None:
    t = Tournament(name="Mixed")
    t.add_entries([entry1, entry12])
    squoreapp.state.tournament = SquoreTournament.from_tournament(t)

    assert client.get("/players").status_code == 200


def test_players_with_doubles_entries(
    client: TestClient, squore_state: dict[str, Any], entry12: Entry, entry21: Entry
) -> None:
    t = Tournament(name="Doubles")
    t.add_entries([entry12, entry21])
    squoreapp.state.tournament = SquoreTournament.from_tournament(t)

    resp = client.get("/players")
    assert resp.status_code == 200
    assert resp.text == "Iddo Hoeve&Martin Krafft\nMartin Krafft&Iddo Hoeve"


# GET /matches


def test_matches(client: TestClient) -> None:
    resp = client.get("/matches")
    assert resp.status_code == 200
    feed = resp.json()
    assert feed["name"] == "Sq Test"
    assert feed["nummatches"] == 2, "matches that are over are not included"
    sections = [k for k in feed if k.startswith(("+", NBSP))]
    assert sections == [f"{NBSP}None", f"{NBSP}Court 1"]


def test_matches_include_played(client: TestClient) -> None:
    resp = client.get("/matches", params={"include_played": True})
    assert resp.json()["nummatches"] == 3


def test_matches_config_is_part_of_feed(client: TestClient) -> None:
    config = client.get("/matches").json()["config"]
    assert config["shareAction"] == "PostResult"
    assert config["numberOfPointsToWinGame"] == 11


def test_matches_post_result_url_is_made_absolute(client: TestClient) -> None:
    config = client.get("/matches").json()["config"]
    assert config["PostResult"] == "http://testserver/squore/v1/result"


def test_matches_keeps_absolute_post_result_url(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    squore_state["config"] = write_file(
        "config.toml", 'PostResult = "http://tcboard.example.org/result"\n'
    )
    config = client.get("/matches").json()["config"]
    assert config["PostResult"] == "http://tcboard.example.org/result"


def test_matches_without_config_file(
    client: TestClient,
    squore_state: dict[str, Any],
    tmp_path: pathlib.Path,
    caplog: LogCaptureFixture,
) -> None:
    squore_state["config"] = tmp_path / "no-such-config.toml"

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resp = client.get("/matches")

    assert resp.status_code == 200
    assert "Squore config file not found at" in caplog.text
    assert "shareAction" not in resp.json()["config"]


def test_matches_with_unknown_key_in_config_file(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    # the validator rejects extra keys itself, with an error that is not handled
    squore_state["config"] = write_file(
        "config.toml", 'shareAction = "PostResult"\nbogus = 1\n'
    )
    assert client.get("/matches").status_code == 500


def test_matches_rejects_config_keys_the_validator_dropped(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
    mocker: MockerFixture,
) -> None:
    """Defensive check that is not reachable with the real validator

    ConfigValidator already refuses extra keys, so make it silently drop one.
    """
    path = write_file("config.toml", "bogus = 1\n")
    squore_state["config"] = path
    mocker.patch.object(sq, "ConfigValidator").validate_python.return_value = {}

    resp = client.get("/matches")

    assert resp.status_code == 500
    assert resp.json() == {"detail": f"Invalid key in config file {path}: bogus"}


def test_matches_for_device_expands_its_court(
    client: TestClient, devmap: pathlib.Path, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        feed = client.get(
            "/matches", params={"device_id": "dev1"}, headers=device("192.0.2.1")
        ).json()

    assert f"+{NBSP}Court 1" in feed, "the court of the device is expanded"
    assert "Expand section for court" in caplog.text
    assert "for device dev1" in caplog.text


def test_matches_court_in_query_beats_the_devmap(
    client: TestClient, devmap: pathlib.Path
) -> None:
    feed = client.get(
        "/matches", params={"court": 2}, headers=device("192.0.2.1")
    ).json()
    assert f"+{NBSP}Court 1" not in feed


def test_matches_overrides_country_code_policy(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resp = client.get("/matches", params={"use_country_code": False})

    assert resp.status_code == 200
    assert "Overriding CountryNamePolicy.use_country_code = True" in caplog.text


def test_matches_does_not_warn_by_default_about_country_code(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        client.get("/matches")
    assert "Overriding" not in caplog.text


def test_matches_without_emulation(client: TestClient) -> None:
    config = client.get("/matches").json()["config"]
    assert config["emulate_StartOnMatchSelection"] is False
    assert config["emulate_AutoLoadNextMatch"] == "None"
    assert config["hideCompletedMatchesFromFeed"] is True


def test_matches_with_emulate_scoring(
    client: TestClient, squore_state: dict[str, Any], caplog: LogCaptureFixture
) -> None:
    squore_state["commandlineparams"] = CommandLineParams(emulate_scoring=True)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        config = client.get("/matches").json()["config"]

    assert config["emulate_StartOnMatchSelection"] is True
    assert config["emulate_AutoLoadNextMatch"] == "Next"
    assert config["hideCompletedMatchesFromFeed"] is False
    assert "emulate scoring" in caplog.text


def test_matches_removes_emulate_config_unless_emulating(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    squore_state["config"] = write_file(
        "config.toml", "[emulate_Config]\nSpeedUpFactor = 10\n"
    )

    config = client.get("/matches").json()["config"]
    assert "emulate_Config" not in config

    squore_state["commandlineparams"] = CommandLineParams(emulate_scoring=True)
    config = client.get("/matches").json()["config"]
    assert config["emulate_Config"] == {"SpeedUpFactor": 10}


def test_matches_command_line_params_take_part_in_selection(
    client: TestClient, squore_state: dict[str, Any], caplog: LogCaptureFixture
) -> None:
    squore_state["commandlineparams"] = CommandLineParams(
        only_this_court=True, max_matches_per_court=1
    )
    with caplog.at_level(logging.INFO, logger=LOGGER):
        assert client.get("/matches").status_code == 200

    assert "only_this_court=True" in caplog.text
    assert "max_matches_per_court=1" in caplog.text


def test_matches_logs_what_it_returns(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        client.get("/matches", headers=device("192.0.2.50"))
    assert "Returning 2 matches in response to request from 192.0.2.50" in caplog.text


# GET /feeds


def test_feeds(client: TestClient) -> None:
    resp = client.get("/feeds")
    assert resp.status_code == 200

    feeds = sorted(resp.json(), key=lambda f: f["CourtID"])
    assert [(f["CourtID"], f["Name"]) for f in feeds] == [
        (1, "Court 1"),
        (2, "Court 7"),
    ]
    assert {f["Section"] for f in feeds} == {"Sq Test"}
    assert {f["PostResult"] for f in feeds} == {"http://testserver/squore/v1/result"}
    for feed in feeds:
        assert feed["FeedMatches"].startswith("http://testserver/matches?")
        assert f"court={feed['CourtID']}" in feed["FeedMatches"]
        assert feed["FeedPlayers"].startswith("http://testserver/players?")


def test_feeds_players_url_asks_for_names_squore_can_use(client: TestClient) -> None:
    (feed, *_) = client.get("/feeds").json()
    for param in ("lnamefirst=1", "include_club=1", "include_country=1"):
        assert param in feed["FeedPlayers"]


def test_feeds_pass_policies_on_to_urls(client: TestClient) -> None:
    (feed, *_) = client.get("/feeds", params={"fnamemaxlen": 1}).json()
    assert "fnamemaxlen=1" in feed["FeedMatches"]
    assert "fnamemaxlen=1" in feed["FeedPlayers"]


def test_feeds_post_result_from_config(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    squore_state["config"] = write_file(
        "config.toml", 'PostResult = "http://tcboard.example.org/result"\n'
    )
    feeds = client.get("/feeds").json()
    assert {f["PostResult"] for f in feeds} == {"http://tcboard.example.org/result"}


def test_feeds_section_for_unnamed_tournament(
    client: TestClient, court1: Court
) -> None:
    t = Tournament()
    t.add_court(court1)
    squoreapp.state.tournament = SquoreTournament.from_tournament(t)

    (feed,) = client.get("/feeds").json()
    assert feed["Section"] == "tptools Tournament"


# GET /init, POST /result


def test_init_redirects_to_settings_with_device_params(client: TestClient) -> None:
    resp = client.get(
        "/init",
        params={"cc": "DE", "version": 7, "ip": "192.0.2.9", "device_id": "abc"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert resp.headers["location"] == (
        "http://testserver/settings?cc=DE&version=7&ip=192.0.2.9&device_id=abc"
    )


def test_init_without_params(client: TestClient) -> None:
    resp = client.get("/init", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "http://testserver/settings"


def test_result_is_ignored_politely(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        resp = client.post("/result", json={"anything": 1}, headers=device("192.0.2.5"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "OK"
    assert "Your job here is done" in body["message"]
    assert "Result posted by remote 192.0.2.5, which we will ignore" in caplog.text


# GET /settings


def test_settings(client: TestClient) -> None:
    resp = client.get("/settings")
    assert resp.status_code == 200
    settings = resp.json()

    assert "_COMMENT" not in settings
    assert settings["customData"] == {"court": None}
    assert settings["StartupAction"] == "SelectFeedMatch"
    assert settings["kioskMode"] == "NotUsed"


def test_settings_urls_are_made_absolute(client: TestClient) -> None:
    settings = client.get("/settings").json()
    assert settings["FlagsURLs"] == "http://testserver/squore/v1/flags/%1$s.png"


def test_settings_keeps_absolute_urls(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    squore_state["settings"] = write_file(
        "settings.json",
        json.dumps({"FlagsURLs": "http://flags.example.org/%1$s.png\n/rel/%1$s.png"}),
    )
    settings = client.get("/settings").json()
    assert settings["FlagsURLs"] == (
        "http://flags.example.org/%1$s.png\nhttp://testserver/rel/%1$s.png"
    )


def test_settings_without_flags_urls(
    client: TestClient,
    squore_state: dict[str, Any],
    write_file: Callable[[str, str], pathlib.Path],
) -> None:
    squore_state["settings"] = write_file(
        "settings.json", json.dumps({"_COMMENT": "x", "Other": 1})
    )
    settings = client.get("/settings").json()
    assert settings["Other"] == 1
    assert "FlagsURLs" not in settings
    assert "_COMMENT" not in settings


def test_settings_file_not_found(
    client: TestClient, squore_state: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    squore_state["settings"] = tmp_path / "no-such-settings.json"
    resp = client.get("/settings")
    assert resp.status_code == 404
    assert "Squore settings file not found at" in resp.json()["detail"]


def test_settings_remote_settings_url_keeps_squore_placeholders(
    client: TestClient,
) -> None:
    settings = client.get("/settings").json()
    expected = (
        "http://testserver/init"
        "?cc=${countryCode}&version=${versionCode}"
        "&ip=${ipAddress}&device_id=${liveScoreDeviceId}"
    )
    assert settings["RemoteSettingsURL"] == expected
    assert settings["RemoteSettingsURL_Default"] == expected


def test_settings_include_feeds(client: TestClient) -> None:
    feeds = client.get("/settings").json()["feedPostUrls"]
    blocks = feeds.split("\n\n")
    assert len(blocks) == 2
    assert blocks[0].splitlines()[0] == "Name=Sq Test Court 1"
    assert blocks[1].splitlines()[0] == "Name=Sq Test Court 7"
    for block in blocks:
        assert {line.split("=")[0] for line in block.splitlines()} == {
            "Name",
            "FeedPlayers",
            "FeedMatches",
            "PostResult",
        }
    assert not feeds.endswith("\n")


def test_settings_without_feeds(
    client: TestClient, squore_state: dict[str, Any]
) -> None:
    squore_state["commandlineparams"] = CommandLineParams(include_feeds=False)
    settings = client.get("/settings").json()
    assert "feedPostUrls" not in settings
    assert "kioskMode" not in settings


def test_settings_kiosk_mode(client: TestClient, squore_state: dict[str, Any]) -> None:
    squore_state["commandlineparams"] = CommandLineParams(kiosk_mode=True)
    assert client.get("/settings").json()["kioskMode"] == "MatchesFromSingleFeed_1"


def test_settings_logs_the_device(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        client.get(
            "/settings",
            params={
                "device_id": "dev1",
                "cc": "DE",
                "version": 3,
                "ip": "198.51.100.1",
            },
            headers=device("192.0.2.6"),
        )
    assert "App settings request from remote 192.0.2.6" in caplog.text
    assert "for device dev1 (ip=198.51.100.1, cc=DE, v=3)" in caplog.text


@pytest.mark.parametrize(
    "ip, court_id, location_id, suffix, feed_idx",
    [
        ("192.0.2.1", 1, 1, "-1@1-C01", 0),  # by name
        ("192.0.2.2", 2, 2, "-2@2-C07", 1),  # by ID
    ],
)
def test_settings_for_device_on_a_court(
    client: TestClient,
    devmap: pathlib.Path,
    sqtournament: SquoreTournament,
    caplog: LogCaptureFixture,
    ip: str,
    court_id: int,
    location_id: int,
    suffix: str,
    feed_idx: int,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        resp = client.get(
            "/settings", params={"device_id": "dev123"}, headers=device(ip)
        )

    assert resp.status_code == 200
    settings = resp.json()
    assert settings["customData"] == {
        "court": {"id": court_id, "location_id": location_id}
    }
    assert settings["liveScoreDeviceId_customSuffix"] == suffix
    assert settings["feedPostUrl"] == feed_idx, "the feed of the court is preselected"
    assert "Pre-selected feed" in caplog.text
    # the court remembers which device it was set up with
    assert sqtournament.courts[court_id].scoredev == f"dev123{suffix}"


def test_settings_for_device_does_not_double_the_suffix(
    client: TestClient, devmap: pathlib.Path, sqtournament: SquoreTournament
) -> None:
    client.get(
        "/settings", params={"device_id": "dev123-1@1-C01"}, headers=device("192.0.2.1")
    )
    assert sqtournament.courts[1].scoredev == "dev123-1@1-C01"


def test_settings_for_device_on_a_court_without_device_id(
    client: TestClient, devmap: pathlib.Path, sqtournament: SquoreTournament
) -> None:
    resp = client.get("/settings", headers=device("192.0.2.1"))
    assert resp.status_code == 200
    assert sqtournament.courts[1].scoredev is None


def test_settings_for_device_on_a_court_without_feeds(
    client: TestClient, devmap: pathlib.Path, caplog: LogCaptureFixture
) -> None:
    squoreapp.dependency_overrides[sq.get_feed_data_for_all_courts] = lambda: []
    try:
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            settings = client.get("/settings", headers=device("192.0.2.1")).json()
    finally:
        del squoreapp.dependency_overrides[sq.get_feed_data_for_all_courts]

    assert "feedPostUrl" not in settings
    assert "There is no feed for a Court" in caplog.text


def test_settings_for_device_on_a_court_without_feeds_included(
    client: TestClient, devmap: pathlib.Path, squore_state: dict[str, Any]
) -> None:
    squore_state["commandlineparams"] = CommandLineParams(include_feeds=False)
    settings = client.get("/settings", headers=device("192.0.2.1")).json()
    assert "feedPostUrl" not in settings
    assert settings["liveScoreDeviceId_customSuffix"] == "-1@1-C01"


@pytest.mark.parametrize("ip", ["192.0.2.4", "192.0.2.99"])
def test_settings_for_unknown_device(
    client: TestClient, devmap: pathlib.Path, ip: str
) -> None:
    settings = client.get("/settings", headers=device(ip)).json()
    assert settings["customData"] == {"court": None}
    assert "liveScoreDeviceId_customSuffix" not in settings
    assert "feedPostUrl" not in settings
    assert "MQTTOtherDeviceId" not in settings


def test_settings_for_mirror_device(
    client: TestClient, devmap: pathlib.Path, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        settings = client.get("/settings", headers=device("192.0.2.3")).json()

    assert settings["MQTTOtherDeviceId"] == "abcdef-12-xyz"
    assert settings["liveScoreDeviceId_customSuffix"] == "-mirror-abcdef-12-xyz"
    assert settings["MQTTDisableInputWhenSlave"] is True
    assert settings["feedPostUrls"] is None
    assert settings["autoSuggestToPostResult"] is False
    assert settings["customData"] == {}
    assert "StartupAction" not in settings
    assert "set up to MQTT-mirror device abcdef-12-xyz" in caplog.text


def test_settings_no_mirror_if_devmap_value_is_not_a_device_id(
    client: TestClient, devmap: pathlib.Path, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        client.get("/settings", headers=device("192.0.2.4"))
    assert (
        "No mirror device found in devmap for device with IP 192.0.2.4" in caplog.text
    )


def test_settings_with_missing_devmap_warns_but_works(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        resp = client.get("/settings")
    assert resp.status_code == 200
    assert "Squore device to court map not found at" in caplog.text


# deprecated routes


def test_deprecated_route_function_redirects_permanently() -> None:
    request = Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("example.org", 80),
            "path": "/squore/feeds",
            "query_string": b"",
            "headers": [(b"host", b"example.org")],
        }
    )
    with pytest.warns(DeprecationWarning, match="deprecated in favour"):
        resp = sq.deprecated_feeds(request)

    assert resp.status_code == 308
    assert resp.headers["location"] == "http://example.org/squore/v1/feeds"


# setup_for_squore()


@pytest.fixture
def mounted(
    clictx: CliContext, restore_squoreapp: None, tmp_path: pathlib.Path
) -> TestClient:
    return TestClient(clictx.api, raise_server_exceptions=False)


async def setup(clictx: CliContext, **kwargs: Any) -> None:
    async with setup_for_squore(clictx=clictx, **kwargs) as task:
        assert task is not None
        task.close()


@pytest.mark.asyncio
async def test_setup_sets_app_state(
    clictx: CliContext, restore_squoreapp: None, tmp_path: pathlib.Path
) -> None:
    await setup(clictx)

    state = squoreapp.state.squore
    assert state["settings"] == SETTINGS_JSON_PATH
    assert state["config"] == CONFIG_TOML_PATH
    assert state["devmap"] == DEVMAP_TOML_PATH
    assert state["commandlineparams"] == CommandLineParams(
        only_this_court=False,
        max_matches_per_court=None,
        kiosk_mode=False,
        include_feeds=True,
        emulate_scoring=False,
    )


@pytest.mark.asyncio
async def test_setup_passes_command_line_params(
    clictx: CliContext, restore_squoreapp: None
) -> None:
    await setup(
        clictx,
        kiosk_mode=True,
        only_this_court=True,
        max_matches_per_court=5,
        include_feeds=False,
        emulate_scoring=True,
    )

    assert squoreapp.state.squore["commandlineparams"] == CommandLineParams(
        kiosk_mode=True,
        only_this_court=True,
        max_matches_per_court=5,
        include_feeds=False,
        emulate_scoring=True,
    )


@pytest.mark.asyncio
async def test_setup_expands_user_in_paths(
    clictx: CliContext,
    restore_squoreapp: None,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    await setup(
        clictx,
        settings_json=pathlib.Path("~/s.json"),
        config_toml=pathlib.Path("~/c.toml"),
        devmap_toml=pathlib.Path("~/d.toml"),
    )

    state = squoreapp.state.squore
    assert state["settings"] == tmp_path / "s.json"
    assert state["config"] == tmp_path / "c.toml"
    assert state["devmap"] == tmp_path / "d.toml"


@pytest.mark.asyncio
async def test_setup_mounts_squore_app_and_flags(
    clictx: CliContext, mounted: TestClient
) -> None:
    await setup(clictx)

    assert mounted.get("/squore/v1/tournament").status_code == 424
    flag = mounted.get("/squore/v1/flags/AD.png")
    assert flag.status_code == 200
    assert flag.headers["content-type"] == "image/png"
    assert mounted.get("/squore/v1/flags/nonexistent.png").status_code == 404
    assert mounted.get("/squore/tournament").status_code == 404, "not unversioned"


@pytest.mark.asyncio
async def test_setup_custom_mount_point(
    clictx: CliContext, mounted: TestClient
) -> None:
    await setup(clictx, api_mount_point="/other")

    assert mounted.get("/other/v1/tournament").status_code == 424
    assert mounted.get(f"{API_MOUNTPOINT}/v1/tournament").status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["/squore", "/other"])
async def test_setup_mounts_deprecated_routes_under_the_mount_point(
    clictx: CliContext, mounted: TestClient, prefix: str
) -> None:
    await setup(clictx, api_mount_point=prefix)

    with pytest.warns(DeprecationWarning, match="deprecated in favour"):
        resp = mounted.get(f"{prefix}/feeds", follow_redirects=False)

    assert resp.status_code == 308
    assert resp.headers["location"] == f"http://testserver{prefix}/v1/feeds"


@pytest.mark.asyncio
async def test_setup_logs(
    clictx: CliContext,
    restore_squoreapp: None,
    tmp_path: pathlib.Path,
    caplog: LogCaptureFixture,
) -> None:
    devmap = tmp_path / "devmap.toml"
    devmap.write_text('"192.0.2.1" = 1\n')

    with caplog.at_level(logging.INFO, logger=LOGGER):
        await setup(clictx, devmap_toml=devmap)

    assert f"Serving app settings from {SETTINGS_JSON_PATH}" in caplog.text
    assert f"Reading tournament & match config from {CONFIG_TOML_PATH}" in caplog.text
    assert f"Reading device to court map from {devmap}" in caplog.text
    assert "Configured the app to serve to Squore from /squore/v1" in caplog.text


@pytest.mark.asyncio
async def test_setup_does_not_mention_missing_devmap(
    clictx: CliContext,
    restore_squoreapp: None,
    tmp_path: pathlib.Path,
    caplog: LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOGGER):
        await setup(clictx, devmap_toml=tmp_path / "missing.toml")
    assert "Reading device to court map" not in caplog.text


@pytest.mark.asyncio
async def test_setup_converts_tournament_updates(
    clictx: CliContext,
    mounted: TestClient,
    tournament2: Tournament,
    caplog: LogCaptureFixture,
) -> None:
    received: list[Any] = []

    async def listen() -> None:
        async for sqt in clictx.itc.updates("sqtournament", yield_immediately=False):
            received.append(sqt)

    listener = asyncio.create_task(listen())
    try:
        await wait_for(lambda: clictx.itc.has_subscribers("sqtournament"))
        with caplog.at_level(logging.INFO, logger=LOGGER):
            async with running(setup_for_squore(clictx=clictx)):
                await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
                assert mounted.get("/squore/v1/tournament").status_code == 424

                clictx.itc.set("tournament", tournament2)
                await wait_for(lambda: len(received) == 1)
    finally:
        listener.cancel()

    (sqt,) = received
    assert isinstance(sqt, SquoreTournament)
    assert sqt.name == "Test 2"
    assert squoreapp.state.tournament is sqt
    assert "Received new tournament data" in caplog.text


@pytest.mark.asyncio
async def test_setup_end_to_end(
    clictx: CliContext, mounted: TestClient, tournament1: Tournament
) -> None:
    async with running(setup_for_squore(clictx=clictx)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        clictx.itc.set("tournament", tournament1)
        await wait_for(lambda: getattr(squoreapp.state, "tournament", None))

        feed = mounted.get("/squore/v1/matches")
        assert feed.status_code == 200
        assert feed.json()["name"] == "Test 1"
        settings = mounted.get("/squore/v1/settings")
        assert settings.status_code == 200
        assert settings.json()["FlagsURLs"] == (
            "http://testserver/squore/v1/flags/%1$s.png"
        )


# the command


@pytest.fixture
def fake_setup(mocker: MockerFixture) -> list[dict[str, Any]]:
    """Record the arguments the command passes to setup_for_squore()"""
    calls: list[dict[str, Any]] = []

    @asynccontextmanager
    async def fake(**kwargs: Any) -> Any:
        calls.append(kwargs)

        async def task() -> None: ...

        yield task()

    mocker.patch.object(sq, "setup_for_squore", fake)
    return calls


def test_squoresrv_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(squoresrv, ["--help"])
    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Mount endpoints to serve data for Squore" in output
    for opt in (
        "--kiosk-mode",
        "--only-this-court",
        "--max-matches-per-court",
        "--no-feeds",
        "--api-mount-point",
        "--settings-json",
        "--config-toml",
        "--devmap-toml",
        "--emulate-scoring",
    ):
        assert opt in output
    assert f"[default: {API_MOUNTPOINT}]" in output


@pytest.mark.asyncio
async def test_squoresrv_defaults(
    make_factory: MakeFactory, clictx: CliContext, fake_setup: list[dict[str, Any]]
) -> None:
    async with running(make_factory(squoresrv, [])()):
        pass

    assert fake_setup == [
        {
            "clictx": clictx,
            "kiosk_mode": False,
            "only_this_court": False,
            "max_matches_per_court": None,
            "include_feeds": True,
            "api_mount_point": API_MOUNTPOINT,
            "settings_json": SETTINGS_JSON_PATH,
            "config_toml": CONFIG_TOML_PATH,
            "devmap_toml": DEVMAP_TOML_PATH,
            "emulate_scoring": False,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, key, value",
    [
        (["-k"], "kiosk_mode", True),
        (["--kiosk-mode"], "kiosk_mode", True),
        (["-o"], "only_this_court", True),
        (["--only-this-court"], "only_this_court", True),
        (["-m", "3"], "max_matches_per_court", 3),
        (["--max-matches-per-court", "1"], "max_matches_per_court", 1),
        (["-n"], "include_feeds", False),
        (["--no-feeds"], "include_feeds", False),
        (["--api-mount-point", "/x"], "api_mount_point", "/x"),
        (["--settings-json", "s.json"], "settings_json", pathlib.Path("s.json")),
        (["--config-toml", "c.toml"], "config_toml", pathlib.Path("c.toml")),
        (["--devmap-toml", "d.toml"], "devmap_toml", pathlib.Path("d.toml")),
        (["-e"], "emulate_scoring", True),
        (["--emulate-scoring"], "emulate_scoring", True),
    ],
)
async def test_squoresrv_options(
    make_factory: MakeFactory,
    fake_setup: list[dict[str, Any]],
    args: list[str],
    key: str,
    value: Any,
) -> None:
    async with running(make_factory(squoresrv, args)()):
        pass

    (call,) = fake_setup
    assert call[key] == value


@pytest.mark.asyncio
async def test_squoresrv_runs_the_task_of_setup(
    make_factory: MakeFactory, fake_setup: list[dict[str, Any]]
) -> None:
    async with make_factory(squoresrv, [])() as task:
        assert asyncio.iscoroutine(task)
        await task


@pytest.mark.parametrize("value", ["0", "-1", "x"])
def test_squoresrv_rejects_bad_max_matches(
    invoke_plugin: InvokePlugin, value: str
) -> None:
    result = invoke_plugin(squoresrv, ["-m", value])
    assert result.exit_code == 2
    assert "--max-matches-per-court" in result.output


def test_squoresrv_rejects_unknown_option(make_factory: MakeFactory) -> None:
    with pytest.raises(click.NoSuchOption):
        make_factory(squoresrv, ["--bogus"])
