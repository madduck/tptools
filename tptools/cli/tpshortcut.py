import click
import sys
import pathlib
from win32com.client import Dispatch
from win32com.shell import shell, shellcon

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
@click.argument("script", nargs=1)
def main(template, script):

    desktopdir = pathlib.Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0))
    scriptshell = Dispatch("WScript.Shell")
    lnk = template.format(tool=script)
    if not lnk.endswith(".lnk"):
        lnk += ".lnk"
    dest = desktopdir / lnk
    shortcut = scriptshell.CreateShortcut(str(dest))
    shortcut.WorkingDirectory = str(desktopdir)
    shortcut.Targetpath = str(BATFILESDIR / f"{script}.bat")
    shortcut.save()

    print(f"Shortcut for {script} created: {dest}")


if __name__ == "__main__":
    sys.exit(main())
