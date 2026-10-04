import pathlib
import sys
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from tptools.cli.tpshortcut import LNKTEMPLATE, main


class FakeShortcut:
    WorkingDirectory: str | None = None
    Targetpath: str | None = None
    saved: bool = False

    def save(self) -> None:
        self.saved = True


class FakeWScriptShell:
    def __init__(self) -> None:
        self.shortcuts: dict[str, FakeShortcut] = {}

    def CreateShortcut(self, dest: str) -> FakeShortcut:  # noqa: N802
        return self.shortcuts.setdefault(dest, FakeShortcut())


@pytest.fixture
def desktopdir(tmp_path: pathlib.Path) -> pathlib.Path:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    return desktop


@pytest.fixture
def scriptshell() -> FakeWScriptShell:
    return FakeWScriptShell()


@pytest.fixture
def winscripts(tmp_path: pathlib.Path, mocker: MockerFixture) -> pathlib.Path:
    path = tmp_path / "winscripts"
    path.mkdir()
    (path / "tpsrv-tp.bat").write_text("@echo off\n")
    (path / "other.bat").write_text("@echo off\n")

    # importlib.resources.path() is a context manager yielding the directory
    mocker.patch(
        "importlib.resources.path",
        return_value=mocker.MagicMock(
            __enter__=mocker.Mock(return_value=path),
            __exit__=mocker.Mock(return_value=False),
        ),
    )
    return path


@pytest.fixture
def fake_pywin32(
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    desktopdir: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> dict[str, Any]:
    """Provide stand-ins for the Windows-only modules imported by main()"""
    shellmod = ModuleType("win32com.shell.shell")
    shellmod.SHGetFolderPath = mocker.Mock(  # type: ignore[attr-defined]
        return_value=str(desktopdir)
    )
    shellconmod = ModuleType("win32com.shell.shellcon")
    shellconmod.CSIDL_DESKTOP = 0x0  # type: ignore[attr-defined]

    shellpkg = ModuleType("win32com.shell")
    shellpkg.shell = shellmod  # type: ignore[attr-defined]
    shellpkg.shellcon = shellconmod  # type: ignore[attr-defined]

    clientpkg = ModuleType("win32com.client")
    dispatch = mocker.Mock(return_value=scriptshell)
    clientpkg.Dispatch = dispatch  # type: ignore[attr-defined]

    win32com = ModuleType("win32com")
    win32com.client = clientpkg  # type: ignore[attr-defined]
    win32com.shell = shellpkg  # type: ignore[attr-defined]

    for name, mod in (
        ("win32com", win32com),
        ("win32com.client", clientpkg),
        ("win32com.shell", shellpkg),
        ("win32com.shell.shell", shellmod),
        ("win32com.shell.shellcon", shellconmod),
    ):
        monkeypatch.setitem(sys.modules, name, mod)

    return {"dispatch": dispatch, "SHGetFolderPath": shellmod.SHGetFolderPath}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_default_template() -> None:
    assert "{tool}" in LNKTEMPLATE


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--template" in result.output
    assert "-t" in result.output
    # the help text may wrap, so normalise whitespace before looking for the default
    assert LNKTEMPLATE in " ".join(result.output.split())


def test_fails_without_pywin32(runner: CliRunner, monkeypatch: MonkeyPatch) -> None:
    # a None entry in sys.modules makes `import` raise ImportError
    for name in ("win32com", "win32com.client", "win32com.shell"):
        monkeypatch.setitem(sys.modules, name, None)

    result = runner.invoke(main, ["tpsrv-tp"])
    assert result.exit_code == 1
    assert "pywin32 is missing" in result.output


def test_no_scripts_is_a_noop(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> None:
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert result.output == ""
    assert scriptshell.shortcuts == {}


def test_unknown_script(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> None:
    result = runner.invoke(main, ["nonexistent"])
    assert result.exit_code == 2
    assert "No such batch file" in result.output
    assert "nonexistent.bat" in result.output
    assert scriptshell.shortcuts == {}


def test_create_shortcut(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    desktopdir: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> None:
    result = runner.invoke(main, ["tpsrv-tp"])
    assert result.exit_code == 0

    dest = desktopdir / "TP file to tpsrv-tp.lnk"
    assert result.output == f"Shortcut for tpsrv-tp created: {dest}\n"

    fake_pywin32["dispatch"].assert_called_once_with("WScript.Shell")
    assert list(scriptshell.shortcuts) == [str(dest)]
    shortcut = scriptshell.shortcuts[str(dest)]
    assert shortcut.saved
    assert shortcut.Targetpath == str(winscripts / "tpsrv-tp.bat")
    assert shortcut.WorkingDirectory == str(desktopdir)


@pytest.mark.parametrize(
    "template, expected",
    [
        ("Open with {tool}", "Open with tpsrv-tp.lnk"),
        ("Open with {tool}.lnk", "Open with tpsrv-tp.lnk"),
        ("static name", "static name.lnk"),
    ],
)
@pytest.mark.parametrize("option", ["--template", "-t"])
def test_template(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    desktopdir: pathlib.Path,
    scriptshell: FakeWScriptShell,
    option: str,
    template: str,
    expected: str,
) -> None:
    result = runner.invoke(main, [option, template, "tpsrv-tp"])
    assert result.exit_code == 0
    assert list(scriptshell.shortcuts) == [str(desktopdir / expected)]


def test_multiple_scripts(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    desktopdir: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> None:
    result = runner.invoke(main, ["tpsrv-tp", "other"])
    assert result.exit_code == 0
    assert list(scriptshell.shortcuts) == [
        str(desktopdir / "TP file to tpsrv-tp.lnk"),
        str(desktopdir / "TP file to other.lnk"),
    ]
    assert all(s.saved for s in scriptshell.shortcuts.values())


def test_stops_at_first_unknown_script(
    runner: CliRunner,
    fake_pywin32: dict[str, Any],
    winscripts: pathlib.Path,
    desktopdir: pathlib.Path,
    scriptshell: FakeWScriptShell,
) -> None:
    result = runner.invoke(main, ["tpsrv-tp", "nonexistent", "other"])
    assert result.exit_code == 2
    # the first one was handled before the error, the last one never was
    assert list(scriptshell.shortcuts) == [str(desktopdir / "TP file to tpsrv-tp.lnk")]


def test_packaged_winscripts_exist() -> None:
    """The batch files that tpshortcut can link to are actually shipped"""
    import importlib.resources

    with importlib.resources.path("tptools", "winscripts") as path:
        assert (path / "tpsrv-tp.bat").is_file()


def test_run_as_script(
    monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import runpy

    monkeypatch.setattr(sys, "argv", ["tpshortcut", "--help"])
    # avoid runpy's warning about re-executing an already imported module
    monkeypatch.delitem(sys.modules, "tptools.cli.tpshortcut")
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tptools.cli.tpshortcut", run_name="__main__")

    assert exc.value.code == 0
    assert "--template" in capsys.readouterr().out
