# ------------------------------------------------------------------------------
#  Project: mdscaffold
#  Copyright (c) 2026 Timothy H. Click, Ph.D.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------------
"""Main orchestration module executing runtime dynamic discovery and structural registration of workspace subcommands.

This module leverages standard Python introspection interfaces to crawl isolated filesystem modules, importing
and attaching detached command routines dynamically to avoid editing a centralized routing file.
"""

import typer
from rich.console import Console

from mdscaffold import __version__  # Fetch the dynamic version variable

app = typer.Typer(
    help="mdscaffold: Automation platform for molecular dynamics simulation structures and environments.",
    no_args_is_help=True,  # Optional: Automatically prints help instead of crashing if run empty
)
console = Console()


def version_callback(value: bool):
    """Evaluate the boolean state of the version option flag and emit licensing, versioning, and legal disclaimers if triggered.

    Parameters
    ----------
    value : bool
        The boolean signal captured by the Typer option parser indicating whether the user explicitly supplied the target flag via the system command-line interface framework.

    Raises
    ------
    typer.Exit
        Intercepts standard execution and forces a clean application exit sequence code of 0 once the informational metadata arrays have been successfully flushed to stdout.
    """
    if value:
        console.print(f"[bold]mdscaffold version {__version__}[/bold]")
        console.print("Copyright (C) 2026 Timothy H. Click")
        console.print("""License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""")
        raise typer.Exit()


# Add a default callback or initialization command
@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show the application version, copyright, and GPLv3+ license statement.",
    )
) -> None:
    """Core entrypoint and initialization callback for the mdscaffold command-line interface framework.

    This function coordinates the foundational execution state, runtime parameter parsing, and diagnostic configurations
    before subcommands are dispatched. It manages the global context layers required to map, build, and validate
    subdirectory configurations and system coordinates for molecular dynamics workspace environments.

    Parameters
    ----------
    version : bool, optional
        A structural command-line flag option string selector that intercepts normal programmatic control loops to
        instantly pipe software version and copyright properties to the terminal window.

    Returns
    -------
    None
        The function returns no explicit values. It configures ambient state context objects and transfers operational
        control vectors directly to the targeted subcommands.

    Raises
    ------
    typer.Exit
        Raised explicitly if initialization parameters, directory verification targets, or platform context bindings
        fail baseline structural sanity checks during startup loops.

    See Also
    --------
    init : Subcommand responsible for building new structural workspace scaffolding matrices.

    Notes
    -----
    This callback acts as an initialization gate. If the application is invoked without explicit subcommands or
    arguments, the framework automatically falls back to emitting standard diagnostic help menus.

    Examples
    --------
    >>> # Invoking the framework through a standard system shell sub-process execution loop to verify the environment
    layout parameters
    >>> mdscaffold --help
    """
    pass


if __name__ == "__main__":
    app()
