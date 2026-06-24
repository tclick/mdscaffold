# ------------------------------------------------------------------------------
#  mdscaffold
#  Copyright (c) 2026 Timothy H. Click, Ph.D.
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
# ------------------------------------------------------------------------------
"""Unit test suites validating package initialization parameters, metadata states, and version fallback mechanisms.

This verification tier checks the structural integrity of the mdscaffold package entrypoint interface. It focuses on
proving that the environmental setup handles normal installed runtime states as well as uninstalled development pathways
without dropping execution exceptions.
"""

import importlib.metadata
import sys


def test_version_fallback_when_package_not_installed(monkeypatch) -> None:
    """Assert that the package root gracefully falls back to a development version string when uninstalled.

    This test uses state modification arrays to simulate an execution environment where mdscaffold is missing from the active
    package distribution registry. It forces a PackageNotFoundError and validates that the fallback assignment matches the
    development branch specification string.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The standard PyTest diagnostic state modifier fixture utilized to swap runtime library execution vectors.

    Returns
    -------
    None
    """

    # Force importlib metadata parsing to raise the target structural initialization error
    def mock_version_raise(distribution_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", mock_version_raise)

    # Evict mdscaffold from active sys.modules if previously imported, forcing a fresh package evaluation sweep
    if "mdscaffold" in sys.modules:
        monkeypatch.delitem(sys.modules, "mdscaffold")

    # Re-import the root module package context to execute the defensive initialization block
    import mdscaffold

    assert mdscaffold.__version__ == "0.1.0-dev"
