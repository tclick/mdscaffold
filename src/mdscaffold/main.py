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

app = typer.Typer()
console = Console()


if __name__ == "__main__":
    app()
