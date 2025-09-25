import pathlib
import sys
from typing import Never

import click

LNKTEMPLATE = "TP file to {tool}"
BATFILESDIR = pathlib.Path(__file__).parent.parent.parent / "winscripts"


@click.command
@click.option(
    "--template",
    "-t",
    default=LNKTEMPLATE,
    show_default=True,
    help="Template to use for link filename",
)
@click.argument("script", type=click.Path(path_type=pathlib.Path), nargs=-1)
def main(template: str, script: list[pathlib.Path]) -> None | Never:
    try:
        from win32com.client import (
            Dispatch,
        )
        from win32com.shell import (
            shell,
            shellcon,
        )

    except ImportError as err:
        raise click.ClickException(
            "pywin32 is missing. This script only works on Windows."
        ) from err

    for s in script:
        batch = BATFILESDIR / f"{s}.bat"
        if not batch.exists():
            raise click.UsageError(f"No such batch file: {batch}")

        desktopdir = pathlib.Path(
            shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)
        )
        scriptshell = Dispatch("WScript.Shell")
        lnk = template.format(tool=s)
        if not lnk.endswith(".lnk"):
            lnk += ".lnk"
        dest = desktopdir / lnk
        shortcut = scriptshell.CreateShortcut(str(dest))
        shortcut.WorkingDirectory = str(desktopdir)
        shortcut.Targetpath = str(batch)
        shortcut.save()

        print(f"Shortcut for {s} created: {dest}")
    return None


if __name__ == "__main__":
    sys.exit(main())
