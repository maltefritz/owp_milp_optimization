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
    """Assert that the optimizer's objective equals the reported costs."""
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
    """Guard that the invest scenario actually builds the tested units."""
    caps = full_invest.data_caps.loc[0]
    for unit in ['hp1', 'gb1', 'eb1', 'sol1', 'tes1']:
        assert caps[f'cap_{unit}'] > 1, f'{unit} is not built'


# %% Output structure

def test_data_all_columns(full_dispatch):
    """``data_all`` has one labeled column per flow, plus storage and
    emission columns."""
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
    """On/off status variables and unlabeled columns are dropped."""
    for col in full_dispatch.data_all.columns:
        assert col is not None
        assert 'status' not in col and 'state' not in col
        assert 'none' not in col.lower()


def test_data_all_index_matches_input(full_dispatch, make_data):
    """The results use the time index of the input data."""
    data = make_data()
    pd.testing.assert_index_equal(
        flows(full_dispatch).index, data.index, check_names=False
    )


def test_data_all_with_storage_has_final_storage_level(full_dispatch):
    """With a storage, the extra last row only holds the final storage
    content; all flows are NaN there."""
    es = full_dispatch
    assert len(es.data_all) == es.periods + 1
    last = es.data_all.iloc[-1]
    assert np.isfinite(last['storage_content_tes1'])
    assert last.drop(['storage_content_tes1', 'Emissions OM']).isna().all()


def test_data_all_without_storage(gas_boiler_only):
    """Without a storage there is no extra row, and only the columns of the
    units that exist."""
    es = gas_boiler_only
    assert len(es.data_all) == es.periods
    assert set(es.data_all.columns) == {
        'H_gb1', 'H_source', 'Q_demand', 'Q_gb1', 'Emissions OM'
    }


def test_data_caps_in_dispatch_mode_are_nominal_capacities(full_dispatch):
    """In dispatch mode, ``data_caps`` reports the given capacities
    (``Q_N`` for storages, ``A_N`` for solar, ``cap_N`` otherwise)."""
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
    """In invest mode, ``data_caps`` also holds the optimized charging and
    discharging power of the storage."""
    expected = {f'cap_{u}' for u in full_invest.param_units}
    expected |= {'cap_in_tes1', 'cap_out_tes1'}
    assert set(full_invest.data_caps.columns) == expected


def test_cost_df_structure(full_dispatch):
    """``cost_df`` has one row per cost type and one column per unit."""
    cost_df = full_dispatch.cost_df
    assert list(cost_df.index) == [
        'invest', 'op_cost_fix', 'op_cost_var', 'op_cost'
    ]
    assert list(cost_df.columns) == list(full_dispatch.param_units)


@pytest.mark.parametrize('scenario', ['full_dispatch', 'full_invest',
                                      'gas_boiler_only'])
def test_key_params_are_complete_and_finite(scenario, request):
    """Every scenario reports all key parameters, none of them NaN or inf.

    ``request.getfixturevalue`` loads the scenario fixture by its name.
    """
    key_params = request.getfixturevalue(scenario).key_params
    assert set(key_params) == KEY_PARAMS
    assert all(np.isfinite(v) for v in key_params.values())


def test_pipeline_does_not_mutate_inputs(
        full_dispatch, full_dispatch_units, make_data, make_opt):
    """Solving and post-processing leave the inputs unchanged."""
    pd.testing.assert_frame_equal(full_dispatch.data, make_data())
    assert full_dispatch.param_units == full_dispatch_units
    assert full_dispatch.param_opt == make_opt()


# %% Physical consistency (dispatch)

def test_heat_balance(full_dispatch):
    """In every hour, heat supply minus storage charging equals demand."""
    d = flows(full_dispatch)
    supply = (
        d['Q_out_hp1'] + d['Q_ccet1'] + d['Q_ice1'] + d['Q_gb1'] + d['Q_eb1']
        + d['Q_sol1'] + d['Q_exhs1'] + d['Q_exhs2'] + d['Q_out_tes1']
    )
    np.testing.assert_allclose(
        supply - d['Q_in_tes1'], d['Q_demand'], atol=TOL
    )


def test_heat_demand_is_met_exactly(full_dispatch, make_data):
    """The delivered heat equals the input heat demand."""
    np.testing.assert_allclose(
        flows(full_dispatch)['Q_demand'], make_data()['heat_demand'],
        atol=TOL
    )


def test_gas_balance(full_dispatch):
    """Bought gas equals the gas used by all gas fired units."""
    d = flows(full_dispatch)
    np.testing.assert_allclose(
        d['H_source'], d['H_ccet1'] + d['H_ice1'] + d['H_gb1'], atol=TOL
    )


def test_electricity_balance(full_dispatch):
    """Grid and internal CHP electricity cover the electric heat units."""
    d = flows(full_dispatch)
    np.testing.assert_allclose(
        d['P_source'] + d['P_internal'], d['P_in_hp1'] + d['P_eb1'], atol=TOL
    )


def test_chp_electricity_balance(full_dispatch):
    """CHP electricity is either sold at the spot market or used
    internally."""
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
    """Output = efficiency * input for every converter in every hour."""
    d = flows(full_dispatch)
    factor = full_dispatch.param_units[unit][eff]
    np.testing.assert_allclose(d[output], factor * d[inp], atol=TOL)


@pytest.mark.parametrize('unit, col', [
    ('hp1', 'Q_out_hp1'), ('ccet1', 'Q_ccet1'), ('ice1', 'Q_ice1'),
    ('gb1', 'Q_gb1'), ('eb1', 'Q_eb1'),
])
def test_part_load_limits(full_dispatch, unit, col):
    """A unit is either off or runs between its minimum and maximum load."""
    params = full_dispatch.param_units[unit]
    q = flows(full_dispatch)[col]
    on = q > TOL
    assert (q[on] >= params['Q_rel_min'] * params['cap_N'] - TOL).all()
    assert (q <= params['Q_rel_max'] * params['cap_N'] + TOL).all()
    assert (q >= -TOL).all()


def test_solar_thermal_follows_irradiation(full_dispatch, make_data):
    """Solar heat = irradiation * collector efficiency * area."""
    params = full_dispatch.param_units['sol1']
    np.testing.assert_allclose(
        flows(full_dispatch)['Q_sol1'],
        make_data()['solar_heat_flow'] * params['eta_col'] * params['A_N'],
        atol=TOL
    )


def test_fixed_external_heat_source_runs_at_nominal_capacity(full_dispatch):
    """An external heat source with ``fix=True`` delivers its full capacity
    in every hour."""
    cap = full_dispatch.param_units['exhs1']['cap_N']
    np.testing.assert_allclose(flows(full_dispatch)['Q_exhs1'], cap, atol=TOL)


def test_flexible_external_heat_source_is_bounded(full_dispatch):
    """A non-fixed external heat source stays between 0 and its capacity."""
    cap = full_dispatch.param_units['exhs2']['cap_N']
    q = flows(full_dispatch)['Q_exhs2']
    assert (q <= cap + TOL).all() and (q >= -TOL).all()


def test_storage_content_within_capacity(full_dispatch):
    """The storage is never below empty or above full."""
    content = full_dispatch.data_all['storage_content_tes1']
    cap = full_dispatch.param_units['tes1']['Q_N']
    assert (content >= -TOL).all() and (content <= cap + TOL).all()


def test_storage_initial_level_and_balance(full_dispatch):
    """The storage starts at ``init_storage * Q_N`` and, being balanced,
    ends at the same level."""
    params = full_dispatch.param_units['tes1']
    content = full_dispatch.data_all['storage_content_tes1']
    assert content.iloc[0] == pytest.approx(
        params['init_storage'] * params['Q_N']
    )
    assert params['balanced']
    assert content.iloc[-1] == pytest.approx(content.iloc[0])


def test_storage_dynamics(full_dispatch):
    """content(t+1) = content(t) * (1 - loss rate) + charging - discharging.

    The reported losses must be ``content(t) * loss rate``.
    """
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


def test_storage_power_limited_in_dispatch_mode(
        solve_and_process, make_data, make_unit, make_opt):
    """Storage power stays within ``Q_in_to_cap``/``Q_out_to_cap`` times the
    capacity, also when the capacity is fixed.

    Regression test: up to v0.0.6 the ratios were only passed as solph's
    ``invest_relation_*_capacity``, which only applies in invest mode, so a
    storage with a fixed capacity could be charged with unlimited power.
    """
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
    """The more efficient boiler runs at full load, the other one covers
    the rest (merit order)."""
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
    """Optimized capacities stay within the min/max limits of each unit."""
    caps = full_invest.data_caps.loc[0]
    for unit, params in full_invest.param_units.items():
        lo, hi = INVEST_BOUNDS.get(
            unit.rstrip('0123456789'), ('cap_min', 'cap_max')
        )
        assert params[lo] - TOL <= caps[f'cap_{unit}'] <= params[hi] + TOL


def test_invest_minimum_capacity_is_enforced(full_invest):
    """``cap_min`` is respected (5 MW for hp1 in the invest scenario)."""
    assert full_invest.data_caps.loc[0, 'cap_hp1'] >= 5.0 - TOL


@pytest.mark.parametrize('unit, col', [
    ('hp1', 'Q_out_hp1'), ('gb1', 'Q_gb1'), ('eb1', 'Q_eb1'),
    ('exhs1', 'Q_exhs1'),
])
def test_invest_flows_within_optimized_capacity(full_invest, unit, col):
    """Units never produce more than their optimized capacity allows."""
    cap = full_invest.data_caps.loc[0, f'cap_{unit}']
    q_rel_max = full_invest.param_units[unit].get('Q_rel_max', 1.0)
    assert (flows(full_invest)[col] <= q_rel_max * cap + TOL).all()


def test_invest_solar_scales_with_optimized_area(full_invest, make_data):
    """Solar heat uses the optimized collector area."""
    area = full_invest.data_caps.loc[0, 'cap_sol1']
    eta = full_invest.param_units['sol1']['eta_col']
    np.testing.assert_allclose(
        flows(full_invest)['Q_sol1'],
        make_data()['solar_heat_flow'] * eta * area, atol=1e-5
    )


def test_invest_storage_power_follows_capacity(full_invest):
    """Storage power is the given ratio times the optimized capacity, and
    flows and content respect these limits."""
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
    """The reported invest uses the optimized capacity, not ``cap_N``."""
    cap = full_invest.data_caps.loc[0, 'cap_hp1']
    params = full_invest.param_units['hp1']
    assert full_invest.cost_df.loc['invest', 'hp1'] == pytest.approx(
        params['inv_spez'] * cap * (1 - params['inv_bonus_rel'])
    )


# %% Economic key parameters (recomputed independently)

@pytest.fixture(scope='module')
def econ(full_dispatch):
    """The full dispatch scenario and its key parameters, recomputed by hand
    from the result flows and the inputs. Returns ``(es, expected)``."""
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
    """Each key parameter matches its independent recomputation."""
    es, expected = econ
    assert es.key_params[key] == pytest.approx(expected[key])


def test_key_param_aggregates(full_dispatch):
    """Totals (costs, revenues, balance) are the sums of their parts."""
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
    """Both LCOH values match ``LCOH()``; including the heat network makes
    heat more expensive."""
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
    """Each unit's ``cost_df`` column matches a manual calculation.

    Gas boilers additionally pay the energy tax per MWh of gas.
    """
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
    """With ``calc_network='total'``, the given network cost totals are used
    instead of length times specific cost."""
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
    """A gas-only system reports 0 (not NaN) for everything electric."""
    kp = gas_boiler_only.key_params
    for key in ['cost_el_grid', 'cost_el_internal', 'cost_el',
                'revenues_spotmarket', 'Emissions OM (Electricity)',
                'Emissions OM (Spotmarket)']:
        assert kp[key] == 0, key
    assert kp['cost_gas'] > 0


def test_electric_only_system_has_no_gas_cost(
        solve_and_process, make_data, make_unit, make_opt):
    """An electricity-only system reports 0 for gas cost and emissions."""
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
    """Hourly emissions come from gas and net grid electricity.

    Electricity sold at the spot market counts as a credit, because it
    replaces grid electricity elsewhere.
    """
    es = full_dispatch
    d = flows(es)
    expected = (
        d['H_source'] * es.param_opt['ef_gas']
        + (d['P_source'] - d['P_spotmarket']) * es.data['ef_om']
    )
    np.testing.assert_allclose(d['Emissions OM'], expected, atol=1e-6)


def test_emission_key_params(full_dispatch):
    """The emission key parameters per source add up to the total; the
    spot market part is negative (credit)."""
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


# %% Consistency of post-processing and optimization

@pytest.mark.parametrize('scenario', ['full_dispatch', 'full_invest',
                                      'gas_boiler_only'])
def test_objective_matches_postprocessed_costs(scenario, request):
    """The costs shown to the user add up to what the optimizer minimized.

    If not, the optimizer decided on different costs than the ones reported
    (see ``expected_objective``).
    """
    assert_objective_consistent(request.getfixturevalue(scenario))


@pytest.mark.xfail(
    strict=True, raises=AssertionError,
    reason=(
        'BUG: the optimization charges op_cost_var of a storage on both the '
        'charging and the discharging flow, the post-processing only on the '
        'charging flow (Q_in).'
    )
)
def test_objective_matches_costs_with_storage_variable_cost(
        solve_and_process, make_data, make_opt, full_dispatch_units):
    """Objective and reported costs agree for a storage with variable
    cost."""
    full_dispatch_units['tes1']['op_cost_var'] = 0.5
    es = solve_and_process(make_data(), full_dispatch_units, make_opt())
    require(flows(es)['Q_out_tes1'].sum() > 1, 'storage is discharged')
    assert_objective_consistent(es)


@pytest.mark.xfail(
    strict=True, raises=AssertionError,
    reason=(
        'BUG: for CHP units in invest mode, the optimization applies '
        'inv_spez and op_cost_fix to the thermal capacity, while the '
        'post-processing applies them to the electrical capacity '
        '(cap / eta_th * eta_el).'
    )
)
def test_objective_matches_costs_with_chp_investment(
        solve_and_process, make_data, make_unit, make_opt, scaled_invest):
    """Objective and reported costs agree for a CHP unit in invest mode."""
    es = solve_and_process(make_data(), {
        'ccet1': scaled_invest('ccet', Q_rel_min=0.0),
        'gb1': make_unit('gb', Q_rel_min=0.0),
    }, make_opt())
    require(es.data_caps.loc[0, 'cap_ccet1'] > 1, 'CHP capacity is built')
    assert_objective_consistent(es)


@pytest.mark.xfail(
    strict=True, raises=AssertionError,
    reason=(
        'BUG: in invest mode, the ep_costs passed to solph contain '
        'op_cost_fix without the operating cost bonus (op_cost_bonus_rel), '
        'while the post-processing reduces the fixed operating cost by it '
        '(as the dashboard tooltip describes).'
    )
)
def test_objective_matches_costs_with_operating_cost_bonus_in_invest_mode(
        solve_and_process, make_data, make_opt, scaled_invest):
    """Objective and reported costs agree with an operating cost bonus in
    invest mode."""
    es = solve_and_process(
        make_data(),
        {'gb1': scaled_invest('gb', Q_rel_min=0.0, op_cost_bonus_rel=0.5)},
        make_opt()
    )
    require(es.data_caps.loc[0, 'cap_gb1'] > 1, 'gas boiler is built')
    assert_objective_consistent(es)


# %% Input edge cases

def test_two_units_of_same_type_are_reported_separately(full_dispatch):
    """exhs1 and exhs2 get their own capacities and cost columns."""
    caps = full_dispatch.data_caps.loc[0]
    assert caps['cap_exhs1'] == 5.0
    assert caps['cap_exhs2'] == 15.0
    assert {'exhs1', 'exhs2'} <= set(full_dispatch.cost_df.columns)


@pytest.mark.xfail(
    strict=True, raises=KeyError,
    reason=(
        'BUG: get_results drops every data_caps column containing "0", so '
        'cap_gb10 (and cap_hp20, ...) is lost and calc_econ_params raises '
        'KeyError. The dashboard allows up to 99 units per type.'
    )
)
def test_ten_or_more_units_of_same_type(
        solve_es, make_data, make_unit, make_opt):
    """Units numbered 10 or higher are reported like any other unit."""
    units = {
        f'gb{i}': make_unit('gb', cap_N=20.0, Q_rel_min=0.0)
        for i in range(1, 11)
    }
    es, status = solve_es(make_data(heat_demand=100.0), units, make_opt())
    require(status == 'ok', 'system with ten boilers solves')

    es.run_postprocessing()
    assert 'cap_gb10' in es.data_caps.columns
    assert 'gb10' in es.cost_df.columns


@pytest.mark.xfail(
    strict=True, raises=AssertionError,
    reason=(
        'BUG: the input index is not validated. A non-datetime index makes '
        'the model time index start at 1970-01-01; costs and emissions are '
        'then computed from misaligned series (all NaN) and silently become '
        '0. The input should either be rejected or handled correctly.'
    )
)
def test_non_datetime_index_is_rejected_or_handled(
        solve_es, make_data, make_unit, make_opt):
    """Input without a datetime index is either rejected or gives correct
    costs, but never silently wrong ones."""
    data = make_data(heat_demand=100.0).reset_index(drop=True)
    opt = make_opt()
    try:
        es, status = solve_es(
            data, {'gb1': make_unit('gb', Q_rel_min=0.0)}, opt
        )
        es.run_postprocessing()
    except (ValueError, TypeError):
        return  # rejecting the input is fine

    gas = es.data_all['H_source'].to_numpy()[:len(data)]
    price = (data['gas_price'] + data['co2_price'] * opt['ef_gas']).to_numpy()
    assert es.key_params['cost_gas'] == pytest.approx((gas * price).sum())
