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
# tests/test_main.py
"""
Unit and functional test suites validating the primary command-line interface entrypoints for mdscaffold.

This module uses the Typer CliRunner matrix infrastructure to assert correct exit codes, standard output streams,
help menu parsing compliance, and dynamic version extraction behaviors from package configuration registries.
"""

import subprocess
import sys

from typer.testing import CliRunner

from mdscaffold import __version__
from mdscaffold.main import app

runner: CliRunner = CliRunner()


def test_cli_help_menu() -> None:
    """Assert that executing the root application binary with help flags returns an informational diagnostics menu.

    Verifies that the CLI subsystem cleanly intercepts the command vector, sets a zero exit status code, and routes
    the base package help string to the standard output buffer.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "mdscaffold" in result.stdout
    assert "Automation platform" in result.stdout


def test_cli_version_flag_output() -> None:
    """Verify that the dynamic version parameter options successfully output package metadata and licensing terms.

    This test executes the application using the explicit '--version' configuration argument and asserts that the
    resulting terminal string includes the synchronized pyproject.toml semantic version string alongside the
    required GNU GPLv3+ open-source compliance declarations.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"mdscaffold version {__version__}" in result.stdout
    assert "License GPLv3+" in result.stdout
    assert "This is free software" in result.stdout


def test_cli_short_version_flag_output() -> None:
    """Assert that the short-form '-v' flag parameter maps identically to the long-form version option behavior.

    Guarantees that option aliases process with matching eager parsing precedence rules and flush the expected
    legal disclaimers to stdout before terminating execution loops cleanly.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert f"mdscaffold version {__version__}" in result.stdout


def test_version_callback_terminates_application() -> None:
    """Assert that executing the short-form version option flag forces a clean execution termination state.

    This test specifically satisfies the '49->exit' coverage gap by proving that the Typer runtime environment
    intercepts the evaluation matrix and triggers an explicit, graceful exit code.
    """
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    # Checking for text components from your triple-quoted GPL text license string ensures code path execution
    assert "License GPLv3+" in result.output


def test_main_module_dunder_execution_block(monkeypatch) -> None:
    """Assert that the standard module execution guard invokes the root Typer entrypoint when evaluated as __main__.

    This test covers line 109 and 113 by executing the script context in a clean, sandboxed subprocess loop,
    ensuring that system binary triggers safely route to the baseline command graph.
    """
    # Execute the module script file directly using the active runtime environment executable path
    cmd = [sys.executable, "-m", "mdscaffold.main", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    assert result.returncode == 0
    assert "mdscaffold:" in result.stdout
