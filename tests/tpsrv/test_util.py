from contextlib import nullcontext
from typing import Any, ContextManager

import click
import pytest

from tptools.tpsrv.util import validate_urls


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
