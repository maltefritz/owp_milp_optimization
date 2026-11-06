"""Tests for building the oemof.solph energy system (no solver involved).

These tests check that ``EnergySystem`` translates the parameter dicts into
the intended oemof.solph nodes, flows and parameters.
"""
import copy

import numpy as np
import oemof.solph as solph
import pandas as pd
import pytest

from owp_milp_optimization.model import EnergySystem, calc_bwsf

ALL_CATS = ['hp', 'ccet', 'ice', 'gb', 'eb', 'sol', 'exhs', 'tes']


def seq(values, n):
    """Materialize an oemof sequence (or scalar sequence) of length n."""
    return np.array([values[t] for t in range(n)], dtype=float)


def build(data, param_units, param_opt):
    """Build all nodes of an ``EnergySystem`` like ``run_model``, but don't
    solve it."""
    es = EnergySystem(data, param_units, param_opt)
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()
    return es


@pytest.fixture
def data(make_data):
    """Default synthetic 24 h input time series."""
    return make_data()


@pytest.fixture
def opt(make_opt):
    """Default optimization parameters."""
    return make_opt()


@pytest.fixture
def all_units(make_unit):
    """Parameters for one unit of every type (``hp1``, ``ccet1``, ...)."""
    return {f'{cat}1': make_unit(cat) for cat in ALL_CATS}


@pytest.fixture
def es_all(data, all_units, opt):
    """Energy system with one unit of every type, built but not solved."""
    return build(data, all_units, opt)


def out_flow(es, unit, bus='hnw'):
    """The solph flow from ``unit`` into ``bus`` (default: heat network)."""
    return es.comps[unit].outputs[es.buses[bus]]


def in_flow(es, unit, bus):
    """The solph flow from ``bus`` into ``unit``."""
    return es.comps[unit].inputs[es.buses[bus]]


# %% Constructor

@pytest.mark.parametrize('units, tes, chp, gas, el', [
    (['gb1'], False, False, True, False),
    (['hp1'], False, False, False, True),
    (['eb1'], False, False, False, True),
    (['ccet1'], False, True, True, True),
    (['ice2'], False, True, True, True),
    (['tes1', 'sol1'], True, False, False, False),
    (['exhs1'], False, False, False, False),
    (['hp12', 'gb3'], False, False, True, True),
    (['sol1', 'tes1', 'tes2', 'ice1'], True, True, True, True),
])
def test_usage_flags(units, tes, chp, gas, el, data, opt, make_unit):
    """Test wether xxx_used attributes are correctly infered from units."""
    param_units = {u: make_unit(u.rstrip('0123456789')) for u in units}
    es = EnergySystem(data, param_units, opt)
    assert (es.tes_used, es.chp_used, es.gas_used, es.el_used) == (
        tes, chp, gas, el
    )


def test_time_index_starts_at_data_and_is_hourly(data, opt, make_unit):
    """The model time index is hourly and matches the input data."""
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.periods == len(data)
    # infer_last_interval adds the end of the last time step
    assert len(es.es.timeindex) == len(data) + 1
    assert es.es.timeindex[0] == data.index[0]
    assert (np.diff(es.es.timeindex) == pd.Timedelta('1h')).all()


def test_bwsf_uses_capital_interest_and_lifetime(data, make_opt, make_unit):
    """The bwsf is computed from ``capital_interest`` and ``lifetime``."""
    opt = make_opt(capital_interest=0.07, lifetime=15)
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.bwsf == pytest.approx(calc_bwsf(0.07, 15))


def test_constructor_does_not_build_nodes(data, opt, make_unit):
    """Nodes are only created by the generate_* methods."""
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.buses == {}
    assert es.comps == {}
    assert len(es.es.nodes) == 0


# %% Topology

@pytest.mark.parametrize('units, buses, comps', [
    (
        ['gb1'],
        {'gnw', 'hnw'},
        {'gas_source', 'heat_sink', 'gb1'},
    ),
    (
        ['hp1', 'eb1'],
        {'enw', 'hnw'},
        {'elec_source', 'heat_sink', 'hp1', 'eb1'},
    ),
    (
        ['ccet1'],
        {'gnw', 'enw', 'hnw', 'chp_node'},
        {'gas_source', 'elec_source', 'heat_sink', 'elec_sink', 'ccet1',
         'chp_internal'},
    ),
    (
        ['sol1', 'exhs1', 'tes1'],
        {'hnw'},
        {'heat_sink', 'sol1', 'exhs1', 'tes1'},
    ),
    (
        ['gb1', 'gb2', 'hp1', 'hp2'],
        {'gnw', 'enw', 'hnw'},
        {'gas_source', 'elec_source', 'heat_sink', 'gb1', 'gb2', 'hp1', 'hp2'},
    ),
])
def test_topology(units, buses, comps, data, opt, make_unit):
    """Only the buses and components needed by the given units are built.

    E.g. a gas boiler needs a gas network and gas source, but no
    electricity network.
    """
    param_units = {u: make_unit(u.rstrip('0123456789')) for u in units}
    es = build(data, param_units, opt)
    assert set(es.buses) == buses
    assert set(es.comps) == comps


def test_all_nodes_are_added_to_solph_energy_system(es_all):
    """Every created node is also added to the solph energy system (a node
    missing there would silently be left out of the optimization)."""
    expected = (
        {str(b.label) for b in es_all.buses.values()}
        | {str(c.label) for c in es_all.comps.values()}
    )
    assert {str(n.label) for n in es_all.es.nodes} == expected


def test_node_labels(es_all):
    """Nodes carry the labels that ``check_column`` relies on later."""
    assert {k: str(b.label) for k, b in es_all.buses.items()} == {
        'gnw': 'gas network',
        'enw': 'electricity network',
        'hnw': 'heat network',
        'chp_node': 'chp node',
    }
    labels = {k: str(c.label) for k, c in es_all.comps.items()}
    assert labels['gas_source'] == 'gas source'
    assert labels['elec_source'] == 'electricity source'
    assert labels['heat_sink'] == 'heat demand'
    assert labels['elec_sink'] == 'spotmarket'
    assert labels['chp_internal'] == 'chp internal'
    for cat in ALL_CATS:
        assert labels[f'{cat}1'] == f'{cat}1'


@pytest.mark.parametrize('unit, cls, inputs, outputs', [
    ('hp1', solph.components.Converter, {'enw'}, {'hnw'}),
    ('eb1', solph.components.Converter, {'enw'}, {'hnw'}),
    ('gb1', solph.components.Converter, {'gnw'}, {'hnw'}),
    ('ccet1', solph.components.Converter, {'gnw'}, {'hnw', 'chp_node'}),
    ('ice1', solph.components.Converter, {'gnw'}, {'hnw', 'chp_node'}),
    ('sol1', solph.components.Source, set(), {'hnw'}),
    ('exhs1', solph.components.Source, set(), {'hnw'}),
    ('tes1', solph.components.GenericStorage, {'hnw'}, {'hnw'}),
    ('gas_source', solph.components.Source, set(), {'gnw'}),
    ('elec_source', solph.components.Source, set(), {'enw'}),
    ('heat_sink', solph.components.Sink, {'hnw'}, set()),
    ('elec_sink', solph.components.Sink, {'chp_node'}, set()),
    ('chp_internal', solph.components.Converter, {'chp_node'}, {'enw'}),
])
def test_component_connections(es_all, unit, cls, inputs, outputs):
    """Each component has the right solph type and connects to the right
    input and output buses."""
    comp = es_all.comps[unit]
    bus_key = {b: k for k, b in es_all.buses.items()}
    assert isinstance(comp, cls)
    assert {bus_key[b] for b in comp.inputs} == inputs
    assert {bus_key[b] for b in comp.outputs} == outputs


# %% Commodity sources and sinks

def test_gas_source_cost_includes_co2(es_all, data, opt):
    """Gas costs the gas price plus the CO2 price per MWh of gas."""
    flow = out_flow(es_all, 'gas_source', 'gnw')
    expected = data['gas_price'] + data['co2_price'] * opt['ef_gas']
    np.testing.assert_allclose(seq(flow.variable_costs, len(data)), expected)


def test_electricity_source_cost(es_all, data, opt):
    """Grid electricity costs spot price plus grid charges minus self charges.

    The self consumption charges are added again on the consumer's input
    flow (see ``test_single_input_converter_parameters``), so grid power
    pays the full grid charges and CHP power only the self charges.
    """
    flow = out_flow(es_all, 'elec_source', 'enw')
    expected = (
        data['el_spot_price'] + opt['elec_consumer_charges_grid']
        - opt['elec_consumer_charges_self']
    )
    np.testing.assert_allclose(seq(flow.variable_costs, len(data)), expected)


def test_heat_sink_is_fixed_to_demand(es_all, data, opt):
    """The heat demand must be met exactly; sold heat counts as revenue
    (negative cost)."""
    flow = in_flow(es_all, 'heat_sink', 'hnw')
    demand = data['heat_demand']
    assert flow.nominal_capacity == pytest.approx(demand.max())
    np.testing.assert_allclose(
        seq(flow.fix, len(data)) * flow.nominal_capacity, demand
    )
    np.testing.assert_allclose(
        seq(flow.variable_costs, len(data)), -opt['heat_price']
    )


def test_spotmarket_sink_revenue(es_all, data, opt):
    """Sold CHP electricity earns the spot price plus the avoided grid fees
    (vNNE)."""
    flow = in_flow(es_all, 'elec_sink', 'chp_node')
    np.testing.assert_allclose(
        seq(flow.variable_costs, len(data)),
        -(data['el_spot_price'] + opt['vNNE'])
    )


def test_chp_internal_link(es_all):
    """CHP electricity can be used internally without loss, practically
    unlimited capacity and extra cost."""
    comp = es_all.comps['chp_internal']
    enw = es_all.buses['enw']
    assert comp.conversion_factors[enw][0] == 1
    assert comp.outputs[enw].nominal_capacity == 9999
    assert comp.inputs[es_all.buses['chp_node']].variable_costs[0] in (0, None)


# %% Heat production units (dispatch mode)

@pytest.mark.parametrize('cat, input_bus, eff_key, cost_key', [
    ('hp', 'enw', 'cop', 'elec_consumer_charges_self'),
    ('eb', 'enw', 'eta', 'elec_consumer_charges_self'),
    ('gb', 'gnw', 'eta', 'energy_tax'),
])
def test_single_input_converter_parameters(
        cat, input_bus, eff_key, cost_key, data, opt, make_unit):
    """Heat pump, electrode and gas boiler get their parameters from the
    unit dict.

    Checked: input cost, efficiency, capacity, part load limits, on/off
    behavior (NonConvex) and the variable cost reduced by the bonus.
    """
    params = make_unit(cat, op_cost_bonus_rel=0.25)
    es = build(data, {f'{cat}1': params}, opt)
    comp = es.comps[f'{cat}1']
    inflow = in_flow(es, f'{cat}1', input_bus)
    outflow = out_flow(es, f'{cat}1')

    assert inflow.variable_costs[0] == pytest.approx(opt[cost_key])
    assert comp.conversion_factors[es.buses[input_bus]][0] == pytest.approx(
        1 / params[eff_key]
    )
    assert outflow.nominal_capacity == params['cap_N']
    assert outflow.maximum[0] == params['Q_rel_max']
    assert outflow.minimum[0] == params['Q_rel_min']
    assert isinstance(outflow.nonconvex, solph.NonConvex)
    assert outflow.investment is None
    assert outflow.variable_costs[0] == pytest.approx(
        params['op_cost_var'] * 0.75
    )


@pytest.mark.parametrize('cat', ['ccet', 'ice'])
def test_chp_parameters(cat, data, opt, make_unit):
    """CHP units (ccet, ice) convert gas into heat and electricity with the
    given efficiencies."""
    params = make_unit(cat, op_cost_bonus_rel=0.25)
    es = build(data, {f'{cat}1': params}, opt)
    comp = es.comps[f'{cat}1']
    heat = out_flow(es, f'{cat}1', 'hnw')
    power = out_flow(es, f'{cat}1', 'chp_node')
    gas = in_flow(es, f'{cat}1', 'gnw')

    assert comp.conversion_factors[es.buses['hnw']][0] == params['eta_th']
    assert comp.conversion_factors[es.buses['chp_node']][0] == (
        params['eta_el']
    )
    assert heat.nominal_capacity == params['cap_N']
    assert heat.maximum[0] == params['Q_rel_max']
    assert heat.minimum[0] == params['Q_rel_min']
    assert isinstance(heat.nonconvex, solph.NonConvex)
    # variable operating cost is charged on the electricity output
    assert power.variable_costs[0] == pytest.approx(
        params['op_cost_var'] * 0.75
    )
    assert gas.variable_costs[0] in (0, None)


def test_solar_thermal_parameters(data, opt, make_unit):
    """Solar heat is fixed by irradiation, collector efficiency and area."""
    params = make_unit('sol', op_cost_bonus_rel=0.5)
    es = build(data, {'sol1': params}, opt)
    flow = out_flow(es, 'sol1')

    assert flow.nominal_capacity == params['A_N']
    np.testing.assert_allclose(
        seq(flow.fix, len(data)),
        data['solar_heat_flow'] * params['eta_col']
    )
    assert flow.variable_costs[0] == pytest.approx(params['op_cost_var'] / 2)


@pytest.mark.parametrize('fix', [True, False])
def test_external_heat_source_fix(fix, data, opt, make_unit):
    """With ``fix=True``, the external heat source always runs at nominal
    capacity. Otherwise the optimizer decides (solph stores ``fix=None``)."""
    params = make_unit('exhs', fix=fix)
    es = build(data, {'exhs1': params}, opt)
    flow = out_flow(es, 'exhs1')

    if fix:
        assert flow.fix[0] == 1
    else:
        assert flow.fix is None
    assert flow.nominal_capacity == params['cap_N']
    assert flow.variable_costs[0] == pytest.approx(params['op_cost_var'])


def test_storage_parameters(data, opt, make_unit):
    """The storage gets capacity, losses, initial level and power limits.

    With a fixed capacity, the charging and discharging power is limited
    by giving both flows a fixed capacity of ``Q_N * Q_in_to_cap`` and
    ``Q_N * Q_out_to_cap``. (solph's ``invest_relation_*_capacity`` would
    only apply in invest mode.) The variable cost (0.3, with 50 % bonus) is
    charged on both charging and discharging.
    """
    params = make_unit(
        'tes', Q_in_to_cap=0.2, Q_out_to_cap=0.3, op_cost_var=0.3,
        op_cost_bonus_rel=0.5
    )
    es = build(data, {'tes1': params}, opt)
    tes = es.comps['tes1']
    charge = in_flow(es, 'tes1', 'hnw')
    discharge = out_flow(es, 'tes1', 'hnw')

    assert tes.nominal_storage_capacity == params['Q_N']
    assert tes.investment is None
    assert tes.loss_rate[0] == params['Q_rel_loss']
    assert tes.initial_storage_level == params['init_storage']
    assert tes.balanced == params['balanced']
    assert charge.nominal_capacity == pytest.approx(params['Q_N'] * 0.2)
    assert discharge.nominal_capacity == pytest.approx(params['Q_N'] * 0.3)
    for flow in (charge, discharge):
        assert flow.investment is None
        assert flow.variable_costs[0] == pytest.approx(0.15)


# %% Investment mode

INVEST_KEYS = {
    'hp': ('cap_max', 'cap_min'),
    'ccet': ('cap_max', 'cap_min'),
    'ice': ('cap_max', 'cap_min'),
    'gb': ('cap_max', 'cap_min'),
    'eb': ('cap_max', 'cap_min'),
    'exhs': ('cap_max', 'cap_min'),
    'sol': ('A_max', 'A_min'),
    'tes': ('Q_max', 'Q_min'),
}


@pytest.mark.parametrize('cat', ALL_CATS)
def test_investment_parameters(cat, data, make_opt, make_unit):
    """In invest mode, the capacity becomes a decision variable.

    Its yearly cost (ep_costs) is the annualized invest (inv_spez / bwsf,
    reduced by the bonus) plus the fixed operating cost. The size limits
    come from the unit dict.
    """
    opt = make_opt(capital_interest=0.06, lifetime=25)
    max_key, min_key = INVEST_KEYS[cat]
    params = make_unit(
        cat, invest_mode=True, inv_bonus_rel=0.3, **{min_key: 1.0}
    )
    es = build(data, {f'{cat}1': params}, opt)

    if cat == 'tes':
        investment = es.comps['tes1'].investment
    else:
        flow = out_flow(es, f'{cat}1')
        assert flow.nominal_capacity is None
        investment = flow.investment

    assert isinstance(investment, solph.Investment)
    expected_ep_costs = (
        params['inv_spez'] / calc_bwsf(0.06, 25) * 0.7 + params['op_cost_fix']
    )
    assert investment.ep_costs[0] == pytest.approx(expected_ep_costs)
    assert investment.maximum[0] == params[max_key]
    assert investment.minimum[0] == params[min_key]


def test_storage_investment_links_flow_capacities(data, opt, make_unit):
    """In invest mode, storage capacity and charging/discharging power are
    all optimized, and the power is tied to the capacity by the ratios."""
    params = make_unit(
        'tes', invest_mode=True, Q_in_to_cap=0.2, Q_out_to_cap=0.3
    )
    es = build(data, {'tes1': params}, opt)
    tes = es.comps['tes1']
    assert tes.nominal_storage_capacity is None
    assert isinstance(in_flow(es, 'tes1', 'hnw').investment, solph.Investment)
    assert isinstance(out_flow(es, 'tes1', 'hnw').investment, solph.Investment)
    assert tes.invest_relation_input_capacity[0] == 0.2
    assert tes.invest_relation_output_capacity[0] == 0.3


def test_mixed_invest_and_dispatch_units(data, opt, make_unit):
    """``invest_mode`` applies per unit, so both modes can be combined."""
    es = build(data, {
        'gb1': make_unit('gb', invest_mode=True),
        'gb2': make_unit('gb', invest_mode=False),
    }, opt)
    assert isinstance(out_flow(es, 'gb1').investment, solph.Investment)
    assert out_flow(es, 'gb2').investment is None
    assert out_flow(es, 'gb2').nominal_capacity == 150.0


# %% Input handling

def test_building_does_not_mutate_inputs(data, all_units, opt):
    """Building leaves the input data and parameter dicts unchanged."""
    data_before = data.copy()
    units_before = copy.deepcopy(all_units)
    opt_before = copy.deepcopy(opt)

    build(data, all_units, opt)

    pd.testing.assert_frame_equal(data, data_before)
    assert all_units == units_before
    assert opt == opt_before


def test_shipped_default_parameters_build(shipped_defaults, make_data):
    """The default JSON files of the dashboard contain every required key."""
    param_units, param_opt = shipped_defaults
    es = build(make_data(), param_units, param_opt)
    assert set(param_units) <= set(es.comps)
