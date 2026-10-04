import json
import logging
from collections.abc import Callable
from contextlib import nullcontext
from functools import partial
from typing import Annotated, Any, ContextManager

import click
import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from httpx import URL, AsyncClient, MockTransport, Request, Response
from pydantic import BaseModel
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from tptools import Tournament
from tptools.tpsrv.util import (
    CliContext,
    PostData,
    bootstrap_tournament_from_url,
    get_clictx,
    get_peer,
    get_tournament,
    http_request,
    validate_url,
    validate_urls,
)


@pytest.fixture
def fake_click_context() -> click.Context:
    return None  # type: ignore[return-value]


@pytest.mark.parametrize(
    "inp, res",
    [
        (None, nullcontext([])),
        ("http://example.org", nullcontext(["http://example.org"])),
        ("https://example.net", nullcontext(["https://example.net"])),
        ("url", pytest.raises(click.BadParameter, match="not absolute")),
        ("/example.net/foo", pytest.raises(click.BadParameter, match="not absolute")),
        (True, pytest.raises(click.BadParameter, match="must be a string")),
        (1, pytest.raises(click.BadParameter, match="must be a string")),
        # TODO:test for InvalidURL
    ],
)
def test_validate_urls(
    fake_click_context: click.Context,
    inp: Any,
    res: ContextManager[Any],
) -> None:
    with res as out:
        assert [str(u) for u in validate_urls(fake_click_context, "url", (inp,))] == out


def test_validate_url_none(fake_click_context: click.Context) -> None:
    assert validate_url(fake_click_context, "url", None) is None


def test_validate_url_returns_url(fake_click_context: click.Context) -> None:
    url = validate_url(fake_click_context, "url", "http://example.org/x")
    assert isinstance(url, URL)
    assert str(url) == "http://example.org/x"


def test_validate_urls_empty(fake_click_context: click.Context) -> None:
    assert validate_urls(fake_click_context, "url", ()) == []  # type: ignore[arg-type]


def test_validate_urls_multiple(fake_click_context: click.Context) -> None:
    urls = validate_urls(
        fake_click_context,
        "url",
        ("http://example.org", "https://example.net/foo"),  # type: ignore[arg-type]
    )
    assert [str(u) for u in urls] == ["http://example.org", "https://example.net/foo"]


def test_validate_urls_stops_at_invalid_url(fake_click_context: click.Context) -> None:
    with pytest.raises(click.BadParameter, match="not absolute"):
        validate_urls(
            fake_click_context,
            "url",
            ("http://example.org", "relative"),  # type: ignore[arg-type]
        )


# CliContext


@pytest.fixture
def clictx() -> CliContext:
    from click_async_plugins import ITC

    return CliContext(api=FastAPI(), itc=ITC())


def test_clictx_defaults(clictx: CliContext) -> None:
    assert clictx.watcher is None


def test_clictx_hash_is_stable_and_follows_api(clictx: CliContext) -> None:
    assert hash(clictx) == hash(clictx.api)
    assert hash(clictx) == hash(clictx)


def test_clictx_hash_differs_per_api() -> None:
    from click_async_plugins import ITC

    a = CliContext(api=FastAPI(), itc=ITC())
    b = CliContext(api=FastAPI(), itc=ITC())
    assert hash(a) != hash(b)


# FastAPI dependencies


@pytest.fixture
def depapp(clictx: CliContext) -> FastAPI:
    app = FastAPI()
    app.state.clictx = clictx

    @app.get("/clictx")
    def clictx_ep(ctx: Annotated[CliContext, Depends(get_clictx)]) -> dict[str, Any]:
        return {"same": ctx is clictx}

    @app.get("/peer")
    def peer_ep(peer: Annotated[str, Depends(get_peer)]) -> str:
        return peer

    @app.get("/tournament")
    def tournament_ep(
        tournament: Annotated[Tournament, Depends(get_tournament)],
    ) -> str:
        return str(tournament.name)

    return app


@pytest.fixture
def depclient(depapp: FastAPI) -> TestClient:
    return TestClient(depapp)


def test_get_clictx(depclient: TestClient) -> None:
    resp = depclient.get("/clictx")
    assert resp.status_code == 200
    assert resp.json() == {"same": True}


def test_get_peer(depclient: TestClient) -> None:
    resp = depclient.get("/peer")
    assert resp.json() == "testclient:50000"


def test_get_peer_prefers_forwarded_for_host(depclient: TestClient) -> None:
    resp = depclient.get("/peer", headers={"X-Forwarded-For": "10.0.0.1"})
    assert resp.json() == "10.0.0.1:50000"


def test_get_peer_without_client() -> None:
    class Conn:
        client = None
        headers: dict[str, str] = {}

    assert get_peer(Conn()) == "(unknown)"  # type: ignore[arg-type]


def test_get_tournament_not_loaded(depclient: TestClient) -> None:
    resp = depclient.get("/tournament")
    assert resp.status_code == 424
    assert resp.json() == {"detail": "Tournament not loaded"}


def test_get_tournament_explicitly_none(
    depclient: TestClient, clictx: CliContext
) -> None:
    # tp_recv sets the tournament to None when there is nothing to bootstrap from
    clictx.itc.set("tournament", None)
    assert depclient.get("/tournament").status_code == 424


def test_get_tournament(depclient: TestClient, clictx: CliContext) -> None:
    clictx.itc.set("tournament", Tournament(name="Loaded"))
    resp = depclient.get("/tournament")
    assert resp.status_code == 200
    assert resp.json() == "Loaded"


# http_request


class Payload(BaseModel):
    answer: int = 42


@pytest.fixture
def url() -> URL:
    return URL("http://example.org/api")


@pytest.fixture
def sleep(mocker: MockerFixture) -> Any:
    return mocker.patch("tptools.tpsrv.util.asyncio.sleep")


@pytest.fixture
def mock_transport(
    mocker: MockerFixture,
) -> Callable[[Callable[[Request], Response]], list[Request]]:
    """Route AsyncClient() inside tpsrv.util through a MockTransport"""

    def install(handler: Callable[[Request], Response]) -> list[Request]:
        seen: list[Request] = []

        def recording(request: Request) -> Response:
            seen.append(request)
            return handler(request)

        mocker.patch(
            "tptools.tpsrv.util.AsyncClient",
            partial(AsyncClient, transport=MockTransport(recording)),
        )
        return seen

    return install


@pytest.mark.asyncio
async def test_http_request_get(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    caplog: LogCaptureFixture,
) -> None:
    seen = mock_transport(lambda _: Response(200, json={"a": 1}))
    with caplog.at_level(logging.INFO):
        assert await http_request("GET", url) == {"a": 1}

    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url == url
    assert seen[0].content == b""
    assert "content-type" not in seen[0].headers
    assert "yielded a response of" in caplog.text


@pytest.mark.asyncio
async def test_http_request_post_model_as_json(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
) -> None:
    seen = mock_transport(lambda _: Response(200, json={}))
    assert await http_request("POST", url, data=Payload()) == {}

    assert seen[0].method == "POST"
    assert seen[0].headers["content-type"] == "application/json"
    assert json.loads(seen[0].content) == {"answer": 42}


@pytest.mark.asyncio
async def test_http_request_postdata_envelope(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
) -> None:
    seen = mock_transport(lambda _: Response(200, json={}))
    data = PostData[Payload](cookie=7, data=Payload(answer=1))
    await http_request("POST", url, data=data)

    assert json.loads(seen[0].content) == {"cookie": 7, "data": {"answer": 1}}


@pytest.mark.asyncio
async def test_http_request_custom_to_json_fn(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
) -> None:
    seen = mock_transport(lambda _: Response(200, json={}))
    await http_request("PUT", url, data=Payload(), to_json_fn=lambda _: "custom")

    assert seen[0].method == "PUT"
    assert seen[0].content == b"custom"
    assert seen[0].headers["content-type"] == "application/json"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [201, 301, 404, 500])
async def test_http_request_non_200_gives_none(
    url: URL,
    status: int,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    caplog: LogCaptureFixture,
    sleep: Any,
) -> None:
    seen = mock_transport(lambda _: Response(status, json={"a": 1}))
    with caplog.at_level(logging.WARNING):
        assert await http_request("GET", url) is None

    assert f"yielded status {status}" in caplog.text
    # an HTTP status is an answer, not a transport problem: no retries
    assert len(seen) == 1
    sleep.assert_not_called()


@pytest.mark.asyncio
async def test_http_request_invalid_json_gives_none(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    caplog: LogCaptureFixture,
    sleep: Any,
) -> None:
    seen = mock_transport(lambda _: Response(200, content=b"not json"))
    with caplog.at_level(logging.WARNING):
        assert await http_request("GET", url) is None

    assert "invalid JSON response" in caplog.text
    assert len(seen) == 1
    sleep.assert_not_called()


@pytest.mark.asyncio
async def test_http_request_retries_then_succeeds(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    caplog: LogCaptureFixture,
    sleep: Any,
) -> None:
    responses: list[Response | Exception] = [
        httpx.ConnectError("boom"),
        httpx.ReadTimeout("slow"),
        Response(200, json={"ok": True}),
    ]

    def handler(request: Request) -> Response:
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    seen = mock_transport(handler)
    with caplog.at_level(logging.WARNING):
        assert await http_request("GET", url, sleep=0.25) == {"ok": True}

    assert len(seen) == 3
    assert sleep.await_count == 2
    sleep.assert_awaited_with(0.25)
    assert caplog.text.count("retrying") == 2


@pytest.mark.asyncio
async def test_http_request_gives_up_after_retries(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    caplog: LogCaptureFixture,
    sleep: Any,
) -> None:
    def handler(request: Request) -> Response:
        raise httpx.ConnectError("down")

    seen = mock_transport(handler)
    with caplog.at_level(logging.WARNING):
        assert await http_request("GET", url, retries=2) is None

    # the initial attempt plus two retries
    assert len(seen) == 3
    assert sleep.await_count == 2
    assert "Giving up GET request" in caplog.text


@pytest.mark.asyncio
async def test_http_request_zero_retries(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
    sleep: Any,
) -> None:
    def handler(request: Request) -> Response:
        raise httpx.ConnectError("down")

    seen = mock_transport(handler)
    assert await http_request("GET", url, retries=0) is None
    assert len(seen) == 1
    sleep.assert_not_called()


# bootstrap_tournament_from_url


@pytest.mark.asyncio
async def test_bootstrap_tournament_from_url(
    url: URL, mocker: MockerFixture, caplog: LogCaptureFixture
) -> None:
    fetch = mocker.patch(
        "tptools.tpsrv.util.http_request",
        return_value=Tournament(name="Remote").model_dump(mode="json"),
    )
    with caplog.at_level(logging.INFO):
        tournament = await bootstrap_tournament_from_url(Tournament, url)

    fetch.assert_awaited_once_with("GET", url)
    assert tournament == Tournament(name="Remote")
    assert "Fetched initial Tournament" in caplog.text


@pytest.mark.asyncio
async def test_bootstrap_tournament_from_url_fetch_fails(
    url: URL, mocker: MockerFixture, caplog: LogCaptureFixture
) -> None:
    mocker.patch("tptools.tpsrv.util.http_request", return_value=None)
    with caplog.at_level(logging.WARNING):
        assert await bootstrap_tournament_from_url(Tournament, url) is None

    assert "Failed to fetch initial Tournament" in caplog.text


@pytest.mark.asyncio
async def test_bootstrap_tournament_from_url_invalid_data(
    url: URL, mocker: MockerFixture, caplog: LogCaptureFixture
) -> None:
    mocker.patch(
        "tptools.tpsrv.util.http_request", return_value={"name": 5, "entries": "x"}
    )
    with caplog.at_level(logging.WARNING):
        assert await bootstrap_tournament_from_url(Tournament, url) is None

    assert "does not validate as Tournament" in caplog.text


@pytest.mark.asyncio
async def test_bootstrap_end_to_end_over_mock_transport(
    url: URL,
    mock_transport: Callable[[Callable[[Request], Response]], list[Request]],
) -> None:
    payload = Tournament(name="Wire").model_dump(mode="json")
    mock_transport(lambda _: Response(200, json=payload))

    assert await bootstrap_tournament_from_url(Tournament, url) == Tournament(
        name="Wire"
    )
