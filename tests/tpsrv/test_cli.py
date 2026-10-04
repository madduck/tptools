import asyncio
import importlib
import logging
import pathlib
import runpy
import sys
from collections.abc import Callable, Generator
from typing import Any

import click
import pytest
from click.testing import CliRunner
from click_async_plugins import PluginLifespan, plugin
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture

from tptools.tpsrv import cli
from tptools.tpsrv.cli import PLUGINS, make_app, tpsrv
from tptools.tpsrv.util import CliContext, pass_clictx


@pytest.fixture(autouse=True)
def default_cfg(tmp_path: pathlib.Path, monkeypatch: MonkeyPatch) -> pathlib.Path:
    """Keep the tests from picking up a real tptools/cfg.toml of the developer

    The default for --config is computed when tptools.tpsrv.cli is imported, so
    setting e.g. XDG_CONFIG_HOME now would be too late; patch the option itself.
    """
    path = tmp_path / "default-config-dir" / "cfg.toml"
    (opt,) = [p for p in tpsrv.params if p.name == "config"]
    monkeypatch.setattr(opt, "default", path)
    return path


@pytest.fixture(autouse=True)
def restore_logging() -> Generator[None]:
    """Invoking the group reconfigures global logging; undo that after each test"""
    root = logging.getLogger()
    names = [*SILENCED, cli.logger.name]
    saved = {
        n: (logging.getLogger(n).level, logging.getLogger(n).propagate) for n in names
    }
    handlers = root.handlers[:]
    yield
    for n, (level, propagate) in saved.items():
        logging.getLogger(n).setLevel(level)
        logging.getLogger(n).propagate = propagate
    root.handlers[:] = handlers


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# make_app()


@pytest.fixture
def client() -> TestClient:
    return TestClient(make_app())


def test_make_app_returns_fastapi() -> None:
    app = make_app()
    assert isinstance(app, FastAPI)


def test_make_app_has_changeevent() -> None:
    app = make_app()
    assert isinstance(app.state.changeevent, asyncio.Event)
    assert not app.state.changeevent.is_set()


def test_make_app_apps_are_independent() -> None:
    a, b = make_app(), make_app()
    assert a is not b
    assert a.state.changeevent is not b.state.changeevent


def test_make_app_custom_class() -> None:
    class MyApp(FastAPI):
        pass

    assert isinstance(make_app(app_class=MyApp), MyApp)


def test_make_app_passes_lifespan(mocker: MockerFixture) -> None:
    lifespan = mocker.Mock()
    app_class = mocker.Mock(wraps=FastAPI)
    make_app(lifespan, app_class=app_class)
    app_class.assert_called_once_with(lifespan=lifespan)


def test_root_pong(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text == "Hello testclient, tpsrv is running!\n"


def test_root_pong_prefers_forwarded_for(client: TestClient) -> None:
    resp = client.get("/", headers={"X-Forwarded-For": "192.0.2.7"})
    assert resp.text == "Hello 192.0.2.7, tpsrv is running!\n"


def test_root_pong_logs_the_client(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=cli.logger.name):
        client.get("/", headers={"X-Forwarded-For": "192.0.2.7"})
    assert "Received ping request from 192.0.2.7" in caplog.text


def test_root_pong_without_client_address() -> None:
    from starlette.requests import Request

    scope: dict[str, Any] = {"type": "http", "headers": [], "client": None}
    app = make_app()
    (route,) = [r for r in app.routes if getattr(r, "path", None) == "/"]
    resp = route.endpoint(Request(scope))  # type: ignore[attr-defined]
    assert resp == "Hello None, tpsrv is running!\n"


def test_robots_txt(client: TestClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text == "User-agent: *\nDisallow: /\n"


def test_favicon(client: TestClient) -> None:
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


def test_unknown_path_is_404(client: TestClient) -> None:
    assert client.get("/nonexistent").status_code == 404


# plugin registration


def test_all_plugins_registered() -> None:
    # command names use dashes, module names underscores
    assert set(tpsrv.commands) == {p.replace("_", "-") for p in PLUGINS}


@pytest.mark.parametrize("name", PLUGINS)
def test_plugin_has_help_text(runner: CliRunner, name: str) -> None:
    result = runner.invoke(tpsrv, [name.replace("_", "-"), "--help"])
    assert result.exit_code == 0
    assert f"Usage: tpsrv {name.replace('_', '-')}" in result.output


def run_cli_module_with_broken_plugins(
    mocker: MockerFixture,
    broken: dict[str, Exception],
) -> dict[str, Any]:
    """Re-execute tptools.tpsrv.cli in a throw-away namespace

    The importlib.import_module() calls at module scope are what registers the
    plugins, and that only ever happens on import. Running the module under a
    different name leaves the real `tpsrv` group (and sys.modules) untouched.
    """
    real_import_module = importlib.import_module

    def import_module(name: str, package: str | None = None) -> Any:
        if name.lstrip(".") in broken:
            raise broken[name.lstrip(".")]
        return real_import_module(name, package)

    mocker.patch("importlib.import_module", side_effect=import_module)
    return rerun_cli_module(mocker)


def rerun_cli_module(mocker: MockerFixture) -> dict[str, Any]:
    # new_logger() reconfigures the root logger (and thus drops pytest's capture
    # handler), so hand the re-executed module a regular named logger instead
    mocker.patch(
        "click_extra.new_logger", return_value=logging.getLogger("tpsrv.cli.rerun")
    )
    # and avoid runpy's warning about re-executing an already imported module
    sys.modules.pop("tptools.tpsrv.cli")
    try:
        return runpy.run_module("tptools.tpsrv.cli", run_name="tptools.tpsrv.cli_rerun")
    finally:
        sys.modules["tptools.tpsrv.cli"] = cli


@pytest.mark.parametrize("exc_type", [ImportError, NotImplementedError])
def test_unloadable_plugin_is_skipped_with_warning(
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    exc_type: type[Exception],
) -> None:
    with caplog.at_level(logging.WARNING):
        ns = run_cli_module_with_broken_plugins(
            mocker, {"squoresrv": exc_type("not today")}
        )

    group = ns["tpsrv"]
    assert "squoresrv" not in group.commands
    assert "post" in group.commands
    assert "Plugin 'squoresrv' cannot be loaded: not today" in caplog.text


def test_other_plugin_errors_are_not_swallowed(mocker: MockerFixture) -> None:
    with pytest.raises(RuntimeError, match="unexpected"):
        run_cli_module_with_broken_plugins(mocker, {"post": RuntimeError("unexpected")})


def test_falls_back_to_asyncio_loop_without_uvloop(
    monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setitem(sys.modules, "uvloop", None)
    ns = rerun_cli_module(mocker)
    assert ns["new_event_loop"] is asyncio.new_event_loop


# the group


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(tpsrv, ["--help"])
    assert result.exit_code == 0
    assert "Serve match and player data via HTTP" in result.output
    for opt in ("--config", "--verbose", "--very-debug", "--host", "--port"):
        assert opt in result.output
    assert "[default: 8000; 1024<=x<=65535]" in " ".join(result.output.split())
    assert "[default: 0.0.0.0]" in result.output


def test_requires_a_command(runner: CliRunner) -> None:
    result = runner.invoke(tpsrv, [])
    assert result.exit_code == 2
    assert "Usage: tpsrv" in result.output


def test_unknown_command(runner: CliRunner) -> None:
    result = runner.invoke(tpsrv, ["nonexistent"])
    assert result.exit_code == 2
    assert "No such command 'nonexistent'" in result.output


@pytest.mark.parametrize("port", ["0", "80", "1023", "65536", "70000", "-1", "abc"])
def test_port_validation(runner: CliRunner, port: str) -> None:
    result = runner.invoke(tpsrv, ["--port", port, "stdout"])
    assert result.exit_code == 2
    assert "Invalid value for '--port' / '-p'" in result.output


# runit() and the way the group wires up the server


class FakeServer:
    """Stand-in for uvicorn.Server that never binds a port"""

    instances: list["FakeServer"] = []
    # what serve() does after plugin tasks have had a chance to start
    behaviour: Callable[[], Any] = staticmethod(lambda: None)

    def __init__(self, config: Any) -> None:
        self.config = config
        self.serve_called = 0
        FakeServer.instances.append(self)

    async def serve(self) -> None:
        self.serve_called += 1
        # let the plugin tasks start; if one of them fails, the task group
        # cancels us right here
        await asyncio.sleep(0.05)
        type(self).behaviour()


@pytest.fixture
def server(mocker: MockerFixture) -> Generator[type[FakeServer]]:
    FakeServer.instances = []
    FakeServer.behaviour = staticmethod(lambda: None)
    mocker.patch("uvicorn.Server", FakeServer)
    yield FakeServer
    FakeServer.instances = []
    FakeServer.behaviour = staticmethod(lambda: None)


@pytest.fixture(autouse=True)
def close_event_loops(mocker: MockerFixture) -> Generator[None]:
    """runit() creates (and never closes) its own event loop; clean up after it"""
    loops: list[asyncio.AbstractEventLoop] = []
    real: Callable[[], asyncio.AbstractEventLoop] = vars(cli)["new_event_loop"]

    def tracking() -> asyncio.AbstractEventLoop:
        loop = real()
        loops.append(loop)
        return loop

    mocker.patch.object(cli, "new_event_loop", tracking)
    yield
    for loop in loops:
        loop.close()
    asyncio.set_event_loop(None)


class Recorder:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.clictx: CliContext | None = None


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def probe(monkeypatch: MonkeyPatch, recorder: Recorder) -> click.Command:
    """A trivial plugin that records its set-up and tear-down"""

    @plugin
    @click.option("--fail-with", help="Raise ClickException during set-up")
    @click.option("--task-fails-with", help="Raise ClickException in the task")
    @click.option("--crash", is_flag=True, help="Raise a random exception in the task")
    @pass_clictx
    async def probe(
        clictx: CliContext,
        fail_with: str | None,
        task_fails_with: str | None,
        crash: bool,
    ) -> PluginLifespan:
        recorder.clictx = clictx
        recorder.events.append("setup")
        if fail_with:
            raise click.ClickException(fail_with)

        async def task() -> None:
            recorder.events.append("task")
            if task_fails_with:
                raise click.ClickException(task_fails_with)
            if crash:
                raise ZeroDivisionError("kaboom")
            await asyncio.sleep(3600)

        try:
            yield task()
        finally:
            recorder.events.append("teardown")

    monkeypatch.setitem(tpsrv.commands, "probe", probe)
    return probe


def test_server_started_with_defaults(
    runner: CliRunner, server: type[FakeServer], probe: click.Command
) -> None:
    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output

    (srv,) = server.instances
    assert srv.serve_called == 1
    assert srv.config.host == "0.0.0.0"
    assert srv.config.port == 8000
    assert srv.config.access_log is False


@pytest.mark.parametrize(
    "args, host, port",
    [
        (["--host", "127.0.0.1"], "127.0.0.1", 8000),
        (["-h", "::1"], "::1", 8000),
        (["--port", "9999"], "0.0.0.0", 9999),
        (["-p", "1024"], "0.0.0.0", 1024),
        (["-p", "65535"], "0.0.0.0", 65535),
        (["-h", "localhost", "-p", "8080"], "localhost", 8080),
    ],
)
def test_host_and_port_reach_server(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    args: list[str],
    host: str,
    port: int,
) -> None:
    result = runner.invoke(tpsrv, [*args, "probe"])
    assert result.exit_code == 0, result.output
    (srv,) = server.instances
    assert (srv.config.host, srv.config.port) == (host, port)


def test_server_serves_the_app_from_the_context(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    recorder: Recorder,
) -> None:
    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output

    assert recorder.clictx is not None
    (srv,) = server.instances
    assert srv.config.app is recorder.clictx.api
    assert isinstance(recorder.clictx.api, FastAPI)
    assert recorder.clictx.watcher is None


def test_plugin_lifecycle(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    recorder: Recorder,
    caplog: LogCaptureFixture,
) -> None:
    # -v is what lowers the log level to INFO, caplog.at_level() alone is overridden
    result = runner.invoke(tpsrv, ["-v", "probe"])
    assert result.exit_code == 0, result.output

    # set up, then run as a task, then torn down after the server returns
    assert recorder.events == ["setup", "task", "teardown"]
    assert "Exiting…" in caplog.text


def test_keyboard_interrupt_is_a_clean_exit(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    recorder: Recorder,
) -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    server.behaviour = staticmethod(interrupt)
    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output
    assert recorder.events == ["setup", "task", "teardown"]


def test_multiple_plugins_share_the_context(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    recorder: Recorder,
) -> None:
    result = runner.invoke(tpsrv, ["probe", "probe"])
    assert result.exit_code == 0, result.output
    assert recorder.events.count("setup") == 2
    assert recorder.events.count("teardown") == 2


def test_clickexception_during_plugin_setup(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
) -> None:
    result = runner.invoke(tpsrv, ["probe", "--fail-with", "no good"])
    assert result.exit_code == 1
    assert "Error: no good" in result.output
    # never got as far as starting the server
    assert server.instances[0].serve_called == 0


def test_clickexception_from_plugin_task(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    recorder: Recorder,
) -> None:
    result = runner.invoke(tpsrv, ["probe", "--task-fails-with", "task broke"])
    assert result.exit_code == 1
    assert "Error: task broke" in result.output
    assert recorder.events[-1] == "teardown"


def test_unexpected_exception_drops_into_debugger_and_exits_1(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
) -> None:
    set_trace = mocker.patch("ipdb.set_trace")
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(tpsrv, ["probe", "--crash"])

    assert result.exit_code == 1
    set_trace.assert_called_once_with()
    assert "Something went really wrong" in caplog.text
    assert "ZeroDivisionError" in caplog.text


# --very-debug and logger silencing


SILENCED: dict[str, int] = {
    "asyncio": logging.WARNING,
    "watchdog": logging.WARNING,
    "click_async_plugins.itc": logging.INFO,
    "click_extra": logging.INFO,
    "tptools.tpmatch": logging.INFO,
    "httpx": logging.WARNING,
    "httpcore.connection": logging.INFO,
    "httpcore.http11": logging.INFO,
}


@pytest.fixture
def silence_logger_spy(mocker: MockerFixture) -> Any:
    return mocker.patch.object(cli, "silence_logger")


def test_loggers_are_silenced_by_default(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    silence_logger_spy: Any,
) -> None:
    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output

    called = {c.args[0]: c.kwargs["level"] for c in silence_logger_spy.call_args_list}
    assert called == SILENCED


def test_very_debug_leaves_loggers_alone(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    silence_logger_spy: Any,
) -> None:
    result = runner.invoke(tpsrv, ["--very-debug", "probe"])
    assert result.exit_code == 0, result.output
    silence_logger_spy.assert_not_called()


# configuration file


def write_config(path: pathlib.Path, content: str) -> pathlib.Path:
    path.write_text(content)
    return path


def test_config_file_sets_options(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    tmp_path: pathlib.Path,
) -> None:
    cfg = write_config(tmp_path / "cfg.toml", '[tpsrv]\nport = 8123\nhost = "::1"\n')
    result = runner.invoke(tpsrv, ["--config", str(cfg), "probe"])
    assert result.exit_code == 0, result.output

    (srv,) = server.instances
    assert (srv.config.host, srv.config.port) == ("::1", 8123)


def test_command_line_beats_config_file(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    tmp_path: pathlib.Path,
) -> None:
    cfg = write_config(tmp_path / "cfg.toml", "[tpsrv]\nport = 8123\n")
    result = runner.invoke(tpsrv, ["--config", str(cfg), "--port", "9000", "probe"])
    assert result.exit_code == 0, result.output
    assert server.instances[0].config.port == 9000


def test_default_config_location() -> None:
    # tpsrv's own default (the real one, not the one patched for these tests)
    default = pathlib.Path(click.get_app_dir("tptools", roaming=True)) / "cfg.toml"
    assert default.name == "cfg.toml"
    assert default.parent.name == "tptools"


def test_default_config_is_read_when_present(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    default_cfg: pathlib.Path,
) -> None:
    default_cfg.parent.mkdir(parents=True)
    write_config(default_cfg, "[tpsrv]\nport = 8777\n")

    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output
    assert server.instances[0].config.port == 8777


def test_missing_default_config_is_fine(
    runner: CliRunner, server: type[FakeServer], probe: click.Command
) -> None:
    result = runner.invoke(tpsrv, ["probe"])
    assert result.exit_code == 0, result.output


def test_missing_explicit_config_is_an_error(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    tmp_path: pathlib.Path,
) -> None:
    result = runner.invoke(tpsrv, ["--config", str(tmp_path / "nope.toml"), "probe"])
    assert result.exit_code != 0
    assert server.instances == []


def test_unknown_config_key_is_rejected(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    tmp_path: pathlib.Path,
) -> None:
    cfg = write_config(tmp_path / "cfg.toml", "[tpsrv]\nbogus = 1\n")
    result = runner.invoke(tpsrv, ["--config", str(cfg), "probe"])
    assert result.exit_code != 0
    assert server.instances == []


def test_invalid_port_in_config_file_is_rejected(
    runner: CliRunner,
    server: type[FakeServer],
    probe: click.Command,
    tmp_path: pathlib.Path,
) -> None:
    cfg = write_config(tmp_path / "cfg.toml", "[tpsrv]\nport = 80\n")
    result = runner.invoke(tpsrv, ["--config", str(cfg), "probe"])
    assert result.exit_code == 2
    assert "--port" in result.output


def test_console_script_entry_point() -> None:
    """pyproject.toml's [project.scripts] points at tptools.tpsrv.cli:tpsrv"""
    from importlib.metadata import entry_points

    (ep,) = [e for e in entry_points(group="console_scripts") if e.name == "tpsrv"]
    assert ep.value == "tptools.tpsrv.cli:tpsrv"
    assert ep.load() is tpsrv
