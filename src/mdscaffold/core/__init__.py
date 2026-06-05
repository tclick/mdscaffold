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
"""Core business logic for mdscaffold.

This package contains all simulation pipeline logic for mdscaffold, organized into subpackages
by concern. It is strictly decoupled from the CLI layer (``mdscaffold.cli``) — no Typer, Rich,
or any other presentation-layer dependency appears here. Every public function and class in this
package is callable from a plain Python script or test without a CLI context.

The intended import boundary is::

    mdscaffold.cli  ->  mdscaffold.core  (allowed)
    mdscaffold.core ->  mdscaffold.cli  (never)

Subpackages
-----------
project
    Project configuration and directory layout. Defines ``ProjectConfig``, the top-level Pydantic
    model that is the single source of truth for a simulation project, alongside ``ProjectLayout``
    and ``StageLayout`` frozen dataclasses that encode the canonical directory structure. The
    ``scaffold`` module creates the directory tree on disk from a ``ProjectLayout`` instance.

simulation
    Typed representations of each simulation stage and the physical parameters that govern them.
    ``SimulationConfig`` (defined in ``project.config``) is parameterised by the models here.
    ``restraints`` encodes the tapered equilibration restraint schedule — six force constant steps
    and the Amber atom mask — as module-level constants consumed by the writers layer.

writers
    Jinja2-based file writers. Each module accepts a typed stage or config object and a destination
    ``Path``, renders the appropriate template from ``core/templates/``, and writes the result to
    disk. No side effects beyond the file write. Three sub-modules cover the three file categories
    generated by ``mdscaffold write``: Amber ``.in`` input scripts, SLURM/PBS/local job scripts,
    and ``README.md`` documentation stubs.

runners
    Scheduler-agnostic job submission and status checking. A ``Runner`` protocol in ``base``
    defines the interface; ``slurm``, ``pbs``, and ``local`` provide concrete implementations.
    The ``local`` runner executes jobs as blocking subprocesses, suitable for development and
    single-user workstations. The ``slurm`` runner wraps ``sbatch`` with dependency chaining
    via ``--dependency=afterok`` to enforce stage ordering across the pipeline.

analysis
    Trajectory analysis built on ``cpptraj``. The ``cpptraj`` module constructs and executes
    ``cpptraj`` input scripts; higher-level modules (``rmsd``, ``rmsf``, ``clustering``,
    ``contacts``) compose ``cpptraj`` commands for specific analyses and return structured results.

templates
    Jinja2 template files (``.j2``) for all generated file types. Organised into three
    subdirectories: ``amber/`` for ``.in`` input scripts, ``jobs/`` for scheduler job scripts,
    and ``readme/`` for ``README.md`` stubs. Templates are loaded at runtime via Jinja2's
    ``PackageLoader`` and are not imported as Python modules.

Notes
-----
**Dependency direction.** The subpackages have a strict internal dependency order::

    project  <-  simulation  <-  writers
                                runners
                                analysis

``project`` has no internal dependencies. ``simulation`` depends only on ``project``.
``writers``, ``runners``, and ``analysis`` may depend on both ``project`` and ``simulation``
but not on each other. Circular imports between subpackages are not permitted.

**No public re-exports.** This ``__init__.py`` intentionally does not re-export symbols from
subpackages. Callers should import directly from the relevant subpackage::

    # Preferred
    from mdscaffold.core.project.config import ProjectConfig
    from mdscaffold.core.simulation.stages import HeatStage

    # Avoid — fragile, hides provenance
    from mdscaffold.core import ProjectConfig

This keeps import paths explicit and makes refactoring across subpackages straightforward.

**Pydantic models vs dataclasses.** User-facing configuration objects that are constructed from
TOML files or CLI input (``ProjectConfig``, ``ReplicaConfig``, ``SimulationConfig``,
``SlurmConfig``) are Pydantic ``BaseModel`` subclasses with full validation. Internal structural
data that the code owns entirely and never deserialises (``ProjectLayout``, ``StageLayout``) uses
``dataclasses.dataclass(frozen=True)`` for simplicity and immutability without validation overhead.

**Template engine.** The writers layer uses Jinja2 rather than Python 3.13 t-strings. Jinja2 is
preferred because templates live on disk as ``.j2`` files (editable without touching Python
source), support ``{% if %}`` and ``{% for %}`` blocks required by conditional restraint sections
and replica loops, and provide whitespace control via ``{%- -%}`` trim markers. T-strings are
suitable for narrow, safety-critical inline interpolation tasks but are not a replacement for a
file-based templating system.

Examples
--------
Typical usage from a CLI command handler:

>>> from mdscaffold.core.project.config import ProjectConfig
>>> from mdscaffold.core.project.layout import ProjectLayout, default_stages
>>> from mdscaffold.core.project.scaffold import scaffold_project
>>>
>>> config = ProjectConfig.from_toml(project_dir)
>>> layout = ProjectLayout(
...     root=config.root,
...     replica_count=config.n_replicas,
...     n_prod_runs=config.simulation.n_prod_runs,
...     stages=default_stages(),
... )
>>> scaffold_project(layout)
"""
