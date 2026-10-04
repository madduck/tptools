import json
import logging
from collections.abc import Callable

import pytest
from pytest import CaptureFixture, LogCaptureFixture
from pytest_mock import MockerFixture

from tptools import MatchSelectionParams
from tptools.ext.squore import Config, MatchesFeed, SquoreTournament
from tptools.namepolicy import PlayerNamePolicy
from tptools.tpsrv.sq_stdout import matches_feed_json, print_sqdata, sq_stdout
from tptools.tpsrv.util import CliContext

from .conftest import InvokePlugin, MakeFactory, running, wait_for


@pytest.fixture
def sqtournament() -> SquoreTournament:
    return SquoreTournament(name="Squore Test")


@pytest.fixture
def expected_feed() -> Callable[..., str]:
    def expect(tournament: SquoreTournament, indent: int | None = None) -> str:
        return (
            MatchesFeed(tournament=tournament, config=Config()).model_dump_json(
                indent=indent,
                context={
                    "matchselectionparams": MatchSelectionParams(
                        include_not_ready=True
                    ),
                    "playernamepolicy": PlayerNamePolicy(),
                },
            )
            + "\n"
        )

    return expect


@pytest.mark.asyncio
async def test_feed_is_written_to_stdout(
    sqtournament: SquoreTournament,
    capfd: CaptureFixture[str],
    expected_feed: Callable[..., str],
) -> None:
    await matches_feed_json(sqtournament)

    out = capfd.readouterr().out
    assert out == expected_feed(sqtournament)
    assert out.count("\n") == 1, "compact JSON is a single line"
    assert isinstance(json.loads(out), dict)


@pytest.mark.asyncio
@pytest.mark.parametrize("indent", [1, 2, 4])
async def test_feed_indent(
    sqtournament: SquoreTournament,
    capfd: CaptureFixture[str],
    expected_feed: Callable[..., str],
    indent: int,
) -> None:
    await matches_feed_json(sqtournament, indent=indent)

    out = capfd.readouterr().out
    assert out == expected_feed(sqtournament, indent)
    assert out.splitlines()[1].startswith(" " * indent + '"')


@pytest.mark.asyncio
async def test_feed_logs(
    sqtournament: SquoreTournament,
    capfd: CaptureFixture[str],
    caplog: LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        await matches_feed_json(sqtournament)
    assert "Squore tournament changed, printing Squore data to stdout" in caplog.text


@pytest.mark.asyncio
async def test_print_sqdata_prints_current_value_immediately(
    clictx: CliContext, mocker: MockerFixture, sqtournament: SquoreTournament
) -> None:
    write = mocker.patch("tptools.tpsrv.sq_stdout.nonblocking_write")
    clictx.itc.set("sqtournament", sqtournament)

    async with running(print_sqdata(clictx, indent=None)):
        await wait_for(lambda: write.call_count == 1)

    assert write.call_args.args[0].endswith("\n")


@pytest.mark.asyncio
async def test_print_sqdata_waits_if_there_is_no_value_yet(
    clictx: CliContext, mocker: MockerFixture, sqtournament: SquoreTournament
) -> None:
    write = mocker.patch("tptools.tpsrv.sq_stdout.nonblocking_write")

    async with running(print_sqdata(clictx, indent=None)):
        await wait_for(lambda: clictx.itc.has_subscribers("sqtournament"))
        write.assert_not_called()

        clictx.itc.set("sqtournament", sqtournament)
        await wait_for(lambda: write.call_count == 1)

        clictx.itc.set("sqtournament", None)
        clictx.itc.set("sqtournament", SquoreTournament(name="Second"))
        await wait_for(lambda: write.call_count == 2)

    assert write.call_count == 2


@pytest.mark.asyncio
async def test_print_sqdata_listens_to_sqtournament_not_tournament(
    clictx: CliContext, mocker: MockerFixture
) -> None:
    write = mocker.patch("tptools.tpsrv.sq_stdout.nonblocking_write")

    async with running(print_sqdata(clictx, indent=None)):
        await wait_for(lambda: clictx.itc.has_subscribers("sqtournament"))
        assert not clictx.itc.has_subscribers("tournament")
        clictx.itc.set("tournament", SquoreTournament(name="Wrong key"))

    write.assert_not_called()


@pytest.mark.asyncio
async def test_print_sqdata_passes_indent(
    clictx: CliContext, mocker: MockerFixture, sqtournament: SquoreTournament
) -> None:
    write = mocker.patch("tptools.tpsrv.sq_stdout.nonblocking_write")
    clictx.itc.set("sqtournament", sqtournament)

    async with running(print_sqdata(clictx, indent=3)):
        await wait_for(lambda: write.call_count == 1)

    assert write.call_args.args[0].splitlines()[1].startswith("   " + '"')


# the command


def test_sq_stdout_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(sq_stdout, ["--help"])
    assert result.exit_code == 0
    assert "Output data as sent to Squore to stdout" in result.output
    assert "--indent" in result.output


@pytest.mark.parametrize("indent", ["0", "-1", "abc"])
def test_sq_stdout_rejects_bad_indent(invoke_plugin: InvokePlugin, indent: str) -> None:
    result = invoke_plugin(sq_stdout, ["-i", indent])
    assert result.exit_code == 2
    assert "--indent" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, multiline", [([], False), (["-i", "2"], True), (["--indent", "2"], True)]
)
async def test_sq_stdout_command(
    make_factory: MakeFactory,
    clictx: CliContext,
    mocker: MockerFixture,
    sqtournament: SquoreTournament,
    args: list[str],
    multiline: bool,
) -> None:
    write = mocker.patch("tptools.tpsrv.sq_stdout.nonblocking_write")
    clictx.itc.set("sqtournament", sqtournament)

    async with running(make_factory(sq_stdout, args)()):
        await wait_for(lambda: write.call_count == 1)

    assert (write.call_args.args[0].count("\n") > 1) is multiline
