import asyncio
import json
import logging
from typing import Any

import click
import pytest
from httpx import URL
from pytest import LogCaptureFixture
from pytest_mock import AsyncMockType, MockerFixture

from tptools import Tournament
from tptools.tpsrv.post import post, post_to_urls, post_tournament
from tptools.tpsrv.util import CliContext, PostData

from .conftest import InvokePlugin, MakeFactory, running, wait_for


@pytest.fixture
def http_request(mocker: MockerFixture) -> AsyncMockType:
    mock: AsyncMockType = mocker.patch(
        "tptools.tpsrv.post.http_request", new_callable=mocker.AsyncMock
    )
    return mock


@pytest.fixture
def urls() -> list[URL]:
    return [URL("http://one.example.org/a"), URL("https://two.example.org/b")]


# post_to_urls


@pytest.mark.asyncio
async def test_post_to_urls_posts_to_every_url(
    http_request: AsyncMockType, urls: list[URL], tournament1: Tournament
) -> None:
    await post_to_urls(tournament1, urls, cookie=1234)

    assert http_request.await_count == len(urls)
    assert sorted(str(c.kwargs["url"]) for c in http_request.call_args_list) == sorted(
        str(u) for u in urls
    )
    for call in http_request.call_args_list:
        assert call.kwargs["method"] == "POST"


@pytest.mark.asyncio
async def test_post_to_urls_wraps_tournament_with_cookie(
    http_request: AsyncMockType, urls: list[URL], tournament1: Tournament
) -> None:
    await post_to_urls(tournament1, urls[:1], cookie=1234)

    data = http_request.call_args.kwargs["data"]
    assert isinstance(data, PostData)
    assert data.cookie == 1234
    assert data.data == tournament1


@pytest.mark.asyncio
async def test_post_to_urls_data_serialises_as_expected_by_tp_recv(
    http_request: AsyncMockType, urls: list[URL], tournament1: Tournament
) -> None:
    await post_to_urls(tournament1, urls[:1], cookie=99)

    data = http_request.call_args.kwargs["data"]
    parsed = PostData[Tournament].model_validate_json(data.model_dump_json())
    assert parsed.cookie == 99
    assert parsed.data == tournament1


@pytest.mark.asyncio
@pytest.mark.parametrize("retries", [1, 5])
async def test_post_to_urls_passes_retries(
    http_request: AsyncMockType, urls: list[URL], retries: int
) -> None:
    await post_to_urls(Tournament(), urls, cookie=1, retries=retries)
    assert {c.kwargs["retries"] for c in http_request.call_args_list} == {retries}


@pytest.mark.asyncio
async def test_post_to_urls_default_retries(
    http_request: AsyncMockType, urls: list[URL]
) -> None:
    await post_to_urls(Tournament(), urls, cookie=1)
    assert {c.kwargs["retries"] for c in http_request.call_args_list} == {1}


@pytest.mark.asyncio
async def test_post_to_urls_without_urls(
    http_request: AsyncMockType, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        await post_to_urls(Tournament(), [], cookie=1)

    http_request.assert_not_called()
    assert "posting to 0 URLs" in caplog.text


@pytest.mark.asyncio
async def test_post_to_urls_posts_concurrently(
    mocker: MockerFixture, urls: list[URL]
) -> None:
    started = asyncio.Event()
    in_flight = 0
    max_in_flight = 0

    async def slow(**kwargs: Any) -> None:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        if in_flight == len(urls):
            started.set()
        await asyncio.wait_for(started.wait(), 2)
        in_flight -= 1

    mocker.patch("tptools.tpsrv.post.http_request", side_effect=slow)
    await post_to_urls(Tournament(), urls, cookie=1)
    assert max_in_flight == len(urls)


@pytest.mark.asyncio
async def test_post_to_urls_logs(
    http_request: AsyncMockType,
    urls: list[URL],
    caplog: LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        await post_to_urls(Tournament(), urls, cookie=1)

    assert f"posting to {len(urls)} URLs" in caplog.text
    assert f"Done posting to {len(urls)} URLs" in caplog.text
    assert caplog.text.count("Task done:") == len(urls)


# post_tournament


@pytest.mark.asyncio
async def test_post_tournament_posts_current_value_immediately(
    clictx: CliContext,
    http_request: AsyncMockType,
    urls: list[URL],
    tournament1: Tournament,
) -> None:
    clictx.itc.set("tournament", tournament1)

    async with running(post_tournament(clictx, urls, retries=2)):
        await wait_for(lambda: http_request.await_count == len(urls))

    for call in http_request.call_args_list:
        assert call.kwargs["data"].data == tournament1
        assert call.kwargs["retries"] == 2


@pytest.mark.asyncio
async def test_post_tournament_uses_hash_of_clictx_as_cookie(
    clictx: CliContext,
    http_request: AsyncMockType,
    urls: list[URL],
) -> None:
    """tp_recv rejects what it posted itself by comparing against this cookie"""
    clictx.itc.set("tournament", Tournament())

    async with running(post_tournament(clictx, urls[:1], retries=1)):
        await wait_for(lambda: http_request.await_count == 1)

    assert http_request.call_args.kwargs["data"].cookie == hash(clictx)


@pytest.mark.asyncio
async def test_post_tournament_waits_for_tournament_and_posts_each_change(
    clictx: CliContext, http_request: AsyncMockType, urls: list[URL]
) -> None:
    async with running(post_tournament(clictx, urls[:1], retries=1)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        http_request.assert_not_called()

        clictx.itc.set("tournament", Tournament(name="One"))
        await wait_for(lambda: http_request.await_count == 1)

        clictx.itc.set("tournament", Tournament(name="Two"))
        await wait_for(lambda: http_request.await_count == 2)

    names = [c.kwargs["data"].data.name for c in http_request.call_args_list]
    assert names == ["One", "Two"]


# the command


def test_post_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(post, ["--help"])
    assert result.exit_code == 0
    assert "Post raw (TP) JSON data to URLs on change" in result.output
    assert "--url" in result.output and "--retries" in result.output


def test_post_requires_a_url(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(post, [])
    assert result.exit_code == 2
    assert "Missing option '--url'" in result.output


@pytest.mark.parametrize("bad", ["relative", "/path/only", "example.org"])
def test_post_rejects_relative_urls(invoke_plugin: InvokePlugin, bad: str) -> None:
    result = invoke_plugin(post, ["-u", bad])
    assert result.exit_code == 2
    assert "URL is not absolute" in result.output


@pytest.mark.parametrize("retries", ["0", "-1", "x"])
def test_post_rejects_bad_retries(invoke_plugin: InvokePlugin, retries: str) -> None:
    result = invoke_plugin(post, ["-u", "http://example.org", "--retries", retries])
    assert result.exit_code == 2
    assert "--retries" in result.output


def test_post_bad_url_raises_for_factory(make_factory: MakeFactory) -> None:
    with pytest.raises(click.BadParameter, match="not absolute"):
        make_factory(post, ["-u", "nope"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, expected_urls, expected_retries",
    [
        (["-u", "http://one.example.org/"], ["http://one.example.org/"], 1),
        (
            ["--url", "http://one.example.org/", "-u", "https://two.example.org/x"],
            ["http://one.example.org/", "https://two.example.org/x"],
            1,
        ),
        (["-u", "http://one.example.org/", "-r", "4"], ["http://one.example.org/"], 4),
        (
            ["-u", "http://one.example.org/", "--retries", "2"],
            ["http://one.example.org/"],
            2,
        ),
    ],
)
async def test_post_command(
    make_factory: MakeFactory,
    clictx: CliContext,
    http_request: AsyncMockType,
    args: list[str],
    expected_urls: list[str],
    expected_retries: int,
) -> None:
    clictx.itc.set("tournament", Tournament(name="Posted"))

    async with running(make_factory(post, args)()):
        await wait_for(lambda: http_request.await_count == len(expected_urls))

    assert sorted(str(c.kwargs["url"]) for c in http_request.call_args_list) == sorted(
        expected_urls
    )
    assert {c.kwargs["retries"] for c in http_request.call_args_list} == {
        expected_retries
    }
    body = json.loads(http_request.call_args.kwargs["data"].model_dump_json())
    assert body["data"]["name"] == "Posted"
