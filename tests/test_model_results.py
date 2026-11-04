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


# %% Physical consistency (dispatch)

def test_heat_balance(full_dispatch):
    d = flows(full_dispatch)
    supply = (
        d['Q_out_hp1'] + d['Q_ccet1'] + d['Q_ice1'] + d['Q_gb1'] + d['Q_eb1']
        + d['Q_sol1'] + d['Q_exhs1'] + d['Q_exhs2'] + d['Q_out_tes1']
    )
    np.testing.assert_allclose(
        supply - d['Q_in_tes1'], d['Q_demand'], atol=TOL
    )


def test_heat_demand_is_met_exactly(full_dispatch, make_data):
    np.testing.assert_allclose(
        flows(full_dispatch)['Q_demand'], make_data()['heat_demand'],
        atol=TOL
    )


def test_gas_balance(full_dispatch):
    d = flows(full_dispatch)
    np.testing.assert_allclose(
        d['H_source'], d['H_ccet1'] + d['H_ice1'] + d['H_gb1'], atol=TOL
    )


def test_electricity_balance(full_dispatch):
    d = flows(full_dispatch)
    np.testing.assert_allclose(
        d['P_source'] + d['P_internal'], d['P_in_hp1'] + d['P_eb1'], atol=TOL
    )


def test_chp_electricity_balance(full_dispatch):
    d = flows(full_dispatch)
    np.testing.assert_allclose(
        d['P_ccet1'] + d['P_ice1'], d['P_spotmarket'] + d['P_internal'],
        atol=TOL
    )


@pytest.mark.parametrize('output, inp, unit, eff', [
    ('Q_gb1', 'H_gb1', 'gb1', 'eta'),
    ('Q_eb1', 'P_eb1', 'eb1', 'eta'),
    ('Q_out_hp1', 'P_in_hp1', 'hp1', 'cop'),
    ('Q_ccet1', 'H_ccet1', 'ccet1', 'eta_th'),
    ('P_ccet1', 'H_ccet1', 'ccet1', 'eta_el'),
    ('Q_ice1', 'H_ice1', 'ice1', 'eta_th'),
    ('P_ice1', 'H_ice1', 'ice1', 'eta_el'),
])
def test_conversion_efficiencies(full_dispatch, output, inp, unit, eff):
    d = flows(full_dispatch)
    factor = full_dispatch.param_units[unit][eff]
    np.testing.assert_allclose(d[output], factor * d[inp], atol=TOL)


@pytest.mark.parametrize('unit, col', [
    ('hp1', 'Q_out_hp1'), ('ccet1', 'Q_ccet1'), ('ice1', 'Q_ice1'),
    ('gb1', 'Q_gb1'), ('eb1', 'Q_eb1'),
])
def test_part_load_limits(full_dispatch, unit, col):
    params = full_dispatch.param_units[unit]
    q = flows(full_dispatch)[col]
    on = q > TOL
    assert (q[on] >= params['Q_rel_min'] * params['cap_N'] - TOL).all()
    assert (q <= params['Q_rel_max'] * params['cap_N'] + TOL).all()
    assert (q >= -TOL).all()


def test_solar_thermal_follows_irradiation(full_dispatch, make_data):
    params = full_dispatch.param_units['sol1']
    np.testing.assert_allclose(
        flows(full_dispatch)['Q_sol1'],
        make_data()['solar_heat_flow'] * params['eta_col'] * params['A_N'],
        atol=TOL
    )


def test_fixed_external_heat_source_runs_at_nominal_capacity(full_dispatch):
    cap = full_dispatch.param_units['exhs1']['cap_N']
    np.testing.assert_allclose(flows(full_dispatch)['Q_exhs1'], cap, atol=TOL)


def test_flexible_external_heat_source_is_bounded(full_dispatch):
    cap = full_dispatch.param_units['exhs2']['cap_N']
    q = flows(full_dispatch)['Q_exhs2']
    assert (q <= cap + TOL).all() and (q >= -TOL).all()


def test_storage_content_within_capacity(full_dispatch):
    content = full_dispatch.data_all['storage_content_tes1']
    cap = full_dispatch.param_units['tes1']['Q_N']
    assert (content >= -TOL).all() and (content <= cap + TOL).all()


def test_storage_initial_level_and_balance(full_dispatch):
    params = full_dispatch.param_units['tes1']
    content = full_dispatch.data_all['storage_content_tes1']
    assert content.iloc[0] == pytest.approx(
        params['init_storage'] * params['Q_N']
    )
    assert params['balanced']
    assert content.iloc[-1] == pytest.approx(content.iloc[0])


def test_storage_dynamics(full_dispatch):
    d = full_dispatch.data_all
    loss_rate = full_dispatch.param_units['tes1']['Q_rel_loss']
    content = d['storage_content_tes1'].to_numpy()
    q_in = d['Q_in_tes1'].to_numpy()[:-1]
    q_out = d['Q_out_tes1'].to_numpy()[:-1]
    np.testing.assert_allclose(
        content[1:], content[:-1] * (1 - loss_rate) + q_in - q_out, atol=1e-5
    )
    np.testing.assert_allclose(
        d['storage_losses_tes1'].to_numpy()[:-1], content[:-1] * loss_rate,
        atol=1e-5
    )


@pytest.mark.xfail(
    strict=True, raises=AssertionError,
    reason=(
        'BUG: Q_in_to_cap and Q_out_to_cap are passed to solph as '
        'invest_relation_*_capacity, which solph only applies in invest '
        'mode. In dispatch mode the storage can be charged and discharged '
        'with unlimited power, although the dashboard shows and uses both '
        'ratios for storages with a fixed capacity.'
    )
)
def test_storage_power_limited_in_dispatch_mode(
        solve_and_process, make_data, make_unit, make_opt):
    # One hour of very cheap electricity makes fast charging attractive
    data = make_data(el_spot_price=300.0)
    data.iloc[2, data.columns.get_loc('el_spot_price')] = -500.0
    tes = make_unit('tes', Q_N=1000.0)
    es = solve_and_process(data, {
        'eb1': make_unit('eb', cap_N=2000.0),
        'gb1': make_unit('gb', Q_rel_min=0.0),
        'tes1': tes,
    }, make_opt())

    d = flows(es)
    assert d['Q_in_tes1'].max() <= tes['Q_in_to_cap'] * tes['Q_N'] + TOL
    assert d['Q_out_tes1'].max() <= tes['Q_out_to_cap'] * tes['Q_N'] + TOL


def test_cheaper_unit_is_dispatched_first(
        solve_and_process, make_data, make_unit, make_opt):
    es = solve_and_process(make_data(heat_demand=100.0), {
        'gb1': make_unit('gb', cap_N=60.0, Q_rel_min=0.0, eta=0.95),
        'gb2': make_unit('gb', cap_N=100.0, Q_rel_min=0.0, eta=0.80),
    }, make_opt())
    d = flows(es)
    np.testing.assert_allclose(d['Q_gb1'], 60.0, atol=TOL)
    np.testing.assert_allclose(d['Q_gb2'], 40.0, atol=TOL)


# %% Investment results

INVEST_BOUNDS = {'tes': ('Q_min', 'Q_max'), 'sol': ('A_min', 'A_max')}


def test_invest_capacities_within_bounds(full_invest):
    caps = full_invest.data_caps.loc[0]
    for unit, params in full_invest.param_units.items():
        lo, hi = INVEST_BOUNDS.get(
            unit.rstrip('0123456789'), ('cap_min', 'cap_max')
        )
        assert params[lo] - TOL <= caps[f'cap_{unit}'] <= params[hi] + TOL


def test_invest_minimum_capacity_is_enforced(full_invest):
    assert full_invest.data_caps.loc[0, 'cap_hp1'] >= 5.0 - TOL


@pytest.mark.parametrize('unit, col', [
    ('hp1', 'Q_out_hp1'), ('gb1', 'Q_gb1'), ('eb1', 'Q_eb1'),
    ('exhs1', 'Q_exhs1'),
])
def test_invest_flows_within_optimized_capacity(full_invest, unit, col):
    cap = full_invest.data_caps.loc[0, f'cap_{unit}']
    q_rel_max = full_invest.param_units[unit].get('Q_rel_max', 1.0)
    assert (flows(full_invest)[col] <= q_rel_max * cap + TOL).all()


def test_invest_solar_scales_with_optimized_area(full_invest, make_data):
    area = full_invest.data_caps.loc[0, 'cap_sol1']
    eta = full_invest.param_units['sol1']['eta_col']
    np.testing.assert_allclose(
        flows(full_invest)['Q_sol1'],
        make_data()['solar_heat_flow'] * eta * area, atol=1e-5
    )


def test_invest_storage_power_follows_capacity(full_invest):
    caps = full_invest.data_caps.loc[0]
    params = full_invest.param_units['tes1']
    assert caps['cap_in_tes1'] == pytest.approx(
        params['Q_in_to_cap'] * caps['cap_tes1']
    )
    assert caps['cap_out_tes1'] == pytest.approx(
        params['Q_out_to_cap'] * caps['cap_tes1']
    )
    d = flows(full_invest)
    assert (d['Q_in_tes1'] <= caps['cap_in_tes1'] + TOL).all()
    assert (d['Q_out_tes1'] <= caps['cap_out_tes1'] + TOL).all()
    assert (
        full_invest.data_all['storage_content_tes1'] <= caps['cap_tes1'] + TOL
    ).all()


def test_invest_cost_uses_optimized_capacity(full_invest):
    cap = full_invest.data_caps.loc[0, 'cap_hp1']
    params = full_invest.param_units['hp1']
    assert full_invest.cost_df.loc['invest', 'hp1'] == pytest.approx(
        params['inv_spez'] * cap * (1 - params['inv_bonus_rel'])
    )


# %% Economic key parameters (recomputed independently)

@pytest.fixture(scope='module')
def econ(full_dispatch):
    es = full_dispatch
    d = flows(es)
    data, opt = es.data, es.param_opt
    expected = {
        'cost_gas': (
            d['H_source'] * (data['gas_price']
                             + data['co2_price'] * opt['ef_gas'])
        ).sum(),
        'cost_el_grid': (
            d['P_source'] * (data['el_spot_price']
                             + opt['elec_consumer_charges_grid'])
        ).sum(),
        'cost_el_internal': (
            d['P_internal'] * opt['elec_consumer_charges_self']
        ).sum(),
        'revenues_spotmarket': (
            d['P_spotmarket'] * (data['el_spot_price'] + opt['vNNE'])
        ).sum(),
        'revenues_heat': d['Q_demand'].sum() * opt['heat_price'],
        'total_heat_demand': data['heat_demand'].sum(),
        'invest_net_total': opt['net_inv_spez'] * opt['net_dist'] * 1000,
        'cost_net_fix_total': (
            opt['net_op_cost_fix'] * opt['net_dist'] * 1000
        ),
        'cost_net_var_total': opt['net_op_cost_var'] * d['Q_demand'].sum(),
    }
    return es, expected


@pytest.mark.parametrize('key', [
    'cost_gas', 'cost_el_grid', 'cost_el_internal', 'revenues_spotmarket',
    'revenues_heat', 'total_heat_demand', 'invest_net_total',
    'cost_net_fix_total', 'cost_net_var_total',
])
def test_key_param_values(econ, key):
    es, expected = econ
    assert es.key_params[key] == pytest.approx(expected[key])


def test_key_param_aggregates(full_dispatch):
    kp = full_dispatch.key_params
    cost_df = full_dispatch.cost_df
    assert kp['op_cost_total'] == pytest.approx(cost_df.loc['op_cost'].sum())
    assert kp['invest_total'] == pytest.approx(cost_df.loc['invest'].sum())
    assert kp['cost_el'] == pytest.approx(
        kp['cost_el_grid'] + kp['cost_el_internal']
    )
    assert kp['cost_total'] == pytest.approx(
        kp['op_cost_total'] + kp['cost_gas'] + kp['cost_el']
    )
    assert kp['revenues_total'] == pytest.approx(
        kp['revenues_spotmarket'] + kp['revenues_heat']
    )
    assert kp['balance_total'] == pytest.approx(
        kp['revenues_total'] - kp['cost_total']
    )


def test_lcoh_values(full_dispatch):
    kp, opt = full_dispatch.key_params, full_dispatch.param_opt
    i, n = opt['capital_interest'], opt['lifetime']
    Q = kp['total_heat_demand']
    revenue = kp['revenues_spotmarket']
    assert kp['LCOH'] == pytest.approx(
        LCOH(kp['invest_total'], kp['cost_total'], Q, revenue, i, n)
    )
    assert kp['LCOH_incl_net'] == pytest.approx(LCOH(
        kp['invest_total'] + kp['invest_net_total'],
        kp['cost_total'] + kp['cost_net_fix_total']
        + kp['cost_net_var_total'],
        Q, revenue, i, n
    ))
    assert kp['LCOH_incl_net'] > kp['LCOH']


def unit_cost_basis(es, unit):
    """(capacity, energy series) that the specific unit costs refer to."""
    cat = unit.rstrip('0123456789')
    params = es.param_units[unit]
    cap = es.data_caps.loc[0, f'cap_{unit}']
    d = flows(es)
    if cat == 'hp':
        return cap, d[f'Q_out_{unit}']
    if cat == 'tes':
        return cap, d[f'Q_in_{unit}']
    if cat in ('ccet', 'ice'):
        # specific CHP costs refer to the electrical capacity and output
        return cap / params['eta_th'] * params['eta_el'], d[f'P_{unit}']
    return cap, d[f'Q_{unit}']


@pytest.mark.parametrize('unit', [
    'hp1', 'ccet1', 'ice1', 'gb1', 'eb1', 'sol1', 'exhs1', 'exhs2', 'tes1'
])
def test_unit_costs(full_dispatch, unit):
    es = full_dispatch
    params = es.param_units[unit]
    cap, energy = unit_cost_basis(es, unit)
    bonus = 1 - params['op_cost_bonus_rel']
    var = params['op_cost_var'] * energy.sum() * bonus
    if unit.startswith('gb'):
        var += es.param_opt['energy_tax'] / params['eta'] * energy.sum()

    costs = es.cost_df[unit]
    assert costs['invest'] == pytest.approx(
        params['inv_spez'] * cap * (1 - params['inv_bonus_rel'])
    )
    assert costs['op_cost_fix'] == pytest.approx(
        params['op_cost_fix'] * cap * bonus
    )
    assert costs['op_cost_var'] == pytest.approx(var)
    assert costs['op_cost'] == pytest.approx(
        costs['op_cost_fix'] + costs['op_cost_var']
    )


def test_network_cost_total_mode(
        solve_and_process, make_data, make_unit, make_opt):
    opt = make_opt(calc_network='total')
    es = solve_and_process(
        make_data(heat_demand=100.0), {'gb1': make_unit('gb', Q_rel_min=0.0)},
        opt
    )
    kp = es.key_params
    assert kp['invest_net_total'] == opt['net_inv_total']
    assert kp['cost_net_fix_total'] == opt['net_op_cost_fix_total']
    assert kp['cost_net_var_total'] == opt['net_op_cost_var_total']


def test_absent_commodities_have_zero_cost_and_emissions(gas_boiler_only):
    kp = gas_boiler_only.key_params
    for key in ['cost_el_grid', 'cost_el_internal', 'cost_el',
                'revenues_spotmarket', 'Emissions OM (Electricity)',
                'Emissions OM (Spotmarket)']:
        assert kp[key] == 0, key
    assert kp['cost_gas'] > 0


def test_electric_only_system_has_no_gas_cost(
        solve_and_process, make_data, make_unit, make_opt):
    es = solve_and_process(
        make_data(heat_demand=100.0), {'eb1': make_unit('eb', cap_N=150.0)},
        make_opt()
    )
    kp = es.key_params
    assert kp['cost_gas'] == 0
    assert kp['Emissions OM (Gas)'] == 0
    assert kp['cost_el_grid'] > 0


# %% Ecological key parameters

def test_emissions_time_series(full_dispatch):
    es = full_dispatch
    d = flows(es)
    expected = (
        d['H_source'] * es.param_opt['ef_gas']
        + (d['P_source'] - d['P_spotmarket']) * es.data['ef_om']
    )
    np.testing.assert_allclose(d['Emissions OM'], expected, atol=1e-6)


def test_emission_key_params(full_dispatch):
    es = full_dispatch
    d, kp = flows(es), es.key_params
    assert kp['Emissions OM (Gas)'] == pytest.approx(
        (d['H_source'] * es.param_opt['ef_gas']).sum()
    )
    assert kp['Emissions OM (Electricity)'] == pytest.approx(
        (d['P_source'] * es.data['ef_om']).sum()
    )
    assert kp['Emissions OM (Spotmarket)'] == pytest.approx(
        -(d['P_spotmarket'] * es.data['ef_om']).sum()
    )
    assert kp['Total Emissions OM'] == pytest.approx(
        kp['Emissions OM (Gas)'] + kp['Emissions OM (Electricity)']
        + kp['Emissions OM (Spotmarket)']
    )
