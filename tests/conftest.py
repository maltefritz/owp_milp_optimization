"""Shared fixtures for the tests of ``owp_milp_optimization.model``.

The fixtures provide

- deterministic, synthetic 24 h input time series (``make_data``),
- explicit unit and optimization parameters that do not depend on the
  defaults shipped in ``input/*.json`` (``make_unit``, ``make_opt``),
- a helper that builds and solves an ``EnergySystem`` the same way the
  Streamlit app does (``solve_es``), and
- a handful of solved reference scenarios that many tests read from.

The solved scenarios are session scoped because solving is the expensive
part. Tests must treat them as read-only.
"""
import copy
import json
import os
from importlib import resources

import numpy as np
import pandas as pd
import pytest

from owp_milp_optimization import model

N_STEPS = 24

UNIT_DEFAULTS = {
    'hp': {
        'cap_N': 40.0, 'Q_rel_max': 1.0, 'Q_rel_min': 0.3, 'cop': 3.5,
        'op_cost_var': 1.2, 'op_cost_fix': 4000.0, 'inv_spez': 510000.0,
        'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0, 'invest_mode': False,
        'cap_max': 100.0, 'cap_min': 0.0,
    },
    'ccet': {
        'cap_N': 30.0, 'Q_rel_max': 1.0, 'Q_rel_min': 0.5, 'eta_th': 0.5,
        'eta_el': 0.35, 'op_cost_var': 4.4, 'op_cost_fix': 29300.0,
        'inv_spez': 880000.0, 'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0,
        'invest_mode': False, 'cap_max': 100.0, 'cap_min': 0.0,
    },
    'ice': {
        'cap_N': 20.0, 'Q_rel_max': 1.0, 'Q_rel_min': 0.4, 'eta_th': 0.45,
        'eta_el': 0.40, 'op_cost_var': 7.5, 'op_cost_fix': 9750.0,
        'inv_spez': 950000.0, 'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0,
        'invest_mode': False, 'cap_max': 100.0, 'cap_min': 0.0,
    },
    'gb': {
        'cap_N': 150.0, 'Q_rel_max': 1.0, 'Q_rel_min': 0.1, 'eta': 0.95,
        'op_cost_var': 1.1, 'op_cost_fix': 1950.0, 'inv_spez': 60000.0,
        'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0, 'invest_mode': False,
        'cap_max': 200.0, 'cap_min': 0.0,
    },
    'eb': {
        'cap_N': 30.0, 'Q_rel_max': 1.0, 'Q_rel_min': 0.0, 'eta': 0.99,
        'op_cost_var': 0.9, 'op_cost_fix': 1070.0, 'inv_spez': 150000.0,
        'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0, 'invest_mode': False,
        'cap_max': 50.0, 'cap_min': 0.0,
    },
    'sol': {
        'A_N': 20000.0, 'eta_col': 0.4, 'op_cost_var': 0.22,
        'op_cost_fix': 0.04, 'inv_spez': 199.0, 'op_cost_bonus_rel': 0.0,
        'inv_bonus_rel': 0.0, 'invest_mode': False, 'A_max': 50000.0,
        'A_min': 0.0,
    },
    'exhs': {
        'cap_N': 5.0, 'inv_spez': 0.0, 'op_cost_var': 20.0,
        'op_cost_fix': 0.0, 'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0,
        'invest_mode': False, 'cap_max': 20.0, 'cap_min': 0.0, 'fix': False,
    },
    'tes': {
        'Q_N': 200.0, 'op_cost_var': 0.0, 'op_cost_fix': 3.0,
        'inv_spez': 580.0, 'op_cost_bonus_rel': 0.0, 'inv_bonus_rel': 0.0,
        'invest_mode': False, 'Q_max': 1000.0, 'Q_min': 0.0,
        'Q_in_to_cap': 0.25, 'Q_out_to_cap': 0.25, 'Q_rel_loss': 0.001,
        'balanced': True, 'init_storage': 0.5,
    },
}

OPT_DEFAULTS = {
    'Solver': 'HiGHS',
    'MIPGap': 1e-6,
    'TimeLimit': 60,
    'calc_network': 'specific',
    'net_dist': 10.0,
    'net_inv_spez': 1500.0,
    'net_op_cost_fix': 50.0,
    'net_op_cost_var': 1.5,
    'net_inv_total': 1000000.0,
    'net_op_cost_fix_total': 70000.0,
    'net_op_cost_var_total': 30000.0,
    'ef_gas': 0.2012,
    'elec_consumer_charges_grid': 52.52,
    'elec_consumer_charges_self': 20.50,
    'heat_price': 76.74,
    'energy_tax': 5.50,
    'vNNE': 7.0,
    'capital_interest': 0.05,
    'lifetime': 20,
}

# Investment cost scaled to the 24 h horizon so that building capacity is a
# real trade-off (annuity costs of a full year against one day of operation
# would make every investment unattractive).
DAYS_PER_YEAR = 365


def _make_data(n=N_STEPS, start='2024-01-01', **overrides):
    """Create a synthetic hourly input time series.

    The default profile is designed so that a system containing every unit
    type dispatches all of them at some point: negative spot prices at night
    (electrode boiler), cheap power in the morning (heat pump), expensive
    power during the day (CHP units sell to the spot market) and solar heat
    around noon.
    """
    index = pd.date_range(start, periods=n, freq='h')
    hours = np.arange(n) % 24
    spot = np.select(
        [hours < 4, hours < 8, hours < 20], [-60.0, 10.0, 180.0], 40.0
    )
    data = pd.DataFrame(
        {
            'heat_demand': 80 + 30 * np.sin(2 * np.pi * (hours - 6) / 24),
            'el_spot_price': spot,
            'ef_om': 300 + 100 * np.cos(2 * np.pi * hours / 24),
            'gas_price': 25.0,
            'co2_price': 30.0,
            'solar_heat_flow': (
                np.clip(np.sin(np.pi * (hours - 6) / 12), 0, None) * 6e-4
            ),
        },
        index=index,
    )
    for col, val in overrides.items():
        data[col] = val
    return data


def _make_unit(cat, **overrides):
    params = copy.deepcopy(UNIT_DEFAULTS[cat])
    params.update(overrides)
    return params


def _make_opt(**overrides):
    params = copy.deepcopy(OPT_DEFAULTS)
    params.update(overrides)
    return params


def _scaled_invest(cat, **overrides):
    """Return unit parameters in invest mode with costs scaled to one day."""
    params = _make_unit(cat, invest_mode=True)
    params['inv_spez'] /= DAYS_PER_YEAR
    params['op_cost_fix'] /= DAYS_PER_YEAR
    params.update(overrides)
    return params


def _solve(data, param_units, param_opt, logdir):
    """Build and solve an energy system like the dashboard does.

    The solver log is written to ``<logdir>/solverlogs`` instead of the
    package directory. ``solve_model`` derives that path from the module's
    ``__file__``, so it is redirected for the duration of the solve. Every
    solve gets its own directory because HiGHS keeps its log file open while
    the solved model is alive, which would otherwise make the next solve fail
    on Windows (see ``test_consecutive_solves_with_shared_log_dir``).
    """
    es = model.EnergySystem(data, param_units, param_opt)
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(model, '__file__', os.path.join(str(logdir), 'model.py'))
        status = es.solve_model()
    return es, status


@pytest.fixture
def shipped_defaults():
    """Default parameters of the dashboard (``input/*.json``).

    Units are numbered like the dashboard does (``hp`` -> ``hp1``).
    Returns ``(param_units, param_opt)``.
    """
    input_dir = resources.files('owp_milp_optimization') / 'input'
    with (input_dir / 'param_units.json').open(encoding='utf-8') as f:
        param_units = {f'{cat}1': p for cat, p in json.load(f).items()}
    with (input_dir / 'param_opt.json').open(encoding='utf-8') as f:
        param_opt = json.load(f)
    return param_units, param_opt


@pytest.fixture(scope='session')
def make_data():
    """Factory for synthetic input time series, see ``_make_data``."""
    return _make_data


@pytest.fixture(scope='session')
def make_unit():
    """Factory for unit parameters: ``make_unit('hp', cap_N=10)``."""
    return _make_unit


@pytest.fixture(scope='session')
def make_opt():
    """Factory for optimization parameters: ``make_opt(heat_price=80)``."""
    return _make_opt


@pytest.fixture(scope='session')
def scaled_invest():
    """Factory for invest-mode unit parameters scaled to a 24 h horizon."""
    return _scaled_invest


@pytest.fixture(scope='session')
def solve_es(tmp_path_factory):
    """Return ``solve(data, param_units, param_opt) -> (es, status)``."""
    def solve(data, param_units, param_opt):
        logdir = tmp_path_factory.mktemp('solver')
        return _solve(data, param_units, param_opt, logdir)
    return solve


@pytest.fixture(scope='session')
def solve_and_process(solve_es):
    """Return a helper that solves and post-processes, asserting success."""
    def run(data, param_units, param_opt):
        es, status = solve_es(data, param_units, param_opt)
        assert status == 'ok', f'Reference scenario did not solve: {status}'
        es.run_postprocessing()
        return es
    return run


def _full_dispatch_units():
    """Every unit type in dispatch mode, including two numbered exhs units.

    With ``_make_data()`` every unit is dispatched at least once, which
    ``test_reference_scenario_dispatches_every_unit`` guards.
    """
    return {
        'hp1': _make_unit('hp', op_cost_bonus_rel=0.2),
        'ccet1': _make_unit('ccet'),
        'ice1': _make_unit('ice'),
        'gb1': _make_unit('gb', op_cost_bonus_rel=0.1),
        'eb1': _make_unit('eb'),
        'sol1': _make_unit('sol'),
        'exhs1': _make_unit('exhs', fix=True),
        'exhs2': _make_unit('exhs', cap_N=15.0, op_cost_var=30.0),
        'tes1': _make_unit('tes'),
    }


def _invest_units():
    """Units without CHP in invest mode (all cost terms consistent)."""
    return {
        'hp1': _scaled_invest('hp', cap_min=5.0, inv_bonus_rel=0.2),
        'gb1': _scaled_invest('gb'),
        'eb1': _scaled_invest('eb'),
        'sol1': _scaled_invest('sol'),
        'exhs1': _scaled_invest('exhs', op_cost_var=45.0),
        'tes1': _scaled_invest('tes'),
    }


@pytest.fixture
def full_dispatch_units():
    """Fresh copy of the unit parameters of the ``full_dispatch`` scenario."""
    return _full_dispatch_units()


@pytest.fixture
def invest_units():
    """Fresh copy of the unit parameters of the ``full_invest`` scenario."""
    return _invest_units()


@pytest.fixture(scope='session')
def full_dispatch(solve_and_process):
    """Solved and post-processed system with every unit type (dispatch)."""
    return solve_and_process(_make_data(), _full_dispatch_units(), _make_opt())


@pytest.fixture(scope='session')
def full_invest(solve_and_process):
    """Solved and post-processed system in invest mode (no CHP units)."""
    return solve_and_process(_make_data(), _invest_units(), _make_opt())


@pytest.fixture(scope='session')
def gas_boiler_only(solve_and_process):
    """Minimal solved system: one gas boiler and a flat heat demand."""
    return solve_and_process(
        _make_data(heat_demand=100.0),
        {'gb1': _make_unit('gb', Q_rel_min=0.0)},
        _make_opt(),
    )
