import logging
from collections.abc import Generator

import click
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import URL
from pytest import LogCaptureFixture
from pytest_mock import AsyncMockType, MockerFixture

from tptools import Tournament
from tptools.tpsrv.tp_recv import (
    API_MOUNTPOINT,
    TPRECV_PATH_VERSION,
    recvapp,
    setup_to_receive_tournament_post,
    tp_recv,
)
from tptools.tpsrv.util import CliContext, PostData

from .conftest import InvokePlugin, MakeFactory

BASE = f"{API_MOUNTPOINT}/{TPRECV_PATH_VERSION}"


@pytest.fixture(autouse=True)
def reset_recvapp_state() -> Generator[None]:
    """recvapp is a module-level app that gets its clictx assigned on set-up"""
    had = hasattr(recvapp.state, "clictx")
    yield
    if not had and hasattr(recvapp.state, "clictx"):
        del recvapp.state.clictx


@pytest.fixture
def client(clictx: CliContext) -> TestClient:
    """A client for clictx.api, with recvapp mounted the way the plugin does it"""
    recvapp.state.clictx = clictx
    clictx.api.mount(path=BASE, app=recvapp, name="squore")
    return TestClient(clictx.api)


def post_body(tournament: Tournament, cookie: int = 1) -> str:
    return PostData[Tournament](cookie=cookie, data=tournament).model_dump_json()


# POST /tournament


def test_post_tournament_stores_tournament(
    client: TestClient, clictx: CliContext, tournament1: Tournament
) -> None:
    resp = client.post(f"{BASE}/tournament", content=post_body(tournament1))

    assert resp.status_code == 200
    assert resp.json() == {"status": f"Received tournament: {tournament1}"}
    assert clictx.itc.get("tournament") == tournament1


def test_post_tournament_notifies_listeners(
    client: TestClient, clictx: CliContext, mocker: MockerFixture
) -> None:
    fire = mocker.spy(clictx.itc, "fire")
    client.post(f"{BASE}/tournament", content=post_body(Tournament(name="x")))
    fire.assert_called_once_with("tournament")


def test_post_tournament_replaces_previous(
    client: TestClient, clictx: CliContext
) -> None:
    client.post(f"{BASE}/tournament", content=post_body(Tournament(name="old")))
    client.post(f"{BASE}/tournament", content=post_body(Tournament(name="new")))
    assert clictx.itc.get("tournament").name == "new"


def test_post_tournament_rejects_own_data(
    client: TestClient, clictx: CliContext, tournament1: Tournament
) -> None:
    resp = client.post(
        f"{BASE}/tournament", content=post_body(tournament1, cookie=hash(clictx))
    )

    assert resp.status_code == 508
    assert resp.json() == {"detail": "Won't receive my own data"}
    assert not clictx.itc.knows_about("tournament")


def test_post_tournament_logs_peer(
    client: TestClient, clictx: CliContext, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        client.post(
            f"{BASE}/tournament",
            content=post_body(Tournament(name="x")),
            headers={"X-Forwarded-For": "192.0.2.9"},
        )
    assert "Received tournament from tptools at 192.0.2.9:" in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        "",
        "not json",
        "{}",
        '{"cookie": 1}',
        '{"cookie": "x", "data": {}}',
        '{"cookie": 1, "data": {"name": 5, "entries": "x"}}',
    ],
)
def test_post_tournament_rejects_invalid_bodies(
    client: TestClient, clictx: CliContext, body: str
) -> None:
    resp = TestClient(clictx.api, raise_server_exceptions=False).post(
        f"{BASE}/tournament", content=body
    )

    assert resp.status_code >= 400
    assert not clictx.itc.knows_about("tournament")


# GET /tournament


def test_get_tournament_before_any_was_received(client: TestClient) -> None:
    resp = client.get(f"{BASE}/tournament")
    assert resp.status_code == 424
    assert resp.json() == {"detail": "Tournament not loaded"}


def test_get_tournament(
    client: TestClient, clictx: CliContext, tournament1: Tournament
) -> None:
    clictx.itc.set("tournament", tournament1)

    resp = client.get(f"{BASE}/tournament")

    assert resp.status_code == 200
    assert Tournament.model_validate(resp.json()) == tournament1


def test_post_then_get_roundtrip(client: TestClient, tournament1: Tournament) -> None:
    client.post(f"{BASE}/tournament", content=post_body(tournament1))

    resp = client.get(f"{BASE}/tournament")

    assert resp.status_code == 200
    assert Tournament.model_validate(resp.json()) == tournament1


def test_get_tournament_logs_peer(
    client: TestClient, clictx: CliContext, caplog: LogCaptureFixture
) -> None:
    clictx.itc.set("tournament", Tournament(name="Logged"))
    with caplog.at_level(logging.DEBUG):
        client.get(f"{BASE}/tournament", headers={"X-Forwarded-For": "192.0.2.5"})
    assert "tournament request from 192.0.2.5:" in caplog.text


@pytest.mark.parametrize("method", ["put", "delete", "patch"])
def test_tournament_endpoint_methods(client: TestClient, method: str) -> None:
    assert getattr(client, method)(f"{BASE}/tournament").status_code == 405


# setup_to_receive_tournament_post


@pytest.fixture
def bootstrap(mocker: MockerFixture) -> AsyncMockType:
    mock: AsyncMockType = mocker.patch(
        "tptools.tpsrv.tp_recv.bootstrap_tournament_from_url",
        new_callable=mocker.AsyncMock,
    )
    return mock


@pytest.mark.asyncio
async def test_setup_mounts_recvapp_at_default_path(clictx: CliContext) -> None:
    async with setup_to_receive_tournament_post(clictx) as bootstrapper:
        assert bootstrapper is not None
        bootstrapper.close()

    assert recvapp.state.clictx is clictx
    mounts = [r for r in clictx.api.routes if getattr(r, "name", None) == "squore"]
    assert [m.path for m in mounts] == [BASE]
    assert BASE == "/tptools/v1"


@pytest.mark.asyncio
async def test_setup_custom_mountpoint(clictx: CliContext) -> None:
    async with setup_to_receive_tournament_post(
        clictx, api_mount_point="/custom"
    ) as bootstrapper:
        assert bootstrapper is not None
        bootstrapper.close()

    client = TestClient(clictx.api)
    assert client.get("/custom/v1/tournament").status_code == 424
    assert client.get(f"{BASE}/tournament").status_code == 404


@pytest.mark.asyncio
async def test_setup_logs(clictx: CliContext, caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        async with setup_to_receive_tournament_post(clictx) as bootstrapper:
            assert bootstrapper is not None
            bootstrapper.close()
    assert f"Configured the app to receive tptools data at {BASE}" in caplog.text


@pytest.mark.asyncio
async def test_setup_without_url_sets_tournament_to_none(
    clictx: CliContext, bootstrap: AsyncMockType
) -> None:
    async with setup_to_receive_tournament_post(clictx) as bootstrapper:
        assert not clictx.itc.knows_about("tournament"), "not before it is awaited"
        assert bootstrapper is not None
        await bootstrapper

    assert clictx.itc.knows_about("tournament")
    assert clictx.itc.get("tournament") is None
    bootstrap.assert_not_called()


@pytest.mark.asyncio
async def test_setup_with_url_bootstraps_from_url(
    clictx: CliContext, bootstrap: AsyncMockType, tournament1: Tournament
) -> None:
    bootstrap.return_value = tournament1
    url = URL("http://other.example.org/tptools/v1/tournament")

    async with setup_to_receive_tournament_post(clictx, url) as bootstrapper:
        assert bootstrapper is not None
        await bootstrapper

    bootstrap.assert_awaited_once_with(Tournament, url)
    assert clictx.itc.get("tournament") == tournament1


@pytest.mark.asyncio
async def test_setup_with_url_that_yields_nothing(
    clictx: CliContext, bootstrap: AsyncMockType
) -> None:
    bootstrap.return_value = None
    url = URL("http://other.example.org/tptools/v1/tournament")

    async with setup_to_receive_tournament_post(clictx, url) as bootstrapper:
        assert bootstrapper is not None
        await bootstrapper

    assert clictx.itc.knows_about("tournament")
    assert clictx.itc.get("tournament") is None


# the command


def test_tp_recv_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(tp_recv, ["--help"])
    assert result.exit_code == 0
    assert "Mount endpoints to receive tournament data" in result.output
    assert "--api-mount-point" in result.output
    assert "--load-from-url" in result.output
    assert f"[default: {API_MOUNTPOINT}]" in " ".join(result.output.split())


@pytest.mark.parametrize("bad", ["relative", "/no/host", "example.org/x"])
def test_tp_recv_rejects_relative_url(invoke_plugin: InvokePlugin, bad: str) -> None:
    result = invoke_plugin(tp_recv, ["-u", bad])
    assert result.exit_code == 2
    assert "URL is not absolute" in result.output


def test_tp_recv_bad_url_raises_for_factory(make_factory: MakeFactory) -> None:
    with pytest.raises(click.BadParameter):
        make_factory(tp_recv, ["--load-from-url", "nope"])


@pytest.mark.asyncio
async def test_tp_recv_command_defaults(
    make_factory: MakeFactory, clictx: CliContext, bootstrap: AsyncMockType
) -> None:
    async with make_factory(tp_recv, [])() as task:
        assert task is not None
        await task

    assert clictx.itc.get("tournament") is None
    bootstrap.assert_not_called()
    assert TestClient(clictx.api).get(f"{BASE}/tournament").status_code == 424


@pytest.mark.asyncio
@pytest.mark.parametrize("option", ["-u", "--load-from-url"])
async def test_tp_recv_command_load_from_url(
    make_factory: MakeFactory,
    clictx: CliContext,
    bootstrap: AsyncMockType,
    tournament1: Tournament,
    option: str,
) -> None:
    bootstrap.return_value = tournament1

    async with make_factory(
        tp_recv, [option, "http://other.example.org/tptools/v1/tournament"]
    )() as task:
        assert task is not None
        await task

    ((cls, url),) = [c.args for c in bootstrap.await_args_list]
    assert cls is Tournament
    assert str(url) == "http://other.example.org/tptools/v1/tournament"
    assert TestClient(clictx.api).get(f"{BASE}/tournament").json()["name"] == "Test 1"


@pytest.mark.asyncio
async def test_tp_recv_command_mountpoint(
    make_factory: MakeFactory, clictx: CliContext, bootstrap: AsyncMockType
) -> None:
    async with make_factory(tp_recv, ["--api-mount-point", "/elsewhere"])() as task:
        assert task is not None
        await task

    assert TestClient(clictx.api).get("/elsewhere/v1/tournament").status_code == 424


@pytest.mark.asyncio
async def test_two_instances_exchange_tournaments_with_loop_protection(
    tournament1: Tournament,
) -> None:
    """What `tpsrv tp-recv` receives from a `post` of another instance is
    accepted, but what it would receive from its own `post` is not"""
    from click_async_plugins import ITC

    mine = CliContext(api=FastAPI(), itc=ITC())
    other = CliContext(api=FastAPI(), itc=ITC())

    recvapp.state.clictx = mine
    mine.api.mount(path=BASE, app=recvapp, name="squore")
    client = TestClient(mine.api)

    from_other = client.post(
        f"{BASE}/tournament", content=post_body(tournament1, cookie=hash(other))
    )
    from_self = client.post(
        f"{BASE}/tournament", content=post_body(tournament1, cookie=hash(mine))
    )

    assert (from_other.status_code, from_self.status_code) == (200, 508)
