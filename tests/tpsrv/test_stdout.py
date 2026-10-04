import asyncio
import json
import logging
from collections.abc import Callable

import pytest
from pytest import CaptureFixture, LogCaptureFixture
from pytest_mock import MockerFixture

from tptools import MatchSelectionParams, Tournament
from tptools.tpsrv.stdout import print_tournament, stdout, tournament_model_dump_json
from tptools.tpsrv.util import CliContext

from .conftest import InvokePlugin, MakeFactory, running, wait_for


@pytest.fixture
def expected_json() -> Callable[..., str]:
    def expect(tournament: Tournament, indent: int | None = None) -> str:
        return (
            tournament.model_dump_json(
                indent=indent,
                context={
                    "matchselectionparams": MatchSelectionParams(include_not_ready=True)
                },
            )
            + "\n"
        )

    return expect


@pytest.mark.asyncio
async def test_dump_writes_json_and_newline_to_stdout(
    tournament1: Tournament, capfd: CaptureFixture[str]
) -> None:
    await tournament_model_dump_json(tournament1)

    out = capfd.readouterr().out
    assert out.endswith("}\n")
    assert out.count("\n") == 1, "compact JSON is a single line"
    assert json.loads(out)["name"] == "Test 1"
    assert Tournament.model_validate_json(out) == tournament1


@pytest.mark.asyncio
async def test_dump_matches_model_dump_json(
    tournament1: Tournament,
    capfd: CaptureFixture[str],
    expected_json: Callable[..., str],
) -> None:
    await tournament_model_dump_json(tournament1)
    assert capfd.readouterr().out == expected_json(tournament1)


@pytest.mark.asyncio
@pytest.mark.parametrize("indent", [1, 2, 4])
async def test_dump_indent(
    tournament1: Tournament,
    capfd: CaptureFixture[str],
    indent: int,
    expected_json: Callable[..., str],
) -> None:
    await tournament_model_dump_json(tournament1, indent=indent)

    out = capfd.readouterr().out
    assert out == expected_json(tournament1, indent)
    assert out.count("\n") > 1
    assert out.splitlines()[1].startswith(" " * indent + '"')


@pytest.mark.asyncio
async def test_dump_includes_matches_that_are_not_ready(
    tournament1: Tournament,
    capfd: CaptureFixture[str],
) -> None:
    await tournament_model_dump_json(tournament1)
    dumped = json.loads(capfd.readouterr().out)
    assert len(dumped["matches"]) == tournament1.nmatches


@pytest.mark.asyncio
async def test_dump_logs(
    tournament1: Tournament, capfd: CaptureFixture[str], caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        await tournament_model_dump_json(tournament1)
    assert "Tournament changed, printing JSON to stdout" in caplog.text


@pytest.mark.asyncio
async def test_print_tournament_prints_on_update_only(
    clictx: CliContext, mocker: MockerFixture, tournament1: Tournament
) -> None:
    write = mocker.patch("tptools.tpsrv.stdout.nonblocking_write")
    # already present before anyone listens: must not be printed
    clictx.itc.set("tournament", Tournament(name="Before"))

    async with running(print_tournament(clictx, indent=None)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        write.assert_not_called()

        clictx.itc.set("tournament", tournament1)
        await wait_for(lambda: write.call_count == 1)

    (call,) = write.call_args_list
    assert json.loads(call.args[0])["name"] == "Test 1"
    assert call.args[0].endswith("\n")


@pytest.mark.asyncio
async def test_print_tournament_every_change(
    clictx: CliContext, mocker: MockerFixture
) -> None:
    write = mocker.patch("tptools.tpsrv.stdout.nonblocking_write")

    async with running(print_tournament(clictx, indent=None)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))

        def printed(n: int) -> Callable[[], bool]:
            return lambda: write.call_count == n

        for i, name in enumerate(["One", "Two", "Three"], 1):
            clictx.itc.set("tournament", Tournament(name=name))
            await wait_for(printed(i))

    names = [json.loads(c.args[0])["name"] for c in write.call_args_list]
    assert names == ["One", "Two", "Three"]


@pytest.mark.asyncio
async def test_print_tournament_ignores_none(
    clictx: CliContext, mocker: MockerFixture
) -> None:
    write = mocker.patch("tptools.tpsrv.stdout.nonblocking_write")

    async with running(print_tournament(clictx, indent=None)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        clictx.itc.set("tournament", None)
        await asyncio.sleep(0.05)

    write.assert_not_called()


@pytest.mark.asyncio
async def test_print_tournament_passes_indent(
    clictx: CliContext, mocker: MockerFixture, tournament1: Tournament
) -> None:
    write = mocker.patch("tptools.tpsrv.stdout.nonblocking_write")

    async with running(print_tournament(clictx, indent=3)):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        clictx.itc.set("tournament", tournament1)
        await wait_for(lambda: write.call_count == 1)

    assert write.call_args.args[0].splitlines()[1].startswith("   " + '"')


# the command


def test_stdout_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(stdout, ["--help"])
    assert result.exit_code == 0
    assert "Output tournament data as JSON to stdout" in result.output
    assert "--indent" in result.output


@pytest.mark.parametrize("indent", ["0", "-1", "abc", "1.5"])
def test_stdout_rejects_bad_indent(invoke_plugin: InvokePlugin, indent: str) -> None:
    result = invoke_plugin(stdout, ["--indent", indent])
    assert result.exit_code == 2
    assert "--indent" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, indent", [([], None), (["-i", "2"], 2), (["--indent", "5"], 5)]
)
async def test_stdout_command(
    make_factory: MakeFactory,
    clictx: CliContext,
    mocker: MockerFixture,
    args: list[str],
    indent: int | None,
) -> None:
    write = mocker.patch("tptools.tpsrv.stdout.nonblocking_write")

    async with running(make_factory(stdout, args)()):
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        clictx.itc.set("tournament", Tournament(name="Cmd"))
        await wait_for(lambda: write.call_count == 1)

    out = write.call_args.args[0]
    assert json.loads(out)["name"] == "Cmd"
    assert (out.count("\n") > 1) is (indent is not None)
