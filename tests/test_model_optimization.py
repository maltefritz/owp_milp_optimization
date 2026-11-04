"""Tests for ``EnergySystem.solve_model`` and ``EnergySystem.run_model``.

HiGHS is a dependency of the package, so it is used for real solves. The
Gurobi and SCIP branches are tested with a fake ``solph.Model.solve`` so that
no commercial or additional solver is needed (e.g. in CI).

The file has three parts:

1. Real HiGHS solves: does a small model solve, is the log file handled and
   are the options passed on to the solver?
2. Termination condition mapping: the solver is replaced by a fake that
   returns a preset termination condition, to check that ``solve_model``
   translates each one into the right status string ('ok', 'infeasable' or
   'unknown solver error').
3. ``run_model``: the full build-and-solve pipeline.
"""
import gc
import math
import sys
import types

import oemof.solph as solph
import pytest
from pyomo.contrib import appsi
from pyomo.contrib.appsi.base import TerminationCondition as AppsiTC
from pyomo.environ import value
from pyomo.opt import TerminationCondition as OptTC

from owp_milp_optimization import model
from owp_milp_optimization.model import EnergySystem


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Redirect the solver log directory of ``solve_model`` to tmp_path.

    ``solve_model`` writes its log to ``<dir of model.py>/solverlogs``. Faking
    the module's ``__file__`` keeps the tests from writing into the installed
    package. Returns the (not yet existing) ``solverlogs`` directory.
    """
    monkeypatch.setattr(model, '__file__', str(tmp_path / 'model.py'))
    return tmp_path / 'solverlogs'


@pytest.fixture
def gb_system(make_data, make_unit, make_opt):
    """Return a factory for a built (unsolved) gas boiler system.

    The smallest useful system: one gas boiler covering a flat 100 MW heat
    demand. Keyword arguments override the optimization parameters, e.g.
    ``gb_system(Solver='SCIP', TimeLimit=None)``.
    """
    def factory(**opt_overrides):
        es = EnergySystem(
            make_data(heat_demand=100.0),
            {'gb1': make_unit('gb', Q_rel_min=0.0)},
            make_opt(**opt_overrides),
        )
        es.generate_buses()
        es.generate_sources()
        es.generate_sinks()
        es.generate_components()
        return es
    return factory


# %% HiGHS (real solves)

def test_feasible_system_solves_ok(gb_system, log_dir):
    """A solvable system returns 'ok' and has a finite objective value."""
    es = gb_system()
    assert es.solve_model() == 'ok'
    assert math.isfinite(value(es.model.objective))


def test_solution_meets_fixed_demand(gb_system, log_dir):
    """The solution read back from pyomo is physically correct."""
    es = gb_system()
    es.solve_model()
    # The gas boiler is the only heat source and must cover 100 MW each hour
    flow = es.model.flow
    gb1, hnw = es.comps['gb1'], es.buses['hnw']
    for t in range(es.periods):
        assert value(flow[gb1, hnw, t]) == pytest.approx(100.0)


def test_highs_log_file_is_written(gb_system, log_dir):
    """Solving creates the solverlogs directory and a non-empty HiGHS log."""
    gb_system().solve_model()
    logfile = log_dir / 'highs_log.txt'
    assert logfile.is_file()
    assert logfile.stat().st_size > 0


def test_previous_log_file_is_replaced(gb_system, log_dir):
    """A log from an earlier run is deleted, not appended to."""
    log_dir.mkdir()
    (log_dir / 'highs_log.txt').write_text('STALE LOG CONTENT')
    gb_system().solve_model()
    assert 'STALE LOG CONTENT' not in (log_dir / 'highs_log.txt').read_text()


def test_unknown_solver_name(gb_system, log_dir, capsys):
    """An unsupported solver name is reported, not silently ignored.

    No solver branch matches, so the termination condition stays ``None``
    and ends up in the 'unknown solver error' branch.
    """
    es = gb_system(Solver='NoSuchSolver')
    assert es.solve_model() == 'unknown solver error'
    assert 'Termination Condition: None' in capsys.readouterr().out


@pytest.fixture
def infeasible_system(make_data, make_unit, make_opt):
    """A built system that has no feasible solution.

    A 10 MW boiler cannot cover a 100 MW fixed heat demand.
    """
    es = EnergySystem(
        make_data(heat_demand=100.0),
        {'gb1': make_unit('gb', cap_N=10.0, Q_rel_min=0.0)},
        make_opt(),
    )
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()
    return es


def test_infeasible_system_is_not_reported_ok(infeasible_system, log_dir):
    """Most important guarantee: an infeasible model is never 'ok'."""
    assert infeasible_system.solve_model() != 'ok'


@pytest.mark.xfail(
    strict=True,
    reason=(
        'BUG: with HiGHS, appsi raises a RuntimeError for infeasible models '
        'because config.load_solution is True. solve_model catches it and '
        'builds an empty HighsResults whose termination condition is '
        '"unknown", so "infeasable" is never returned for HiGHS.'
    )
)
def test_infeasible_system_is_reported_infeasible(infeasible_system, log_dir):
    """An infeasible model should get the specific 'infeasable' status."""
    assert infeasible_system.solve_model() == 'infeasable'


@pytest.fixture
def gc_disabled():
    """Pin the garbage collector off, making GC-timing dependent bugs
    deterministic."""
    gc.collect()
    gc.disable()
    yield
    gc.enable()
    gc.collect()


@pytest.mark.xfail(
    sys.platform == 'win32', raises=PermissionError, strict=True,
    reason=(
        'BUG (Windows): every solve writes to the same solverlogs/'
        'highs_log.txt inside the package and deletes it first. HiGHS keeps '
        'that file open until the garbage collector frees the previous '
        'solver, so a second solve in the same process fails with '
        'PermissionError depending on GC timing (pinned here by disabling '
        'the GC).'
    )
)
def test_consecutive_solves_with_shared_log_dir(
        log_dir, make_data, make_opt, full_dispatch_units, gb_system,
        gc_disabled):
    """Two solves in one process (e.g. two dashboard runs) both succeed.

    Both systems use the same log directory, like the dashboard does. The
    first solve's HiGHS instance still holds the log file open when the
    second solve tries to delete it.
    """
    first = EnergySystem(make_data(), full_dispatch_units, make_opt())
    first.run_model()

    second = gb_system()
    assert second.solve_model() == 'ok'


class SpyHighs(appsi.solvers.Highs):
    """Real HiGHS solver that remembers the instances used for solving.

    It solves normally, but lets a test inspect the ``config`` that
    ``solve_model`` set on the solver afterwards.
    """
    instances = []

    def solve(self, *args, **kwargs):
        SpyHighs.instances.append(self)
        return super().solve(*args, **kwargs)


@pytest.fixture
def spy_highs(monkeypatch):
    """Make ``solve_model`` use ``SpyHighs`` instead of appsi's Highs."""
    SpyHighs.instances = []
    monkeypatch.setattr(model.appsi.solvers, 'Highs', SpyHighs)
    return SpyHighs


def test_highs_receives_gap_time_limit_and_logfile(
        gb_system, log_dir, spy_highs):
    """MIPGap, TimeLimit and the log path from param_opt reach HiGHS."""
    gb_system(MIPGap=0.123, TimeLimit=42).solve_model()
    # Unpacking into one name also asserts that exactly one solver was used
    (solver,) = spy_highs.instances
    assert solver.config.mip_gap == 0.123
    assert solver.config.time_limit == 42
    assert solver.config.logfile == str(log_dir / 'highs_log.txt')


def test_highs_without_time_limit(gb_system, log_dir, spy_highs):
    """``TimeLimit=None`` means no time limit is set on the solver."""
    assert gb_system(TimeLimit=None).solve_model() == 'ok'
    (solver,) = spy_highs.instances
    assert solver.config.time_limit is None


# %% Termination condition mapping (fake solvers)
# A real solver cannot easily be forced into every termination condition
# (time limit, unbounded, error, ...), so these tests replace it with a fake
# that returns a preset condition and only check the translation into the
# status string of solve_model.

STATUS_CASES_APPSI = [
    (AppsiTC.optimal, 'ok'),
    (AppsiTC.objectiveLimit, 'ok'),
    (AppsiTC.maxTimeLimit, 'ok'),
    (AppsiTC.infeasible, 'infeasable'),
    (AppsiTC.unbounded, 'infeasable'),
    (AppsiTC.infeasibleOrUnbounded, 'infeasable'),
    (AppsiTC.error, 'unknown solver error'),
    (AppsiTC.interrupted, 'unknown solver error'),
    (AppsiTC.unknown, 'unknown solver error'),
]


class FakeHighs:
    """Stand-in for appsi's Highs returning a preset termination condition.

    It does not solve anything. Set ``termination_condition`` to choose the
    result, or ``raise_runtime_error`` to fail like appsi does when it finds
    no solution.
    """
    termination_condition = None
    raise_runtime_error = False

    def __init__(self):
        self.config = types.SimpleNamespace(
            mip_gap=None, logfile=None, time_limit=None
        )

    def solve(self, pyomo_model):
        if FakeHighs.raise_runtime_error:
            raise RuntimeError('A feasible solution was not found')
        return types.SimpleNamespace(
            termination_condition=FakeHighs.termination_condition
        )


@pytest.mark.parametrize('tc, expected', STATUS_CASES_APPSI)
def test_highs_termination_condition_mapping(
        tc, expected, gb_system, log_dir, monkeypatch):
    """Each appsi termination condition maps to the right status string."""
    monkeypatch.setattr(model.appsi.solvers, 'Highs', FakeHighs)
    monkeypatch.setattr(FakeHighs, 'termination_condition', tc)
    assert gb_system().solve_model() == expected


def test_highs_runtime_error_is_unknown_solver_error(
        gb_system, log_dir, monkeypatch):
    """A RuntimeError from appsi is caught and reported, not raised."""
    monkeypatch.setattr(model.appsi.solvers, 'Highs', FakeHighs)
    monkeypatch.setattr(FakeHighs, 'raise_runtime_error', True)
    assert gb_system().solve_model() == 'unknown solver error'


@pytest.fixture
def fake_solph_solve(monkeypatch):
    """Replace ``solph.Model.solve`` and record the call arguments.

    Gurobi and SCIP are called through ``solph.Model.solve``, so no solver
    has to be installed. Returns an object with ``calls`` (the keyword
    arguments of every call) and ``outcome['tc']`` (the termination
    condition the fake returns, ``optimal`` by default).
    """
    calls = []
    outcome = {'tc': OptTC.optimal}

    def fake_solve(self, **kwargs):
        calls.append(kwargs)
        return types.SimpleNamespace(
            Solver=types.SimpleNamespace(Termination_condition=outcome['tc'])
        )

    monkeypatch.setattr(solph.Model, 'solve', fake_solve)
    return types.SimpleNamespace(calls=calls, outcome=outcome)


def test_gurobi_options(gb_system, log_dir, fake_solph_solve):
    """param_opt is translated into Gurobi's option names."""
    status = gb_system(Solver='Gurobi', MIPGap=0.05, TimeLimit=30).solve_model()

    assert status == 'ok'
    (call,) = fake_solph_solve.calls
    assert call['solver'] == 'gurobi'
    assert call['allow_nonoptimal'] is True
    assert call['solve_kwargs'] == {'tee': True}
    assert call['cmdline_options'] == {
        'MIPGap': 0.05,
        'LogFile': str(log_dir / 'gurobi_log.txt'),
        'TimeLimit': 30,
    }


def test_scip_options(gb_system, log_dir, fake_solph_solve):
    """param_opt is translated into SCIP's option names."""
    status = gb_system(Solver='SCIP', MIPGap=0.05, TimeLimit=30).solve_model()

    assert status == 'ok'
    (call,) = fake_solph_solve.calls
    assert call['solver'] == 'scip'
    assert call['allow_nonoptimal'] is True
    assert call['cmdline_options'] == {
        'limits/gap': 0.05,
        'logfile': str(log_dir / 'scip_log.txt'),
        'limits/time': 30,
    }


@pytest.mark.parametrize('solver, time_key', [
    ('Gurobi', 'TimeLimit'), ('SCIP', 'limits/time')
])
def test_cli_solvers_without_time_limit(
        solver, time_key, gb_system, log_dir, fake_solph_solve):
    """``TimeLimit=None`` leaves the time option out for Gurobi and SCIP."""
    gb_system(Solver=solver, TimeLimit=None).solve_model()
    (call,) = fake_solph_solve.calls
    assert time_key not in call['cmdline_options']


@pytest.mark.parametrize('solver', ['Gurobi', 'SCIP'])
@pytest.mark.parametrize('tc, expected', [
    (OptTC.optimal, 'ok'),
    (OptTC.maxTimeLimit, 'ok'),
    # pyomo.opt has no objectiveLimit member, so a plain string is used
    ('objectiveLimit', 'ok'),
    (OptTC.infeasible, 'infeasable'),
    (OptTC.unbounded, 'infeasable'),
    (OptTC.infeasibleOrUnbounded, 'infeasable'),
    (OptTC.error, 'unknown solver error'),
    (OptTC.other, 'unknown solver error'),
])
def test_cli_solver_termination_condition_mapping(
        solver, tc, expected, gb_system, log_dir, fake_solph_solve):
    """Each pyomo.opt termination condition maps to the right status.

    Gurobi and SCIP report ``pyomo.opt`` conditions, not the appsi ones
    ``solve_model`` compares against. They still match because the pyomo.opt
    members are strings ('optimal', ...) and the lists in ``solve_model``
    also contain the plain string names.
    """
    fake_solph_solve.outcome['tc'] = tc
    assert gb_system(Solver=solver).solve_model() == expected


# %% run_model

def test_run_model_builds_and_solves(
        make_data, make_unit, make_opt, log_dir):
    """``run_model`` runs all generate_* steps and then solves the model."""
    es = EnergySystem(
        make_data(heat_demand=100.0),
        {'gb1': make_unit('gb', Q_rel_min=0.0)},
        make_opt(),
    )
    es.run_model()

    assert set(es.buses) == {'gnw', 'hnw'}
    assert {'gas_source', 'heat_sink', 'gb1'} <= set(es.comps)
    assert math.isfinite(value(es.model.objective))


def test_shipped_default_parameters_solve(
        shipped_defaults, make_data, solve_es):
    """The dashboard defaults (one unit of each type) solve with HiGHS."""
    param_units, param_opt = shipped_defaults
    es, status = solve_es(make_data(heat_demand=100.0), param_units, param_opt)
    assert status == 'ok'
    es.run_postprocessing()
    assert all(math.isfinite(v) for v in es.key_params.values())
