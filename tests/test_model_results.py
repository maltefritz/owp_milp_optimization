"""End-to-end tests of the optimization results and their post-processing.

Most tests read from the session-scoped reference scenarios defined in
``conftest.py`` and check

- the structure of the public outputs (``data_all``, ``data_caps``,
  ``cost_df``, ``key_params``),
- physical consistency (energy balances, conversion efficiencies, part load
  limits, storage dynamics),
- the economic and ecological key parameters, recomputed independently, and
- that the post-processed costs agree with the optimizer's objective value.
"""
import copy

import numpy as np
import pandas as pd
import pytest
from pyomo.environ import value

from owp_milp_optimization.model import LCOH

TOL = 1e-6

KEY_PARAMS = {
    'op_cost_total', 'invest_total', 'cost_gas', 'cost_el_grid',
    'cost_el_internal', 'cost_el', 'cost_total', 'invest_net_total',
    'cost_net_fix_total', 'cost_net_var_total', 'revenues_spotmarket',
    'revenues_heat', 'revenues_total', 'balance_total', 'LCOH',
    'LCOH_incl_net', 'total_heat_demand', 'Emissions OM (Gas)',
    'Emissions OM (Electricity)', 'Emissions OM (Spotmarket)',
    'Total Emissions OM',
}


def require(condition, message):
    """Check a scenario precondition.

    Raises ``pytest.fail`` instead of ``AssertionError`` so that a broken
    precondition is reported as a failure even in tests marked as ``xfail``.
    """
    if not condition:
        pytest.fail(f'Scenario precondition not met: {message}')


def flows(es):
    """Time series results restricted to the optimization periods.

    With a storage, ``data_all`` has one additional row holding the storage
    content at the end of the last time step.
    """
    return es.data_all.iloc[:es.periods]


def expected_objective(es):
    """Objective value implied by the post-processed results.

    The optimizer minimizes variable costs minus revenues plus, for units in
    invest mode, the annualized specific invest and the fixed operating
    cost. The post-processing reports the full invest and the fixed operating
    cost of every unit, so these are converted accordingly.
    """
    kp = es.key_params
    invest = [u for u, p in es.param_units.items() if p['invest_mode']]
    dispatch = [u for u in es.param_units if u not in invest]
    return (
        kp['cost_total'] - kp['revenues_total']
        - es.cost_df.loc['op_cost_fix', dispatch].sum()
        + es.cost_df.loc['invest', invest].sum() / es.bwsf
    )


def assert_objective_consistent(es):
    assert value(es.model.objective) == pytest.approx(
        expected_objective(es), rel=1e-6, abs=1e-2
    )


# %% Reference scenario guard

def test_reference_scenario_dispatches_every_unit(full_dispatch):
    """Guard that the physics and cost tests below are not trivially true."""
    totals = flows(full_dispatch).sum()
    for col in ['Q_out_hp1', 'Q_ccet1', 'Q_ice1', 'Q_gb1', 'Q_eb1', 'Q_sol1',
                'Q_exhs1', 'Q_exhs2', 'Q_in_tes1', 'Q_out_tes1', 'P_source',
                'P_internal', 'P_spotmarket']:
        assert totals[col] > 1, f'{col} is not used in the reference scenario'


def test_reference_invest_scenario_builds_capacity(full_invest):
    caps = full_invest.data_caps.loc[0]
    for unit in ['hp1', 'gb1', 'eb1', 'sol1', 'tes1']:
        assert caps[f'cap_{unit}'] > 1, f'{unit} is not built'


# %% Output structure

def test_data_all_columns(full_dispatch):
    assert set(full_dispatch.data_all.columns) == {
        'H_ccet1', 'H_gb1', 'H_ice1', 'H_source',
        'P_ccet1', 'P_eb1', 'P_ice1', 'P_in_hp1', 'P_internal', 'P_source',
        'P_spotmarket',
        'Q_ccet1', 'Q_demand', 'Q_eb1', 'Q_exhs1', 'Q_exhs2', 'Q_gb1',
        'Q_ice1', 'Q_in_tes1', 'Q_out_hp1', 'Q_out_tes1', 'Q_sol1',
        'storage_content_tes1', 'storage_losses_tes1',
        'Emissions OM',
    }


def test_data_all_contains_no_status_or_unlabeled_columns(full_dispatch):
    for col in full_dispatch.data_all.columns:
        assert col is not None
        assert 'status' not in col and 'state' not in col
        assert 'none' not in col.lower()


def test_data_all_index_matches_input(full_dispatch, make_data):
    data = make_data()
    pd.testing.assert_index_equal(
        flows(full_dispatch).index, data.index, check_names=False
    )


def test_data_all_with_storage_has_final_storage_level(full_dispatch):
    es = full_dispatch
    assert len(es.data_all) == es.periods + 1
    last = es.data_all.iloc[-1]
    assert np.isfinite(last['storage_content_tes1'])
    assert last.drop(['storage_content_tes1', 'Emissions OM']).isna().all()


def test_data_all_without_storage(gas_boiler_only):
    es = gas_boiler_only
    assert len(es.data_all) == es.periods
    assert set(es.data_all.columns) == {
        'H_gb1', 'H_source', 'Q_demand', 'Q_gb1', 'Emissions OM'
    }


def test_data_caps_in_dispatch_mode_are_nominal_capacities(full_dispatch):
    caps = full_dispatch.data_caps
    assert list(caps.index) == [0]
    expected = {}
    for unit, params in full_dispatch.param_units.items():
        key = {'tes': 'Q_N', 'sol': 'A_N'}.get(
            unit.rstrip('0123456789'), 'cap_N'
        )
        expected[f'cap_{unit}'] = params[key]
    assert caps.loc[0].to_dict() == pytest.approx(expected)


def test_data_caps_in_invest_mode_include_storage_flow_capacities(
        full_invest):
    expected = {f'cap_{u}' for u in full_invest.param_units}
    expected |= {'cap_in_tes1', 'cap_out_tes1'}
    assert set(full_invest.data_caps.columns) == expected


def test_cost_df_structure(full_dispatch):
    cost_df = full_dispatch.cost_df
    assert list(cost_df.index) == [
        'invest', 'op_cost_fix', 'op_cost_var', 'op_cost'
    ]
    assert list(cost_df.columns) == list(full_dispatch.param_units)


@pytest.mark.parametrize('scenario', ['full_dispatch', 'full_invest',
                                      'gas_boiler_only'])
def test_key_params_are_complete_and_finite(scenario, request):
    key_params = request.getfixturevalue(scenario).key_params
    assert set(key_params) == KEY_PARAMS
    assert all(np.isfinite(v) for v in key_params.values())


def test_pipeline_does_not_mutate_inputs(
        full_dispatch, full_dispatch_units, make_data, make_opt):
    pd.testing.assert_frame_equal(full_dispatch.data, make_data())
    assert full_dispatch.param_units == full_dispatch_units
    assert full_dispatch.param_opt == make_opt()
