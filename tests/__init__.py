# ------------------------------------------------------------------------------
#  mdscaffold
#  Copyright (c) 2026 Timothy H. Click
#
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of the author nor the names of its contributors may be used
#  to endorse or promote products derived from this software without specific
#  prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
#  ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
#  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#  DAMAGE.
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
