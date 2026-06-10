# ------------------------------------------------------------------------------
#  Copyright (C) 2026 Timothy H. Click
#
#  This file is part of mdscaffold.
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
"""Automated workspace scaffolding and input file orchestration engine for Molecular Dynamics simulations.

The `mdscaffold` package provides an automated, reproducible pipeline for initializing directory trees, parameter
input manifests, and analysis scripts for Amber Molecular Dynamics (`pmemd.cuda`, `sander`) configurations. It
enforces configuration integrity at the user interface boundary via Pydantic and generates cross-platform
executable shell routines to manage multi-step minimization, heating, tapered equilibration, and multi-replica
production trajectories.

Available Submodules
--------------------
cli/
    Frontend execution matrix powered by Typer and Rich. Handles user arguments, terminal styling, automated command
    routing, and dynamic subcommand discovery using a filesystem-driven autoregister registry pattern.
core/
    Core computational and structural layout engine. Houses structural file templates, validation routines, and the
    underlying file IO handlers.
    - `core.config`: Rigid Pydantic validation schemas enforcing runtime and hardware parameter limits.
    - `core.engine`: Orchestration engine responsible for generating the actual simulation files and folders.
    - `core.io`: High-level file wrapper logic reading and compiling human-readable YAML configurations.

Package Metadata
----------------
__version__ : str
    The active semantic version string of the package layout.
__license__ : str
    The explicit open-source software license binding this codebase (GPL-3.0-or-later).

See Also
--------
mdscaffold.core.engine : Core generation routines managing Amber execution templates.
mdscaffold.cli.entrypoint : Primary root command entry point for the executable interface layer.

Examples
--------
While primarily interacted with via its terminal interface, the underlying validation structures can be imported
directly into custom Python execution environments or Jupyter Notebooks to parse parameters safely:

>>> from pathlib import Path
>>> from mdscaffold.core.config import MatchConfig
>>> config = MatchConfig(input_pdb=Path("system.pdb"), modes=24, tolerance=1e-4)
>>> print(config.modes)
24
"""

__version__ = "0.1.0"
__license__ = "GPL-3.0-or-later"
