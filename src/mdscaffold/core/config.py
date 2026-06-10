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
"""Project configuration models for mdscaffold.

Defines the Pydantic models that represent the complete configuration for an mdscaffold project.
These models are the single source of truth passed through the entire simulation pipeline — from
directory scaffolding and input file generation through job submission and trajectory analysis.

Configuration is read from a ``mdscaffold.toml`` file at the project root and validated on load.
All downstream components (writers, runners, analysis) accept a ``ProjectConfig`` instance rather
than individual parameters.
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ReplicaConfig(BaseModel):
    """Configuration for a single simulation replica.

    Each replica represents an independent copy of the simulation with a unique random seed.
    Replicas share the same force field parameters and starting coordinates but diverge due to
    differences in initial velocities assigned during heating.

    Parameters
    ----------
    index : int
        Zero-based replica index. Used to construct the replica directory name,
        e.g. index 0 -> ``replica_00/``. Must be unique across all replicas in a project.
    seed : int
        Random seed passed to Amber's ``ig`` parameter during heating and equilibration.
        Must be a positive odd integer as required by Amber's random number generator.
        Use -1 to let Amber generate a seed from the system clock — not recommended for
        reproducible simulations.

    Examples
    --------
    >>> replica = ReplicaConfig(index=0, seed=12345)
    >>> replica.dir_name
    'replica_00'
    """

    index: int = Field(..., ge=0, description="Zero-based replica index.")
    seed: int = Field(..., ge=-1, description="Amber random seed (ig). Positive odd integer or -1.")

    @field_validator("seed")
    @classmethod
    def seed_must_be_valid(cls, v: int) -> int:
        """Validate that the seed is either -1 or a positive odd integer.

        Parameters
        ----------
        v : int
            The seed value to validate.

        Returns
        -------
        int
            The validated seed value, unchanged.

        Raises
        ------
        ValueError
            If the seed is not -1 and is not a positive odd integer.
        """
        if v != -1 and (v <= 0 or v % 2 == 0):
            raise ValueError(f"Amber seed must be a positive odd integer or -1, got {v!r}.")
        return v

    @property
    def dir_name(self) -> str:
        """Return the replica directory name derived from the replica index.

        Returns
        -------
        str
            Zero-padded directory name, e.g. ``'replica_00'``, ``'replica_03'``.
        """
        return f"replica_{self.index:02d}"


class SlurmConfig(BaseModel):
    """SLURM job scheduler configuration for a project.

    Controls the resources requested in generated ``#SBATCH`` directives. These values are
    written into job scripts by the writers layer and are not validated against the actual
    hardware — it is the user's responsibility to ensure requested resources do not exceed
    what is available on the target machine or partition.

    Parameters
    ----------
    partition : str
        SLURM partition name. Defaults to ``'debug'``, the conventional name for the default
        partition on a single-node SLURM installation.
    n_gpus : int
        Number of GPUs to request per job via ``--gres=gpu:<n_gpus>``. Must be >= 1.
        For ``pmemd.cuda``, one GPU per job is typical.
    n_cpus : int
        Number of CPUs to request per job via ``--cpus-per-task``. Must be >= 1.
    mem_gb : int
        Memory to request in gigabytes via ``--mem``. Must be >= 1.
    walltime : str
        Maximum walltime in ``HH:MM:SS`` format passed to ``--time``. Jobs exceeding this
        limit are killed by SLURM. Defaults to ``'24:00:00'``.
    account : str | None
        SLURM account name for job accounting via ``--account``. Optional; omitted from
        job scripts when ``None``.

    Examples
    --------
    >>> slurm = SlurmConfig(partition="gpu", n_gpus=1, n_cpus=8, mem_gb=16)
    >>> slurm.walltime
    '24:00:00'
    """

    partition: str = Field(default="debug", min_length=1, description="SLURM partition name.")
    n_gpus: int = Field(default=1, ge=1, description="Number of GPUs per job.")
    n_cpus: int = Field(default=8, ge=1, description="Number of CPUs per job.")
    mem_gb: int = Field(default=8, ge=1, description="Memory per job in GB.")
    walltime: str = Field(default="24:00:00", description="Maximum walltime as HH:MM:SS.")
    account: str | None = Field(default=None, description="SLURM account name for job accounting.")

    @field_validator("walltime")
    @classmethod
    def walltime_must_be_valid(cls, v: str) -> str:
        """Validate that walltime is in HH:MM:SS format.

        Parameters
        ----------
        v : str
            The walltime string to validate.

        Returns
        -------
        str
            The validated walltime string, unchanged.

        Raises
        ------
        ValueError
            If the walltime string does not match ``HH:MM:SS`` format or contains
            out-of-range values for minutes or seconds.
        """
        parts = v.split(":")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Walltime must be in HH:MM:SS format, got {v!r}.")
        _, mm, ss = parts
        if not (0 <= int(mm) <= 59 and 0 <= int(ss) <= 59):
            raise ValueError(f"Walltime minutes and seconds must be 0-59, got {v!r}.")
        return v


class SimulationConfig(BaseModel):
    """Physical and simulation parameters shared across all stages and replicas.

    These values are injected into Amber ``.in`` input file templates by the writers layer.
    All parameters apply to every stage unless a stage-specific override is provided in the
    relevant ``StageConfig`` subclass.

    Parameters
    ----------
    target_temp : float
        Target simulation temperature in Kelvin. Must be > 0. Heating stages ramp from 0 K
        to this value; equilibration and production stages maintain it via a Langevin thermostat.
        Defaults to 300.0 K.
    target_pressure : float
        Target simulation pressure in bar. Must be > 0. Applied during NPT equilibration and
        production stages via a Monte Carlo barostat. Defaults to 1.0 bar.
    timestep_fs : float
        Integration timestep in femtoseconds. Must be > 0. Standard value for simulations with
        SHAKE constraints on bonds involving hydrogen is 2.0 fs. Defaults to 2.0 fs.
    cutoff_angstrom : float
        Non-bonded interaction cutoff distance in Angstroms. Must be > 0. Typical values for
        explicit solvent simulations are 10-12 Å. Defaults to 10.0 Å.
    n_prod_steps : int
        Number of MD steps per production run segment. Combined with ``timestep_fs``, this
        determines the length of each segment: 50,000,000 steps x 2 fs = 100 ns. Must be >= 1.
        Defaults to 50,000,000.
    n_prod_runs : int
        Number of sequential 100-ns production run segments per replica. Total production time
        per replica is ``n_prod_runs x n_prod_steps x timestep_fs``. Must be >= 1.
        Defaults to 10 (1 µs per replica).

    Examples
    --------
    >>> sim = SimulationConfig()
    >>> sim.prod_time_ns
    1000.0

    >>> sim = SimulationConfig(n_prod_runs=5, timestep_fs=2.0, n_prod_steps=50_000_000)
    >>> sim.prod_time_ns
    500.0
    """

    target_temp: float = Field(default=300.0, gt=0, description="Target temperature in Kelvin.")
    target_pressure: float = Field(default=1.0, gt=0, description="Target pressure in bar.")
    timestep_fs: float = Field(default=2.0, gt=0, description="Integration timestep in femtoseconds.")
    cutoff_angstrom: float = Field(default=10.0, gt=0, description="Non-bonded cutoff in Angstroms.")
    n_prod_steps: int = Field(default=50_000_000, ge=1, description="MD steps per production segment.")
    n_prod_runs: int = Field(default=10, ge=1, description="Number of 100-ns production segments per replica.")

    @property
    def prod_time_ns(self) -> float:
        """Return total production time per replica in nanoseconds.

        Returns
        -------
        float
            Total production time in ns: ``n_prod_runs x n_prod_steps x timestep_fs x 1e-6``.
        """
        return self.n_prod_runs * self.n_prod_steps * self.timestep_fs * 1e-6


class ProjectConfig(BaseModel):
    """Top-level configuration model for an mdscaffold project.

    The single source of truth for a simulation project. Constructed from a ``mdscaffold.toml``
    file at the project root and passed through the entire pipeline — scaffolding, file writing,
    job submission, and analysis. All downstream components accept a ``ProjectConfig`` instance
    rather than individual keyword arguments.

    Serialised to and from ``mdscaffold.toml`` via ``model_dump()`` and ``model_validate()``.
    The TOML file is written to the project root by ``new project`` and re-read by all subsequent
    subcommands.

    Parameters
    ----------
    name : str
        Human-readable project name. Used as the top-level directory name and in generated
        README files. Must be non-empty and contain only alphanumeric characters, hyphens,
        and underscores to ensure filesystem compatibility. Examples: ``'hspa1a_apo'``,
        ``'brd4-inhibitor-complex'``.
    root : Path
        Absolute path to the project root directory. Created by ``new project`` if it does not
        exist. All replica and stage directories are constructed relative to this path.
    replicas : list[ReplicaConfig]
        List of replica configurations. Must contain at least one replica. Replica indices must
        be unique and form a contiguous zero-based sequence (0, 1, 2, ...).
    simulation : SimulationConfig
        Physical and MD parameters shared across all stages. Defaults to standard values
        (300 K, 1 bar, 2 fs timestep, 10 Å cutoff, 10 x 100 ns production).
    slurm : SlurmConfig
        SLURM scheduler configuration for generated job scripts. Only used when
        ``scheduler == 'slurm'``.
    scheduler : Literal['slurm', 'pbs', 'local']
        Job scheduler backend used by ``run`` subcommands. Determines which job script
        templates are rendered by the writers layer. Defaults to ``'slurm'``.

    Examples
    --------
    Construct a minimal project configuration programmatically:

    >>> config = ProjectConfig(
    ...     name="hspa1a_apo",
    ...     root=Path("/data/simulations/hspa1a_apo"),
    ...     replicas=[
    ...         ReplicaConfig(index=0, seed=11111),
    ...         ReplicaConfig(index=1, seed=33333),
    ...         ReplicaConfig(index=2, seed=55555),
    ...     ],
    ... )
    >>> config.n_replicas
    3
    >>> config.simulation.prod_time_ns
    1000.0

    Load from a ``mdscaffold.toml`` file:

    >>> import tomllib
    >>> with open("mdscaffold.toml", "rb") as f:
    ...     config = ProjectConfig.model_validate(tomllib.load(f))

    Save to a ``mdscaffold.toml`` file:

    >>> import tomli_w
    >>> with open("mdscaffold.toml", "wb") as f:
    ...     tomli_w.dump(config.model_dump(mode="json"), f)
    """

    name: str = Field(..., min_length=1, description="Project name; used as the root directory name.")
    root: Path = Field(..., description="Absolute path to the project root directory.")
    replicas: list[ReplicaConfig] = Field(..., min_length=1, description="Per-replica configurations.")
    simulation: SimulationConfig = Field(default_factory=SimulationConfig, description="MD parameters.")
    slurm: SlurmConfig = Field(default_factory=SlurmConfig, description="SLURM scheduler settings.")
    scheduler: Literal["slurm", "pbs", "local"] = Field(default="slurm", description="Job scheduler backend.")

    @field_validator("name")
    @classmethod
    def name_must_be_filesystem_safe(cls, v: str) -> str:
        """Validate that the project name is safe to use as a directory name.

        Parameters
        ----------
        v : str
            The project name to validate.

        Returns
        -------
        str
            The validated project name, unchanged.

        Raises
        ------
        ValueError
            If the name contains characters other than alphanumerics, hyphens, or underscores.
        """
        import re

        if not re.fullmatch(r"[a-zA-Z0-9_-]+", v):
            raise ValueError(f"Project name {v!r} must contain only alphanumeric characters, hyphens, and underscores.")
        return v

    @field_validator("root")
    @classmethod
    def root_must_be_absolute(cls, v: Path) -> Path:
        """Validate that the project root is an absolute path.

        Parameters
        ----------
        v : Path
            The root path to validate.

        Returns
        -------
        Path
            The validated root path, unchanged.

        Raises
        ------
        ValueError
            If the path is relative rather than absolute.
        """
        if not v.is_absolute():
            raise ValueError(f"Project root must be an absolute path, got {v!r}.")
        return v

    @model_validator(mode="after")
    def replica_indices_must_be_unique_and_contiguous(self) -> Self:
        """Validate that replica indices are unique and form a contiguous zero-based sequence.

        Returns
        -------
        Self
            The validated model instance, unchanged.

        Raises
        ------
        ValueError
            If replica indices contain duplicates or gaps (e.g. [0, 2, 3] instead of [0, 1, 2]).
        """
        indices = [r.index for r in self.replicas]
        if len(indices) != len(set(indices)):
            raise ValueError(f"Replica indices must be unique, got duplicates in {indices!r}.")
        expected = list(range(len(indices)))
        if sorted(indices) != expected:
            raise ValueError(
                f"Replica indices must form a contiguous zero-based sequence {expected!r}, got {sorted(indices)!r}."
            )
        return self

    @property
    def n_replicas(self) -> int:
        """Return the number of replicas in the project.

        Returns
        -------
        int
            Total number of replicas.
        """
        return len(self.replicas)

    @property
    def toml_path(self) -> Path:
        """Return the expected path of the project TOML configuration file.

        Returns
        -------
        Path
            Absolute path to ``mdscaffold.toml`` at the project root.
        """
        return self.root / "mdscaffold.toml"

    @classmethod
    def from_toml(cls, project_dir: Path) -> "ProjectConfig":
        """Load and validate a ``ProjectConfig`` from a ``mdscaffold.toml`` file.

        Parameters
        ----------
        project_dir : Path
            Path to the directory containing ``mdscaffold.toml``. Typically the project root.

        Returns
        -------
        ProjectConfig
            Validated project configuration instance.

        Raises
        ------
        FileNotFoundError
            If ``mdscaffold.toml`` does not exist in ``project_dir``.
        tomllib.TOMLDecodeError
            If the TOML file is malformed.
        pydantic.ValidationError
            If the configuration values fail validation.

        Examples
        --------
        >>> config = ProjectConfig.from_toml(Path("/data/simulations/hspa1a_apo"))
        """
        import tomllib

        toml_path = project_dir / "mdscaffold.toml"
        if not toml_path.exists():
            raise FileNotFoundError(
                f"No mdscaffold.toml found in {project_dir!r}. Run 'mdscaffold new project' to initialise a project."
            )
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    def to_toml(self) -> None:
        """Serialise the project configuration to ``mdscaffold.toml`` at the project root.

        Creates the project root directory if it does not yet exist. Overwrites any existing
        ``mdscaffold.toml``. The output is suitable for round-tripping back through
        ``from_toml()``.

        Raises
        ------
        ImportError
            If ``tomli-w`` is not installed. Add it to your project dependencies:
            ``pip install tomli-w``.

        Examples
        --------
        >>> config.to_toml()  # writes to config.root / "mdscaffold.toml"
        """
        try:
            import tomli_w
        except ImportError as e:
            raise ImportError("Writing TOML requires 'tomli-w'. Install it with: pip install tomli-w") from e

        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.toml_path, "wb") as f:
            tomli_w.dump(self.model_dump(mode="json"), f)
