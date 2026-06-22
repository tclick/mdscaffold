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
"""Integration and unit testing framework verifying discovery registries and execution routing inside main.py."""

from typer.testing import CliRunner

from mdscaffold.main import app

runner = CliRunner()


def test_cli_help_menu_displays_scaffold_context() -> None:
    """Verify that triggering the baseline help flag successfully surfaces core platform branding instructions.

    Returns
    -------
    None
    """
    # Act: Invoke the primary application interface root with standard help arguments
    result = runner.invoke(app, ["--help"])

    # Assert: Confirm clean execution and verification that expected platform branding strings exist
    assert result.exit_code == 0
    assert "mdscaffold:" in result.output
    assert "Automation platform for molecular dynamics" in result.output
