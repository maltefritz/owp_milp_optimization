"""Tests for ``EnergySystem.solve_model`` and ``EnergySystem.run_model``.

HiGHS is a dependency of the package, so it is used for real solves. All
three solvers (HiGHS, Gurobi, SCIP) are called through ``solph.Model.solve``,
which is replaced by a fake for the remaining tests, so that no commercial or
additional solver is needed (e.g. in CI).

The file has three parts:

1. Real HiGHS solves: does a small model solve, is the solver log kept and
   do the options really reach the solver?
2. Fake solves: are the options translated into each solver's names, and is
   each termination condition translated into the right status string ('ok',
   'infeasable' or 'unknown solver error')?
3. ``run_model``: the full build-and-solve pipeline.
"""
import gc
import math
import pathlib
import tempfile
import types

import oemof.solph as solph
import pytest
from pyomo.contrib.appsi.base import TerminationCondition as AppsiTC
from pyomo.environ import Var, value
from pyomo.opt import TerminationCondition as OptTC

from owp_milp_optimization.model import EnergySystem

# solph warns when the solver ends without an optimal solution. Tests that
# provoke this on purpose check the status returned by solve_model instead.
ignore_nonoptimal_warning = pytest.mark.filterwarnings(
    'ignore:The solver did not return an optimal solution:UserWarning'
)


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Redirect the temporary log directories of ``solve_model`` to tmp_path.

    Gurobi and SCIP write their log into a new temporary directory, which
    ``solve_model`` removes after reading the log. Redirecting the temporary
    directory of ``tempfile`` keeps these directories out of the user's temp
    folder and lets tests check that they are removed. Returns tmp_path.
    """
    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    return tmp_path


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


def test_highs_log_is_kept(gb_system, log_dir):
    """Solving keeps the content of the HiGHS log."""
    es = gb_system()
    es.solve_model()
    assert es.solver_log


def test_each_solve_keeps_its_own_log(gb_system, log_dir):
    """A second solve neither sees nor changes the log of the first one."""
    first = gb_system(MIPGap=0.123)
    first.solve_model()
    second = gb_system(MIPGap=0.05)
    second.solve_model()
    assert 'tolerance: 12.3%' in first.solver_log
    assert 'tolerance: 12.3%' not in second.solver_log


def test_highs_uses_mip_gap(gb_system, log_dir):
    """The MIP gap from param_opt really reaches HiGHS.

    HiGHS silently ignores unknown option names, so a misspelled option in
    ``solve_model`` would not cause any error. The solving report in the log
    shows the gap tolerance HiGHS actually used.
    """
    es = gb_system(MIPGap=0.123)
    es.solve_model()
    assert 'tolerance: 12.3%' in es.solver_log


@ignore_nonoptimal_warning
def test_highs_time_limit_without_solution(
        make_data, make_opt, full_dispatch_units, log_dir):
    """Hitting the time limit before any solution is found is not 'ok'.

    With ``TimeLimit=0``, HiGHS stops with ``maxTimeLimit`` right after
    presolve, before it found a solution. (The gas boiler system is too
    small for this, because presolve already solves it completely.) This
    also shows that the time limit really reaches HiGHS.
    """
    es = EnergySystem(make_data(), full_dispatch_units, make_opt(TimeLimit=0))
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()

    assert es.solve_model() == 'unknown solver error'
    # Make sure the 'no solution' case was tested, not some other failure
    assert es.model.solver_results['termination_condition'] == 'maxTimeLimit'


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


@ignore_nonoptimal_warning
def test_infeasible_system_is_not_reported_ok(infeasible_system, log_dir):
    """Most important guarantee: an infeasible model is never 'ok'."""
    assert infeasible_system.solve_model() != 'ok'


@ignore_nonoptimal_warning
def test_infeasible_system_is_reported_infeasible(infeasible_system, log_dir):
    """An infeasible model gets the specific 'infeasable' status."""
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


def test_consecutive_solves(
        log_dir, make_data, make_opt, full_dispatch_units, gb_system,
        gc_disabled):
    """Two solves in one process (e.g. two dashboard runs) both succeed.

    When all solves shared one log file, the second solve failed on Windows
    with a PermissionError, because HiGHS kept the file of the first solve
    open until the garbage collector freed it (pinned here by disabling the
    GC).
    """
    first = EnergySystem(make_data(), full_dispatch_units, make_opt())
    first.run_model()

    second = gb_system()
    assert second.solve_model() == 'ok'


# %% Fake solves: options and termination condition mapping
# A real solver cannot easily be forced into every termination condition
# (unbounded, error, time limit with or without a solution, ...), and Gurobi
# and SCIP may not be installed. These tests replace solph.Model.solve with a
# fake that only records how it was called and stores preset results.

@pytest.fixture
def fake_solph_solve(monkeypatch):
    """Replace ``solph.Model.solve`` and record the call arguments.

    Like the real method, the fake stores the solver's results in
    ``model.solver_results``, which ``solve_model`` reads afterwards. For
    HiGHS, solph stores a dict with the *name* of the appsi termination
    condition. For all other solvers, it stores pyomo's ``SolverResults``,
    which hold the ``pyomo.opt`` termination condition itself.

    Returns an object with

    - ``calls``: the keyword arguments of every call,
    - ``outcome['tc']``: the termination condition to report (``optimal``
      by default; an appsi member for HiGHS, a pyomo.opt member otherwise),
    - ``outcome['solution']``: whether a solution is loaded into the model
      (``True`` by default). All variables are then set to 0, so that the
      objective can be evaluated, as it would after a real solve.
    """
    calls = []
    outcome = {'tc': None, 'solution': True}

    def fake_solve(self, **kwargs):
        calls.append(kwargs)
        tc = outcome['tc']
        if outcome['solution']:
            for var in self.component_data_objects(Var):
                var.set_value(0)
        if kwargs['solver'] == 'highs':
            self.solver_results = {
                'termination_condition': (tc or AppsiTC.optimal).name
            }
        else:
            self.solver_results = types.SimpleNamespace(
                Solver=types.SimpleNamespace(
                    Termination_condition=tc or OptTC.optimal
                )
            )

    monkeypatch.setattr(solph.Model, 'solve', fake_solve)
    return types.SimpleNamespace(calls=calls, outcome=outcome)


# Each solver's own names for the options set from param_opt
OPTION_NAMES = {
    # solver: (solph name, MIPGap, TimeLimit)
    'HiGHS': ('highs', 'mip_rel_gap', 'time_limit'),
    'Gurobi': ('gurobi', 'MIPGap', 'TimeLimit'),
    'SCIP': ('scip', 'limits/gap', 'limits/time'),
}

# Gurobi and SCIP write their log into a file, HiGHS needs none
LOG_FILE_OPTIONS = {'Gurobi': 'LogFile', 'SCIP': 'logfile'}


@pytest.mark.parametrize('solver', OPTION_NAMES)
def test_solver_options(solver, gb_system, log_dir, fake_solph_solve):
    """param_opt is translated into each solver's own option names.

    Non optimal results must be allowed, so that solph returns instead of
    raising and ``solve_model`` can report the status. Gurobi and SCIP also
    print their output to the console (``tee``).
    """
    solph_name, gap_key, time_key = OPTION_NAMES[solver]
    status = gb_system(Solver=solver, MIPGap=0.05, TimeLimit=30).solve_model()

    assert status == 'ok'
    (call,) = fake_solph_solve.calls
    assert call['solver'] == solph_name
    assert call['allow_nonoptimal'] is True
    if solver != 'HiGHS':
        assert call['solve_kwargs'] == {'tee': True}
    # The log file option is checked in test_log_file_in_temporary_directory
    options = dict(call['cmdline_options'])
    options.pop(LOG_FILE_OPTIONS.get(solver), None)
    assert options == {gap_key: 0.05, time_key: 30}


@pytest.mark.parametrize('solver', LOG_FILE_OPTIONS)
def test_log_file_in_temporary_directory(
        solver, gb_system, log_dir, fake_solph_solve):
    """Gurobi and SCIP log into a temporary directory, which is removed."""
    gb_system(Solver=solver).solve_model()
    (call,) = fake_solph_solve.calls
    logfile = pathlib.Path(call['cmdline_options'][LOG_FILE_OPTIONS[solver]])
    assert logfile.name == f'{solver.lower()}_log.txt'
    assert logfile.parent.parent == log_dir
    assert not logfile.parent.exists()


@pytest.mark.parametrize('solver', OPTION_NAMES)
def test_solvers_without_time_limit(
        solver, gb_system, log_dir, fake_solph_solve):
    """``TimeLimit=None`` leaves the time option out for every solver."""
    time_key = OPTION_NAMES[solver][2]
    assert gb_system(Solver=solver, TimeLimit=None).solve_model() == 'ok'
    (call,) = fake_solph_solve.calls
    assert time_key not in call['cmdline_options']


@pytest.mark.parametrize('solver', ['HiGHS', 'SCIP'])
def test_no_log_without_solver_output(
        solver, gb_system, log_dir, fake_solph_solve):
    """Without any log output from the solver (like SCIP), there is no log."""
    es = gb_system(Solver=solver)
    assert es.solve_model() == 'ok'
    assert es.solver_log is None


OK, INFEASIBLE, UNKNOWN = 'ok', 'infeasable', 'unknown solver error'

# (termination condition, status with a solution, status without a solution)
# 'ok' needs a solution: a solver can hit a limit before it finds one.
STATUS_CASES_HIGHS = [
    (AppsiTC.optimal, OK, UNKNOWN),
    (AppsiTC.objectiveLimit, OK, UNKNOWN),
    (AppsiTC.maxTimeLimit, OK, UNKNOWN),
    (AppsiTC.infeasible, INFEASIBLE, INFEASIBLE),
    (AppsiTC.unbounded, INFEASIBLE, INFEASIBLE),
    (AppsiTC.infeasibleOrUnbounded, INFEASIBLE, INFEASIBLE),
    (AppsiTC.error, UNKNOWN, UNKNOWN),
    (AppsiTC.interrupted, UNKNOWN, UNKNOWN),
    (AppsiTC.unknown, UNKNOWN, UNKNOWN),
]

STATUS_CASES_CLI = [
    (OptTC.optimal, OK, UNKNOWN),
    (OptTC.maxTimeLimit, OK, UNKNOWN),
    # pyomo.opt has no objectiveLimit member, so a plain string is used
    ('objectiveLimit', OK, UNKNOWN),
    (OptTC.infeasible, INFEASIBLE, INFEASIBLE),
    (OptTC.unbounded, INFEASIBLE, INFEASIBLE),
    (OptTC.infeasibleOrUnbounded, INFEASIBLE, INFEASIBLE),
    (OptTC.error, UNKNOWN, UNKNOWN),
    (OptTC.other, UNKNOWN, UNKNOWN),
]


@pytest.mark.parametrize(
    'solution', [True, False], ids=['solution', 'no_solution']
)
@pytest.mark.parametrize('tc, with_solution, without_solution',
                         STATUS_CASES_HIGHS)
def test_highs_termination_condition_mapping(
        tc, with_solution, without_solution, solution, gb_system, log_dir,
        fake_solph_solve):
    """Each appsi termination condition maps to the right status string.

    ``solve_model`` compares the condition's name, which solph stores for
    HiGHS, against plain strings.
    """
    fake_solph_solve.outcome.update(tc=tc, solution=solution)
    expected = with_solution if solution else without_solution
    assert gb_system().solve_model() == expected


@pytest.mark.parametrize('solver', ['Gurobi', 'SCIP'])
@pytest.mark.parametrize(
    'solution', [True, False], ids=['solution', 'no_solution']
)
@pytest.mark.parametrize('tc, with_solution, without_solution',
                         STATUS_CASES_CLI)
def test_cli_solver_termination_condition_mapping(
        solver, tc, with_solution, without_solution, solution, gb_system,
        log_dir, fake_solph_solve):
    """Each pyomo.opt termination condition maps to the right status.

    Gurobi and SCIP report the ``pyomo.opt`` conditions themselves, not
    their names. They still match the plain strings in ``solve_model``,
    because the pyomo.opt members are strings ('optimal', ...).
    """
    fake_solph_solve.outcome.update(tc=tc, solution=solution)
    expected = with_solution if solution else without_solution
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
