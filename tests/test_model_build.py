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
    es = EnergySystem(data, param_units, param_opt)
    es.generate_buses()
    es.generate_sources()
    es.generate_sinks()
    es.generate_components()
    return es


@pytest.fixture
def data(make_data):
    return make_data()


@pytest.fixture
def opt(make_opt):
    return make_opt()


@pytest.fixture
def all_units(make_unit):
    return {f'{cat}1': make_unit(cat) for cat in ALL_CATS}


@pytest.fixture
def es_all(data, all_units, opt):
    """Energy system with one unit of every type, built but not solved."""
    return build(data, all_units, opt)


def out_flow(es, unit, bus='hnw'):
    return es.comps[unit].outputs[es.buses[bus]]


def in_flow(es, unit, bus):
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
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.periods == len(data)
    # infer_last_interval adds the end of the last time step
    assert len(es.es.timeindex) == len(data) + 1
    assert es.es.timeindex[0] == data.index[0]
    assert (np.diff(es.es.timeindex) == pd.Timedelta('1h')).all()


def test_bwsf_uses_capital_interest_and_lifetime(data, make_opt, make_unit):
    opt = make_opt(capital_interest=0.07, lifetime=15)
    es = EnergySystem(data, {'gb1': make_unit('gb')}, opt)
    assert es.bwsf == pytest.approx(calc_bwsf(0.07, 15))


def test_constructor_does_not_build_nodes(data, opt, make_unit):
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
    param_units = {u: make_unit(u.rstrip('0123456789')) for u in units}
    es = build(data, param_units, opt)
    assert set(es.buses) == buses
    assert set(es.comps) == comps


def test_all_nodes_are_added_to_solph_energy_system(es_all):
    expected = (
        {str(b.label) for b in es_all.buses.values()}
        | {str(c.label) for c in es_all.comps.values()}
    )
    assert {str(n.label) for n in es_all.es.nodes} == expected


def test_node_labels(es_all):
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
    comp = es_all.comps[unit]
    bus_key = {b: k for k, b in es_all.buses.items()}
    assert isinstance(comp, cls)
    assert {bus_key[b] for b in comp.inputs} == inputs
    assert {bus_key[b] for b in comp.outputs} == outputs


# %% Commodity sources and sinks

def test_gas_source_cost_includes_co2(es_all, data, opt):
    flow = out_flow(es_all, 'gas_source', 'gnw')
    expected = data['gas_price'] + data['co2_price'] * opt['ef_gas']
    np.testing.assert_allclose(seq(flow.variable_costs, len(data)), expected)


def test_electricity_source_cost(es_all, data, opt):
    flow = out_flow(es_all, 'elec_source', 'enw')
    expected = (
        data['el_spot_price'] + opt['elec_consumer_charges_grid']
        - opt['elec_consumer_charges_self']
    )
    np.testing.assert_allclose(seq(flow.variable_costs, len(data)), expected)


def test_heat_sink_is_fixed_to_demand(es_all, data, opt):
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
    flow = in_flow(es_all, 'elec_sink', 'chp_node')
    np.testing.assert_allclose(
        seq(flow.variable_costs, len(data)),
        -(data['el_spot_price'] + opt['vNNE'])
    )


def test_chp_internal_link(es_all):
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
    assert outflow.max[0] == params['Q_rel_max']
    assert outflow.min[0] == params['Q_rel_min']
    assert isinstance(outflow.nonconvex, solph.NonConvex)
    assert outflow.investment is None
    assert outflow.variable_costs[0] == pytest.approx(
        params['op_cost_var'] * 0.75
    )


@pytest.mark.parametrize('cat', ['ccet', 'ice'])
def test_chp_parameters(cat, data, opt, make_unit):
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
    assert heat.max[0] == params['Q_rel_max']
    assert heat.min[0] == params['Q_rel_min']
    assert isinstance(heat.nonconvex, solph.NonConvex)
    # variable operating cost is charged on the electricity output
    assert power.variable_costs[0] == pytest.approx(
        params['op_cost_var'] * 0.75
    )
    assert gas.variable_costs[0] in (0, None)


def test_solar_thermal_parameters(data, opt, make_unit):
    params = make_unit('sol', op_cost_bonus_rel=0.5)
    es = build(data, {'sol1': params}, opt)
    flow = out_flow(es, 'sol1')

    assert flow.nominal_capacity == params['A_N']
    np.testing.assert_allclose(
        seq(flow.fix, len(data)),
        data['solar_heat_flow'] * params['eta_col']
    )
    assert flow.variable_costs[0] == pytest.approx(params['op_cost_var'] / 2)


@pytest.mark.parametrize('fix, expected', [(True, 1), (False, None)])
def test_external_heat_source_fix(fix, expected, data, opt, make_unit):
    params = make_unit('exhs', fix=fix)
    es = build(data, {'exhs1': params}, opt)
    flow = out_flow(es, 'exhs1')

    assert flow.fix[0] == expected
    assert flow.nominal_capacity == params['cap_N']
    assert flow.variable_costs[0] == pytest.approx(params['op_cost_var'])


def test_storage_parameters(data, opt, make_unit):
    params = make_unit('tes', op_cost_var=0.3, op_cost_bonus_rel=0.5)
    es = build(data, {'tes1': params}, opt)
    tes = es.comps['tes1']

    assert tes.nominal_storage_capacity == params['Q_N']
    assert tes.investment is None
    assert tes.loss_rate[0] == params['Q_rel_loss']
    assert tes.initial_storage_level == params['init_storage']
    assert tes.balanced == params['balanced']
    assert tes.invest_relation_input_capacity[0] == params['Q_in_to_cap']
    assert tes.invest_relation_output_capacity[0] == params['Q_out_to_cap']
    for flow in (in_flow(es, 'tes1', 'hnw'), out_flow(es, 'tes1', 'hnw')):
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
    es = build(data, {'tes1': make_unit('tes', invest_mode=True)}, opt)
    assert es.comps['tes1'].nominal_storage_capacity is None
    assert isinstance(in_flow(es, 'tes1', 'hnw').investment, solph.Investment)
    assert isinstance(out_flow(es, 'tes1', 'hnw').investment, solph.Investment)


def test_mixed_invest_and_dispatch_units(data, opt, make_unit):
    es = build(data, {
        'gb1': make_unit('gb', invest_mode=True),
        'gb2': make_unit('gb', invest_mode=False),
    }, opt)
    assert isinstance(out_flow(es, 'gb1').investment, solph.Investment)
    assert out_flow(es, 'gb2').investment is None
    assert out_flow(es, 'gb2').nominal_capacity == 150.0


# %% Input handling

def test_building_does_not_mutate_inputs(data, all_units, opt):
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
