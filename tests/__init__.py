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
"""Test automation suite initialization module for the mdscaffold workspace generation engine.

This module establishes the root namespace for the testing infrastructure of the `mdscaffold` application. The suite
is architecturally split into two primary paradigms: deterministic example-based testing for the CLI frontend and
rigorous property-based fuzzing for the underlying file-orchestration and script-generation engines.

Testing Architecture & Submodules
---------------------------------
core/
    Contains structural layout and parameter validation routines. Driven by `pytest` and `hypothesis`, this layer
    fuzzes the simulation configuration generators with randomized input parameters (e.g., temperatures, replica
    counts, step boundaries), ensuring that Pydantic models parse input data safely and backend string templates
    always emit syntactically valid Amber (`sander`/`pmemd.cuda`) and `cpptraj` syntax blocks.
cli/
    Validates terminal interface behaviors, subcommand routing, and YAML configuration file ingestion boundaries.
    - `test_registry.py`: Assures the filesystem-driven autoregistration pipeline registers all active commands.
    - `commands/`: Uses `click.testing.CliRunner` to evaluate individual Typer subcommands (e.g., `setup`, `analyze`)
      against static terminal arguments, verifying correct standard output rendering and shell exit code structures.

Global Configuration & Fixtures
-------------------------------
Shared testing utilities, mock Amber parameter constraints, and automated temporary file/directory lifecycle
fixtures (utilizing pytest's `tmp_path` machinery) are centralized within the root-level `conftest.py` module to
enable cross-submodule reuse and rapid filesystem assertion setups.

See Also
--------
mdscaffold.core.engine : The core orchestration engine that generates the Amber simulation file configurations.
mdscaffold.cli.registry : The dynamic subcommand registration engine verified in the CLI test layer.

Notes
-----
All test execution profiles, system state isolation layers, parallelized multicore distribution via `pytest-xdist`,
and coverage collection boundaries are managed uniformly through the project's root `noxfile.py` automation matrix.
"""
