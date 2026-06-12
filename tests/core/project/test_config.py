# ------------------------------------------------------------------------------
#  Copyright (c) 2026 Timothy H. Click, Ph.D.
#
#  This file is part of mdscaffold.
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
"""Tests for ``mdscaffold.core.project.config``.

Covers all four Pydantic models defined in ``config.py``:
``ReplicaConfig``, ``SlurmConfig``, ``SimulationConfig``, and
``ProjectConfig``. Validation logic, computed properties, and TOML
round-trip I/O are all exercised.

Test strategy
-------------
Plain pytest
    Used for concrete examples, TOML I/O (requires a real filesystem),
    and assertions about error message text where the exact wording
    matters.

Hypothesis property-based tests
    Used wherever a validator has a clear valid/invalid boundary that
    hand-picked examples would under-cover:

    - ``ReplicaConfig.seed`` — positive odd integers vs even/negative
    - ``ProjectConfig.name`` — filesystem-safe character set
    - ``ProjectConfig.root`` — absolute vs relative paths
    - ``ProjectConfig`` replica index contiguity
    - ``SimulationConfig.prod_time_ns`` — arithmetic identity

    Hypothesis strategies are defined at module level and reused
    across tests to keep individual test functions concise.

Notes
-----
All tests are self-contained and use ``tmp_path`` (pytest fixture) or
``tmp_path_factory`` for filesystem operations. No real Amber
installation or HPC scheduler is required.

The ``from_toml`` / ``to_toml`` tests require ``tomli-w`` to be
installed (``pip install tomli-w``). The read-only ``from_toml`` path
uses only the standard-library ``tomllib`` and has no extra
dependencies.
"""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from mdscaffold.core.project.config import (
    ProjectConfig,
    ReplicaConfig,
    SimulationConfig,
    SlurmConfig,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Valid Amber seeds: positive odd integers.
valid_seeds: st.SearchStrategy[int] = st.integers(min_value=1, max_value=2**31 - 1).filter(lambda n: n % 2 == 1)

# Invalid seeds: zero, negative integers, or positive even integers (excluding -1).
invalid_seeds: st.SearchStrategy[int] = st.one_of(
    st.integers(max_value=-2),
    st.just(0),
    st.integers(min_value=2).filter(lambda n: n % 2 == 0),
)

# Valid project names: non-empty strings of alphanumerics, hyphens, and underscores.
valid_names: st.SearchStrategy[str] = st.from_regex(r"[a-zA-Z0-9_-]+", fullmatch=True)

# Invalid project names: strings containing at least one forbidden character.
invalid_names: st.SearchStrategy[str] = st.text(
    alphabet=st.characters(
        blacklist_categories=("Lu", "Ll", "Nd"),
        blacklist_characters="-_",
    ),
    min_size=1,
)

# Valid walltimes: HH:MM:SS strings with in-range minutes and seconds.
valid_walltimes: st.SearchStrategy[str] = st.builds(
    lambda h, m, s: f"{h:02d}:{m:02d}:{s:02d}",
    h=st.integers(min_value=0, max_value=999),
    m=st.integers(min_value=0, max_value=59),
    s=st.integers(min_value=0, max_value=59),
)

# Invalid walltimes: out-of-range minutes or seconds, or wrong format entirely.
invalid_walltimes: st.SearchStrategy[str] = st.one_of(
    st.builds(
        lambda h, m, s: f"{h:02d}:{m:02d}:{s:02d}",
        h=st.integers(min_value=0, max_value=99),
        m=st.integers(min_value=60, max_value=99),
        s=st.integers(min_value=0, max_value=59),
    ),
    st.builds(
        lambda h, m, s: f"{h:02d}:{m:02d}:{s:02d}",
        h=st.integers(min_value=0, max_value=99),
        m=st.integers(min_value=0, max_value=59),
        s=st.integers(min_value=60, max_value=99),
    ),
    st.just("not-a-walltime"),
    st.just("24:00"),
    st.just(""),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_replica(index: int = 0, seed: int = 11111) -> ReplicaConfig:
    """Construct a ``ReplicaConfig`` with sensible defaults.

    Parameters
    ----------
    index : int, optional
        Replica index. Defaults to 0.
    seed : int, optional
        Amber random seed. Must be a positive odd integer. Defaults to 11111.

    Returns
    -------
    ReplicaConfig
        A valid ``ReplicaConfig`` instance.
    """
    return ReplicaConfig(index=index, seed=seed)


def make_project(
    *,
    name: str = "test-project",
    root: Path | None = None,
    n_replicas: int = 2,
    tmp_path: Path | None = None,
) -> ProjectConfig:
    """Construct a minimal valid ``ProjectConfig`` for use in tests.

    Parameters
    ----------
    name : str, optional
        Project name. Defaults to ``'test-project'``.
    root : Path or None, optional
        Absolute root path. If ``None``, defaults to ``tmp_path / name``
        when ``tmp_path`` is provided, or ``Path('/tmp') / name`` otherwise.
    n_replicas : int, optional
        Number of replicas. Defaults to 2.
    tmp_path : Path or None, optional
        Pytest ``tmp_path`` fixture value used to construct a default root.

    Returns
    -------
    ProjectConfig
        A valid ``ProjectConfig`` instance.
    """
    if root is None:
        base = tmp_path if tmp_path is not None else Path("/tmp")
        root = base / name
    replicas = [ReplicaConfig(index=i, seed=2 * i + 1) for i in range(n_replicas)]
    return ProjectConfig(name=name, root=root, replicas=replicas)


# ---------------------------------------------------------------------------
# ReplicaConfig
# ---------------------------------------------------------------------------


class TestReplicaConfig:
    """Tests for ``ReplicaConfig`` validation and properties.

    Methods
    -------
    test_valid_seed_accepted
        Property-based: any positive odd integer is accepted as a seed.
    test_invalid_seed_rejected
        Property-based: even, zero, and negative integers (except -1) are rejected.
    test_clock_seed_accepted
        Literal -1 is accepted as a special clock-based seed value.
    test_dir_name_zero_padded
        ``dir_name`` property returns a two-digit zero-padded string.
    test_dir_name_large_index
        ``dir_name`` does not truncate indices larger than 9.
    test_index_negative_rejected
        Negative replica indices are rejected by the ``ge=0`` constraint.
    """

    @given(seed=valid_seeds)
    def test_valid_seed_accepted(self, seed: int) -> None:
        """Any positive odd integer is accepted as a valid Amber seed.

        Parameters
        ----------
        seed : int
            A positive odd integer generated by Hypothesis.
        """
        replica = ReplicaConfig(index=0, seed=seed)
        assert replica.seed == seed

    @given(seed=invalid_seeds)
    def test_invalid_seed_rejected(self, seed: int) -> None:
        """Even integers, zero, and negative integers other than -1 are rejected.

        Parameters
        ----------
        seed : int
            An invalid seed value generated by Hypothesis.
        """
        with pytest.raises(ValidationError):
            ReplicaConfig(index=0, seed=seed)

    def test_clock_seed_accepted(self) -> None:
        """Seed value -1 is accepted as a special clock-based seed.

        Notes
        -----
        Amber uses ``ig = -1`` to generate a seed from the system clock.
        This is permitted but not recommended for reproducible simulations.
        """
        replica = ReplicaConfig(index=0, seed=-1)
        assert replica.seed == -1

    @pytest.mark.parametrize(
        ("index", "expected"),
        [
            (0, "replica_00"),
            (1, "replica_01"),
            (9, "replica_09"),
            (10, "replica_10"),
        ],
    )
    def test_dir_name_zero_padded(self, index: int, expected: str) -> None:
        """``dir_name`` returns a zero-padded two-digit replica directory name.

        Parameters
        ----------
        index : int
            Replica index.
        expected : str
            Expected directory name string.
        """
        replica = make_replica(index=index)
        assert replica.dir_name == expected

    def test_dir_name_large_index(self) -> None:
        """``dir_name`` does not truncate indices with more than two digits.

        Notes
        -----
        The ``{index:02d}`` format pads to a minimum of two digits but does
        not cap at two digits, so index 100 produces ``'replica_100'`` rather
        than truncating or raising.
        """
        replica = make_replica(index=100)
        assert replica.dir_name == "replica_100"

    def test_index_negative_rejected(self) -> None:
        """Negative replica indices are rejected by the ``ge=0`` field constraint."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ReplicaConfig(index=-1, seed=11111)


# ---------------------------------------------------------------------------
# SlurmConfig
# ---------------------------------------------------------------------------


class TestSlurmConfig:
    """Tests for ``SlurmConfig`` validation and defaults.

    Methods
    -------
    test_defaults
        Default values match documented standard settings.
    test_valid_walltime_accepted
        Property-based: any well-formed HH:MM:SS walltime is accepted.
    test_invalid_walltime_rejected
        Property-based: malformed or out-of-range walltimes are rejected.
    test_n_gpus_zero_rejected
        Zero GPU count is rejected by the ``ge=1`` constraint.
    test_n_cpus_zero_rejected
        Zero CPU count is rejected.
    test_mem_gb_zero_rejected
        Zero memory is rejected.
    test_account_none_by_default
        The ``account`` field defaults to ``None``.
    test_account_accepts_string
        A non-None string account name is accepted.
    """

    def test_defaults(self) -> None:
        """Default ``SlurmConfig`` values match documented standard settings.

        Notes
        -----
        Checks all default field values in a single assertion block to keep
        the test concise. Changes to defaults will be caught immediately.
        """
        slurm = SlurmConfig()
        assert slurm.partition == "debug"
        assert slurm.n_gpus == 1
        assert slurm.n_cpus == 8
        assert slurm.mem_gb == 8
        assert slurm.walltime == "24:00:00"
        assert slurm.account is None

    @given(walltime=valid_walltimes)
    def test_valid_walltime_accepted(self, walltime: str) -> None:
        """Any well-formed HH:MM:SS walltime with in-range minutes and seconds is accepted.

        Parameters
        ----------
        walltime : str
            A valid HH:MM:SS string generated by Hypothesis.
        """
        slurm = SlurmConfig(walltime=walltime)
        assert slurm.walltime == walltime

    @given(walltime=invalid_walltimes)
    def test_invalid_walltime_rejected(self, walltime: str) -> None:
        """Malformed or out-of-range walltimes are rejected by the field validator.

        Parameters
        ----------
        walltime : str
            An invalid walltime string generated by Hypothesis.
        """
        with pytest.raises(ValidationError):
            SlurmConfig(walltime=walltime)

    def test_zero_n_gpus_rejected(self) -> None:
        """Zero GPU count is rejected by the ``ge=1`` constraint on ``n_gpus``."""
        with pytest.raises(ValidationError):
            SlurmConfig(n_gpus=0)

    def test_zero_n_cpus_rejected(self) -> None:
        """Zero CPU count is rejected by the ``ge=1`` constraint on ``n_cpus``."""
        with pytest.raises(ValidationError):
            SlurmConfig(n_cpus=0)

    def test_zero_mem_gb_rejected(self) -> None:
        """Zero memory is rejected by the ``ge=1`` constraint on ``mem_gb``."""
        with pytest.raises(ValidationError):
            SlurmConfig(mem_gb=0)

    def test_account_none_by_default(self) -> None:
        """The SLURM account field defaults to ``None`` and is omitted from job scripts."""
        assert SlurmConfig().account is None

    def test_account_accepts_string(self) -> None:
        """A non-None string account name is stored without modification."""
        slurm = SlurmConfig(account="md-group")
        assert slurm.account == "md-group"


# ---------------------------------------------------------------------------
# SimulationConfig
# ---------------------------------------------------------------------------


class TestSimulationConfig:
    """Tests for ``SimulationConfig`` validation and computed properties.

    Methods
    -------
    test_defaults
        Default parameter values match standard Amber NPT settings.
    test_prod_time_ns_identity
        Property-based: ``prod_time_ns`` equals the expected arithmetic identity.
    test_zero_temp_rejected
        Zero target temperature is rejected by the ``gt=0`` constraint.
    test_zero_pressure_rejected
        Zero target pressure is rejected.
    test_zero_timestep_rejected
        Zero timestep is rejected.
    test_zero_cutoff_rejected
        Zero non-bonded cutoff is rejected.
    test_zero_n_prod_steps_rejected
        Zero production steps is rejected by the ``ge=1`` constraint.
    test_zero_n_prod_runs_rejected
        Zero production runs is rejected.
    """

    def test_defaults(self) -> None:
        """Default values match standard Amber NPT settings (300 K, 1 bar, 2 fs, 10 Å).

        Notes
        -----
        Default production settings encode 10 x 100 ns = 1 µs per replica.
        """
        sim = SimulationConfig()
        assert sim.target_temp == 300.0
        assert sim.target_pressure == 1.0
        assert sim.timestep_fs == 2.0
        assert sim.cutoff_angstrom == 10.0
        assert sim.n_prod_steps == 50_000_000
        assert sim.n_prod_runs == 10

    @given(
        n_runs=st.integers(min_value=1, max_value=100),
        n_steps=st.integers(min_value=1, max_value=100_000_000),
        timestep=st.floats(min_value=0.001, max_value=4.0, allow_nan=False, allow_infinity=False),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_prod_time_ns_identity(
        self,
        n_runs: int | float,
        n_steps: int | float,
        timestep: float,
    ) -> None:
        """``prod_time_ns`` equals ``n_prod_runs x n_prod_steps x timestep_fs x 1e-6``.

        Parameters
        ----------
        n_runs : int | float
            Number of production run segments. Typed ``int | float`` to satisfy Hypothesis
            type inference when ``integers()`` and ``floats()`` strategies share a ``@given``
            decorator; cast to ``int`` before passing to ``SimulationConfig``.
        n_steps : int | float
            Number of MD steps per production segment. Cast to ``int`` before use.
        timestep : float
            Integration timestep in femtoseconds. Infinities and NaN are excluded by the
            strategy to ensure ``SimulationConfig`` validation does not raise.

        Notes
        -----
        Hypothesis infers drawn argument types as ``int | float`` when ``integers()`` and
        ``floats()`` strategies are combined in a single ``@given`` call. The explicit
        ``int | float`` annotation reflects this; the ``int()`` casts below restore the
        correct runtime type expected by ``SimulationConfig``.

        Uses ``pytest.approx`` to allow for floating-point rounding in the multiplication.
        A relative tolerance of 1e-6 is sufficient for all physically meaningful combinations
        of timestep and step count.
        """
        n_runs_int: int = int(n_runs)
        n_steps_int: int = int(n_steps)
        sim = SimulationConfig(
            n_prod_runs=n_runs_int,
            n_prod_steps=n_steps_int,
            timestep_fs=timestep,
        )
        expected = n_runs_int * n_steps_int * timestep * 1e-6
        assert sim.prod_time_ns == pytest.approx(expected, rel=1e-6)

    def test_zero_target_temp_rejected(self) -> None:
        """Zero target temperature is rejected by the ``gt=0`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(target_temp=0.0)

    def test_zero_target_pressure_rejected(self) -> None:
        """Zero target pressure is rejected by the ``gt=0`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(target_pressure=0.0)

    def test_zero_timestep_fs_rejected(self) -> None:
        """Zero timestep is rejected by the ``gt=0`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(timestep_fs=0.0)

    def test_zero_cutoff_angstrom_rejected(self) -> None:
        """Zero non-bonded cutoff is rejected by the ``gt=0`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(cutoff_angstrom=0.0)

    def test_zero_n_prod_steps_rejected(self) -> None:
        """Zero production step count is rejected by the ``ge=1`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(n_prod_steps=0)

    def test_zero_n_prod_runs_rejected(self) -> None:
        """Zero production run count is rejected by the ``ge=1`` constraint."""
        with pytest.raises(ValidationError):
            SimulationConfig(n_prod_runs=0)


# ---------------------------------------------------------------------------
# ProjectConfig
# ---------------------------------------------------------------------------


class TestProjectConfig:
    """Tests for ``ProjectConfig`` validation, properties, and TOML I/O.

    Methods
    -------
    test_valid_name_accepted
        Property-based: any non-empty alphanumeric/hyphen/underscore name is accepted.
    test_invalid_name_rejected
        Property-based: names containing forbidden characters are rejected.
    test_absolute_root_accepted
        An absolute ``Path`` is accepted as the project root.
    test_relative_root_rejected
        A relative ``Path`` is rejected by the root validator.
    test_n_replicas_property
        ``n_replicas`` returns the length of the replicas list.
    test_toml_path_property
        ``toml_path`` returns ``root / 'mdscaffold.toml'``.
    test_duplicate_replica_indices_rejected
        Duplicate replica indices trigger a ``model_validator`` error.
    test_non_contiguous_replica_indices_rejected
        Gaps in replica indices are rejected.
    test_empty_replicas_rejected
        An empty replicas list is rejected by the ``min_length=1`` constraint.
    test_from_toml_roundtrip
        A config saved with ``to_toml`` is recovered identically by ``from_toml``.
    test_from_toml_missing_file_raises
        ``from_toml`` raises ``FileNotFoundError`` with an actionable message.
    test_to_toml_creates_root_dir
        ``to_toml`` creates the project root directory if it does not exist.
    """

    @given(name=valid_names)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_name_accepted(self, name: str) -> None:
        """Any non-empty string of alphanumerics, hyphens, and underscores is accepted.

        Parameters
        ----------
        name : str
            A valid project name generated by Hypothesis.
        """
        config = make_project(name=name)
        assert config.name == name

    @given(name=invalid_names)
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_name_rejected(self, name: str) -> None:
        """Names containing characters outside ``[a-zA-Z0-9_-]`` are rejected.

        Parameters
        ----------
        name : str
            An invalid project name generated by Hypothesis.
        """
        with pytest.raises(ValidationError):
            make_project(name=name)

    def test_absolute_root_accepted(self, tmp_path: Path) -> None:
        """An absolute ``Path`` is accepted as the project root without modification.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory (always absolute).
        """
        config = make_project(root=tmp_path / "myproject")
        assert config.root.is_absolute()

    def test_relative_root_rejected(self) -> None:
        """A relative ``Path`` is rejected by the ``root_must_be_absolute`` validator.

        Notes
        -----
        The error message should reference the invalid path to aid debugging.
        """
        with pytest.raises(ValidationError, match="absolute path"):
            make_project(root=Path("relative/path"))

    @pytest.mark.parametrize("n", [1, 2, 5, 10])
    def test_n_replicas_property(self, n: int) -> None:
        """``n_replicas`` returns the number of replicas in the project.

        Parameters
        ----------
        n : int
            Number of replicas to create.
        """
        config = make_project(n_replicas=n)
        assert config.n_replicas == n

    def test_toml_path_property(self, tmp_path: Path) -> None:
        """``toml_path`` returns ``root / 'mdscaffold.toml'``.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory.
        """
        config = make_project(tmp_path=tmp_path)
        assert config.toml_path == config.root / "mdscaffold.toml"

    def test_duplicate_replica_indices_rejected(self, tmp_path: Path) -> None:
        """Duplicate replica indices are caught by the ``model_validator``.

        Notes
        -----
        Two replicas with ``index=0`` should raise a ``ValidationError``
        mentioning uniqueness, not a silent deduplication.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory.
        """
        replicas = [
            ReplicaConfig(index=0, seed=11111),
            ReplicaConfig(index=0, seed=33333),
        ]
        with pytest.raises(ValidationError, match="unique"):
            ProjectConfig(name="dup-test", root=tmp_path / "dup", replicas=replicas)

    def test_non_contiguous_replica_indices_rejected(self, tmp_path: Path) -> None:
        """Gaps in replica indices (e.g. [0, 2]) are rejected by the ``model_validator``.

        Notes
        -----
        The scaffold layer derives directory names from indices and depends on
        a contiguous sequence. Gaps would silently produce an incomplete directory
        tree if not caught at construction time.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory.
        """
        replicas = [
            ReplicaConfig(index=0, seed=11111),
            ReplicaConfig(index=2, seed=33333),
        ]
        with pytest.raises(ValidationError, match="contiguous"):
            ProjectConfig(name="gap-test", root=tmp_path / "gap", replicas=replicas)

    def test_empty_replicas_rejected(self, tmp_path: Path) -> None:
        """An empty replicas list is rejected by the ``min_length=1`` field constraint.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory.
        """
        with pytest.raises(ValidationError):
            ProjectConfig(name="empty", root=tmp_path / "empty", replicas=[])

    def test_from_toml_roundtrip(self, tmp_path: Path) -> None:
        """A config serialised with ``to_toml`` is recovered identically by ``from_toml``.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory used as the project root.

        Notes
        -----
        Compares ``model_dump()`` outputs rather than model instances directly,
        since Pydantic models do not implement ``__eq__`` by value for nested
        models by default. All nested fields (replicas, simulation, slurm) are
        included in the comparison.
        """
        pytest.importorskip("tomli_w", reason="tomli-w required for to_toml()")
        original = make_project(tmp_path=tmp_path, n_replicas=3)
        original.to_toml()
        recovered = ProjectConfig.from_toml(original.root)
        assert recovered.model_dump() == original.model_dump()

    def test_from_toml_missing_file_raises(self, tmp_path: Path) -> None:
        """``from_toml`` raises ``FileNotFoundError`` when no ``mdscaffold.toml`` is present.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided empty temporary directory (contains no TOML file).

        Notes
        -----
        The error message should include the string ``'mdscaffold new project'``
        to direct the user to the correct remediation command.
        """
        with pytest.raises(FileNotFoundError, match="mdscaffold new project"):
            ProjectConfig.from_toml(tmp_path)

    def test_to_toml_creates_root_dir(self, tmp_path: Path) -> None:
        """``to_toml`` creates the project root directory tree if it does not yet exist.

        Parameters
        ----------
        tmp_path : Path
            Pytest-provided temporary directory. The project root is set to a
            non-existent subdirectory to verify that ``mkdir(parents=True)`` is called.

        Notes
        -----
        This verifies that running ``mdscaffold new project`` on a fresh machine
        does not require the user to manually create the target directory first.
        """
        pytest.importorskip("tomli_w", reason="tomli-w required for to_toml()")
        root = tmp_path / "new" / "nested" / "project"
        assert not root.exists()
        config = make_project(root=root)
        config.to_toml()
        assert root.exists()
        assert (root / "mdscaffold.toml").exists()
